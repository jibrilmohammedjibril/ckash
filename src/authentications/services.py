import os
from datetime import datetime, timezone
import httpx
from sqlmodel import Session, select
import random
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import os
from .models import OTP

TERMII_API_KEY = os.getenv("TERMII_API_KEY")
SENDER_ID = os.getenv("SENDER_ID")
BASE_URL = os.getenv("BASE_URL")


async def send_otp_via_termii(phone_number: str, otp: str, message_template: str):
    """
    Send an OTP to a phone number using Termii.

    Args:
        phone_number (str): The recipient's phone number in international format (e.g., +2341234567890).
        otp (str): The OTP to send.
        message_template (str): The message template, e.g., "Your OTP is {otp}."

    Returns:
        dict: Response from Termii API.
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

    print(otp)

    # Use async with to manage the HTTP client session
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()  # Raises an exception for 4xx/5xx responses
            response_data = response.json()  # Parse the JSON response

            # Check if Termii's API response is successful
            if response_data.get("status") == "success":
                print("OTP sent")
                return {"success": True, "message": "OTP sent successfully."}
            else:
                print("OTP not sent")
                return {"success": False, "message": response_data.get("message", "Failed to send OTP.")}

        except httpx.HTTPStatusError as e:
            # Handle non-200 HTTP responses (e.g., 4xx or 5xx errors)
            print(f"HTTP error occurred: {e}")
            return {"success": False, "message": f"HTTP error occurred: {e}"}

        except httpx.RequestError as e:
            # Handle request-related errors (e.g., network problems)
            print(f"Request error occurred: {e}")
            return {"success": False, "message": f"Request error occurred: {e}"}

        except httpx.JSONDecodeError as e:
            # Handle case where the response isn't valid JSON
            print(f"Failed to decode JSON: {e}")
            return {"success": False, "message": "Failed to decode JSON response from Termii."}

async def generate_otp(length=6):
    """
    Generate a numeric OTP of the specified length.
    """
    return ''.join(str(random.randint(0, 9)) for _ in range(length))


async def validate_otp(phone_number: str, entered_otp: str):
    """
    Validate the OTP entered by the user.
    """
    # Retrieve the OTP from Redis using the phone number as part of the key
    stored_otp = await redis.get(f"otp:{phone_number}")

    # Ensure stored_otp is a string (in case it's returned as bytes)
    if stored_otp:
        stored_otp = stored_otp.decode("utf-8")
    print(stored_otp)

    # Check if the stored OTP matches the entered OTP
    if stored_otp and stored_otp == entered_otp:
        # Remove OTP after validation
        await redis.delete(f"otp:{phone_number}")
        return True

    return False


async def send_user_otp(phone_number: str, db_session: AsyncSession):
    otp = await generate_otp()
    await store_otp(phone_number, otp, db_session)
    message_template = f"Your OTP is {otp}. It is valid for 5 minutes."
    response = await send_otp_via_termii(phone_number, otp, message_template)
    return response


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
