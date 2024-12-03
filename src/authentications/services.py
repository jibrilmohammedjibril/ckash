from datetime import datetime, timezone, timedelta
import httpx
import random
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import os

from sqlmodel import select

from .models import OTP
from PIL import Image, ImageDraw, ImageFont
import cloudinary
import cloudinary.uploader
from io import BytesIO
import dotenv

dotenv.load_dotenv()
TERMII_API_KEY = os.getenv("TERMII_API_KEY")
SENDER_ID = os.getenv("SENDER_ID")
BASE_URL = os.getenv("BASE_URL")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),  # Replace with your Cloudinary cloud name
    api_key=os.getenv("CLOUDINARY_API_KEY"),  # Replace with your Cloudinary API key
    api_secret=os.getenv("CLOUDINARY_API_SECRET")  # Replace with your Cloudinary API secret
)


async def send_otp_via_termii(phone_number: str, otp: str, message_template: str):
    """
    Send an OTP to a phone number using Termii.

    Args:
        phone_number (str): The recipient's phone number in international format (e.g., +2341234567890).
        otp (str): The OTP to send.
        message_template (str): The message template, e.g., "Your OTP is {otp}."

    Returns:
        dict: Response indicating success or failure.
    """
    url = f"{BASE_URL}/api/sms/send"
    message = message_template.format(otp=otp)

    payload = {
        "to": phone_number,
        "from": SENDER_ID,
        "sms": message,
        "type": "plain",  # Use 'plain' for standard SMS.
        "channel": "generic",  # Use 'generic' unless you're sending a voice message.
        "api_key": TERMII_API_KEY,
    }

    print(f"Sending OTP: {otp} to {phone_number}")

    # Use async with to manage the HTTP client session
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()  # Raises an exception for 4xx/5xx responses
            response_data = response.json()  # Parse the JSON response

            # Extract relevant fields from Termii's response
            message_id = response_data.get("message_id")
            balance = response_data.get("balance")
            user = response_data.get("user")
            message_status = response_data.get("message", "").lower()

            # Check for success based on Termii's documented response structure
            if "successfully sent" in message_status:
                print("OTP sent successfully.")
                return {
                    "success": True,
                    "message": "OTP sent successfully.",
                    "details": {
                        "message_id": message_id,
                        "balance": balance,
                        "user": user,
                    },
                }
            else:
                print("OTP failed to send.")
                return {
                    "success": False,
                    "message": response_data.get("message", "Failed to send OTP."),
                }

        except httpx.HTTPStatusError as e:
            # Handle non-200 HTTP responses (e.g., 4xx or 5xx errors)
            print(f"HTTP error occurred: {e}")
            return {"success": False, "message": f"HTTP error occurred: {e}"}


async def generate_otp(length=4):
    """
    Generate a numeric OTP of the specified length.
    """
    return ''.join(str(random.randint(0, 9)) for _ in range(length))


MAX_REQUESTS_BEFORE_BAN = 10
MAX_REQUESTS_LIMIT = 5
OTP_VALIDITY_PERIOD = timedelta(minutes=5)
RESEND_DELAY_PERIOD = timedelta(minutes=30)


