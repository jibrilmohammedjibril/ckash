from datetime import datetime, timezone, timedelta

from .models import User, OTP
from .schemas import SigninRequest, SignupRequest
from .services import send_user_otp, upload_image_to_cloudinary, generate_initial_image, generate_otp
from fastapi import APIRouter, Depends, status, BackgroundTasks
from fastapi.exceptions import HTTPException
from src.database import get_db
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup/")
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    # Use select() for async query
    statement = select(User).filter(User.phone_number == request.phone_number)
    result = await db.execute(statement)  # Use db directly here, no need to call db()
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User with this phone number already exists.")

    # Create and save the new user
    new_user = User(
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number,
        login_pin=request.login_pin
    )
    db.add(new_user)
    await db.commit()

    # Generate the image with initials
    image = await generate_initial_image(request.first_name, request.last_name)

    # Upload the image to Cloudinary
    image_url = await upload_image_to_cloudinary(image)

    # Update user with profile picture URL
    new_user.profile_picture = image_url
    await db.commit()

    # Send OTP
    response = await send_user_otp(request.phone_number, db)

    return {"message": "Signup successful. OTP sent.", "response": response, "profile_picture": image_url}


@router.post("/signin/")
async def signin(request: SigninRequest, db: AsyncSession = Depends(get_db)):
    # Use select() for async query
    statement = select(User).filter(User.phone_number == request.phone_number)
    result = await db.execute(statement)  # Use db directly here
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Send OTP
    response = await send_user_otp(request.phone_number, db)
    return {"message": "Signin successful. OTP sent.", "response": response}


@router.post("/verify-otp_signup/")
async def verify_otp(phone_number: str, otp: str, db: AsyncSession = Depends(get_db)):
    # Query the database for the OTP record based on the OTP code
    statement = select(OTP).where(OTP.otp_code == otp, OTP.is_valid == True)
    result = await db.execute(statement)
    otp_record = result.scalars().first()

    if not otp_record:
        raise HTTPException(status_code=404, detail="Invalid or expired OTP.")

    # Check if the phone number matches
    if otp_record.phone_number != phone_number:
        raise HTTPException(status_code=400, detail="The provided phone number does not match the OTP.")

    # Ensure created_date is timezone-aware
    created_date = otp_record.created_date
    if created_date.tzinfo is None:  # If naive, make it aware
        created_date = created_date.replace(tzinfo=timezone.utc)

    # Check if five minutes have elapsed since `created_date`
    current_time = datetime.now(timezone.utc)
    elapsed_time = current_time - created_date
    if elapsed_time > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="OTP has expired.")

    # Delete the OTP record after successful verification
    await db.delete(otp_record)
    await db.commit()

    return {"success": True, "message": "OTP verified successfully."}


@router.post("/verify-otp_signup/")
async def verify_otp(phone_number: str, otp: str, db: AsyncSession = Depends(get_db)):
    # Query the database for the OTP record based on the OTP code
    statement = select(OTP).where(OTP.otp_code == otp, OTP.is_valid == True)
    result = await db.execute(statement)
    otp_record = result.scalars().first()

    if not otp_record:
        raise HTTPException(status_code=404, detail="Invalid or expired OTP.")

    # Check if the phone number matches
    if otp_record.phone_number != phone_number:
        raise HTTPException(status_code=400, detail="The provided phone number does not match the OTP.")

    # Ensure created_date is timezone-aware
    created_date = otp_record.created_date
    if created_date.tzinfo is None:  # If naive, make it aware
        created_date = created_date.replace(tzinfo=timezone.utc)

    # Check if five minutes have elapsed since `created_date`
    current_time = datetime.now(timezone.utc)
    elapsed_time = current_time - created_date
    if elapsed_time > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="OTP has expired.")

    # Delete the OTP record after successful verification
    await db.delete(otp_record)
    await db.commit()

    return {"success": True, "message": "OTP verified successfully."}


@router.post("/verify-otp_signin/")
async def verify_otp(phone_number: str, otp: str, db: AsyncSession = Depends(get_db)):
    # Query the database for the OTP record based on the OTP code
    statement = select(OTP).where(OTP.otp_code == otp, OTP.is_valid == True)
    result = await db.execute(statement)
    otp_record = result.scalars().first()

    if not otp_record:
        raise HTTPException(status_code=404, detail="Invalid or expired OTP.")

    # Check if the phone number matches
    if otp_record.phone_number != phone_number:
        raise HTTPException(status_code=400, detail="The provided phone number does not match the OTP.")

    # Ensure created_date is timezone-aware
    created_date = otp_record.created_date
    if created_date.tzinfo is None:  # If naive, make it aware
        created_date = created_date.replace(tzinfo=timezone.utc)

    # Check if five minutes have elapsed since `created_date`
    current_time = datetime.now(timezone.utc)
    elapsed_time = current_time - created_date
    if elapsed_time > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="OTP has expired.")

    # Delete the OTP record after successful verification
    await db.delete(otp_record)
    await db.commit()

    # Query the User table using the phone number
    user_query = select(User).where(User.phone_number == phone_number)
    user_result = await db.execute(user_query)
    user_record = user_result.scalars().first()

    if not user_record:
        raise HTTPException(status_code=404, detail="User not found.")

    # Return user information
    return {
        "success": True,
        "message": "OTP verified successfully.",
        "user": {
            "first_name": user_record.first_name,
            "profile_picture": user_record.profile_picture,
            "phone_number": user_record.phone_number,
        }
    }


@router.post("/forgot-login-pin/")
async def forgot_login_pin(phone_number: str, db: AsyncSession = Depends(get_db)):
    # Step 1: Verify user exists
    statement = select(User).where(User.phone_number == phone_number)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User with this phone number does not exist.")

    # Step 2: Generate OTP and store it in the OTP table
    otp = await generate_otp()
    new_otp = OTP(
        phone_number=phone_number,
        otp_code=otp,
        is_valid=True,
        # Convert to naive datetime (strip timezone)
        created_date=datetime.now(timezone.utc).replace(tzinfo=None)  # Make it naive
    )
    db.add(new_otp)
    await db.commit()

    # Step 3: Send OTP to user
    response = await send_user_otp(phone_number, db)
    if not response.get("success"):
        raise HTTPException(status_code=500, detail="Failed to send OTP.")

    return {"message": "OTP sent successfully."}


@router.post("/reset-login-pin/")
async def reset_login_pin(phone_number: str, otp: str, new_login_pin: str, db: AsyncSession = Depends(get_db)):
    # Step 1: Validate the OTP
    statement = select(OTP).where(OTP.phone_number == phone_number, OTP.otp_code == otp, OTP.is_valid == True)
    result = await db.execute(statement)
    otp_record = result.scalars().first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    # Ensure OTP is not expired
    created_date = otp_record.created_date
    if created_date.tzinfo is None:
        created_date = created_date.replace(tzinfo=timezone.utc)
    current_time = datetime.now(timezone.utc)
    if current_time - created_date > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="OTP has expired.")

    # Step 2: Invalidate OTP
    otp_record.is_valid = False
    db.add(otp_record)

    # Step 3: Update the user's login pin
    statement = select(User).where(User.phone_number == phone_number)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.login_pin = new_login_pin
    db.add(user)
    await db.commit()

    return {"message": "Login PIN reset successfully."}