async def send_user_otp(phone_number: str, db_session: AsyncSession):
    """
    Handle OTP requests with limits and validity checks.

    Args:
        phone_number (str): The recipient's phone number.
        db_session (AsyncSession): The database session.

    Returns:
        dict: Response indicating success or failure.
    """
    # Check if the phone number exists in the OTP table
    statement = select(OTP).where(OTP.phone_number == phone_number)
    result = await db_session.execute(statement)
    existing_otp = result.scalars().first()

    # Current time with timezone
    time_now = datetime.now(timezone.utc)

    if existing_otp:
        # Ensure `created_date` is timezone-aware
        created_date = existing_otp.created_date
        if created_date.tzinfo is None:  # If `created_date` is naive, make it timezone-aware
            created_date = created_date.replace(tzinfo=timezone.utc)

        time_since_created = time_now - created_date

        # Case 4: Request count <= 5
        if existing_otp.request_count < MAX_REQUESTS_LIMIT:
            new_otp = await generate_otp()
            existing_otp.otp_code = new_otp
            existing_otp.is_valid = True
            existing_otp.request_count += 1
            existing_otp.expire_date = time_now.replace(tzinfo=None)
            await db_session.commit()

            # Send OTP to the user
            message_template = f"Your OTP is {new_otp}. It is valid for 5 minutes."
            response = await send_otp_via_termii(phone_number, new_otp, message_template)
            return {"success": True, "message": "OTP sent successfully.", "otp": new_otp}

        # Case 3: Request count > 10
        if existing_otp.request_count > MAX_REQUESTS_BEFORE_BAN:
            return {"success": False, "message": "Your account has been banned due to excessive requests."}

        # Case 1: Request count > 5 and time < 30 minutes
        if existing_otp.request_count >= MAX_REQUESTS_LIMIT and time_since_created < RESEND_DELAY_PERIOD:
            return {"success": False, "message": "Too many requests. Please try again after 30 minutes."}

        # Case 2: Request count >= 5 and time >= 30 minutes
        if existing_otp.request_count <= MAX_REQUESTS_BEFORE_BAN and time_since_created >= RESEND_DELAY_PERIOD:
            new_otp = await generate_otp()
            existing_otp.otp_code = new_otp
            existing_otp.is_valid = True
            existing_otp.request_count += 1
            existing_otp.expire_date = time_now.replace(tzinfo=None)
            await db_session.commit()

            # Send OTP to the user
            message_template = f"Your OTP is {new_otp}. It is valid for 5 minutes."
            response = await send_otp_via_termii(phone_number, new_otp, message_template)
            return {"success": True, "message": "OTP sent successfully.", "otp": new_otp}

    # If no OTP exists, create a new one
    new_otp = await generate_otp()
    new_otp_record = OTP(
        phone_number=phone_number,
        otp_code=new_otp,
        is_valid=True,
        created_date=time_now.replace(tzinfo=None),
        request_count=1,
    )
    db_session.add(new_otp_record)
    await db_session.commit()

    # Send OTP to the user
    message_template = f"Your OTP is {new_otp}. It is valid for 5 minutes."
    response = await send_otp_via_termii(phone_number, new_otp, message_template)

    return {"success": True, "message": "OTP sent successfully.", "otp": new_otp}


# async def send_user_otp(phone_number: str, db_session: AsyncSession):
#     otp = await generate_otp()
#     await store_otp(phone_number, otp, db_session)
#     message_template = f"Your OTP is {otp}. It is valid for 5 minutes."
#     response = await send_otp_via_termii(phone_number, otp, message_template)
#     return response


async def store_otp(phone_number: str, otp: str, db_session: AsyncSession):
    # First, mark the existing OTP as invalid
    # Use `db_session.execute` to perform the update with the `update` query
    await db_session.execute(
        OTP.__table__.update()
        .where(OTP.phone_number == phone_number)
        .values(is_valid=False)
    )
    # Commit the changes to make them persistent in the database
    await db_session.commit()

    # Now create the new OTP record
    otp_record = OTP(
        phone_number=phone_number,
        otp_code=otp,
        created_at=datetime.now(timezone.utc)
    )

    # Add the new OTP record and commit to save it
    db_session.add(otp_record)
    await db_session.commit()


async def generate_initial_image(first_name: str, last_name: str) -> Image:
    # Create an image with a white background
    image = Image.new("RGB", (200, 200), color="white")
    draw = ImageDraw.Draw(image)

    # Load a font
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except IOError:
        font = ImageFont.load_default()

    # Get the initials from the first and last name
    initials = f"{first_name[0].upper()}{last_name[0].upper()}"

    # Define text color (random color for each letter)
    def random_color():
        return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    # Positioning the text in the center of the image
    text_bbox = draw.textbbox((0, 0), initials, font=font)  # Get the bounding box
    text_width = text_bbox[2] - text_bbox[0]  # Width of the text
    text_height = text_bbox[3] - text_bbox[1]  # Height of the text
    position = ((200 - text_width) / 2, (200 - text_height) / 2)

    # Draw each letter with a random color
    for i, letter in enumerate(initials):
        draw.text((position[0] + i * text_width / len(initials), position[1]),
                  letter, font=font, fill=random_color())

    return image


async def upload_image_to_cloudinary(image):
    """
    Uploads the generated image to Cloudinary and returns the URL.
    If the image is passed as a BytesIO object, it will be converted to PIL.Image first.
    """

    # Check if the image is already a PIL.Image
    if isinstance(image, BytesIO):
        # If it's a BytesIO object, load it as a PIL.Image
        image = Image.open(image)

    # Create a BytesIO buffer to store the image data
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")  # Save the image in PNG format to the buffer
    img_byte_arr.seek(0)  # Rewind the buffer to the beginning

    # Upload image to Cloudinary
    response = cloudinary.uploader.upload(img_byte_arr, resource_type="image")

    # Return the URL of the uploaded image
    return response['secure_url']
