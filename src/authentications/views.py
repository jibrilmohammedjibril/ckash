from datetime import datetime, timezone, timedelta

from .models import User, OTP, InitUser
from .schemas import SigninRequest, SignupRequest, TokenResponse, LoginRequest, VerifyOTPSignup, VerifyOTPSignin, \
    ForgotLoginPin, ResetLoginPin, ResendOTP
from .services import send_user_otp, upload_image_to_cloudinary, generate_initial_image, generate_otp
from fastapi import APIRouter, Depends, status, BackgroundTasks
from fastapi.exceptions import HTTPException
from src.database import get_db
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from .utilities import (verify_password, create_access_token, create_refresh_token, decode_token, REFRESH_SECRET_KEY,
                        get_current_user, hash_password)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup/")
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    # Step 1: Check if the user already exists in the InitUser table
    statement = select(User).filter(User.phone_number == request.phone_number)
    statement1 = select(InitUser).filter(InitUser.phone_number == request.phone_number)
    result = await db.execute(statement)
    result1 = await db.execute(statement1)
    existing_user = result.scalars().first()
    existing_user_init = result1.scalars().first()

    if existing_user_init:
        await db.delete(existing_user_init)
        await db.commit()

    if existing_user:
        raise HTTPException(status_code=400, detail="User with this phone number already exists.")

    # Step 2: Create a new InitUser object and save to the temporary table
    new_init_user = InitUser(
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number,
        login_pin=await hash_password(request.login_pin)
    )
    db.add(new_init_user)
    await db.commit()

    # Step 3: Generate the image with initials
    image = await generate_initial_image(request.first_name, request.last_name)

    # Step 4: Upload the image to Cloudinary
    image_url = await upload_image_to_cloudinary(image)

    # Step 5: Update the profile picture URL in InitUser
    new_init_user.profile_picture = image_url
    await db.commit()

    # Step 6: Send OTP
    response = await send_user_otp(request.phone_number, db)

    # Step 7: Return response
    return {"message": "Signup successful. OTP sent.", "response": response}


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
async def verify_otp_signup(request: VerifyOTPSignup, db: AsyncSession = Depends(get_db)):
    # Step 1: Query the database for the OTP record based on the OTP code
    statement = select(OTP).where(OTP.otp_code == request.otp, OTP.is_valid == True)
    result = await db.execute(statement)
    otp_record = result.scalars().first()

    if not otp_record:
        raise HTTPException(status_code=404, detail="Invalid or expired OTP.")

    # Step 2: Check if the phone number matches
    if otp_record.phone_number != request.phone_number:
        raise HTTPException(status_code=400, detail="The provided phone number does not match the OTP.")

    # Step 3: Ensure created_date is timezone-aware
    created_date = otp_record.expire_date
    #
    # Step 4: Check if five minutes have elapsed since `created_date`
    current_time = datetime.now(timezone.utc)
    elapsed_time = current_time - created_date
    print(f"the created date is {created_date}")
    print(f"the current date is {current_time}")
    print(f"the remaining date is {elapsed_time}")
    if elapsed_time > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="OTP has expired.")

    # Step 5: Retrieve the user data from the InitUser table
    statement = select(InitUser).where(InitUser.phone_number == request.phone_number)
    result = await db.execute(statement)
    init_user_record = result.scalars().first()

    if not init_user_record:
        raise HTTPException(status_code=404, detail="No temporary user data found.")

    # Step 6: Copy data from InitUser to User
    new_user = User(
        first_name=init_user_record.first_name,
        last_name=init_user_record.last_name,
        phone_number=init_user_record.phone_number,
        login_pin=init_user_record.login_pin,
        profile_picture=init_user_record.profile_picture
    )
    db.add(new_user)
    await db.commit()

    # Step 7: Delete the InitUser record after successful verification and transfer
    await db.delete(init_user_record)
    await db.commit()

    # Step 8: Delete the OTP record after successful verification
    await db.delete(otp_record)
    await db.commit()

    return {"success": True, "message": "OTP verified successfully, user account created."}


@router.post("/verify-otp_signin/")
async def verify_otp_signin(request: VerifyOTPSignin, db: AsyncSession = Depends(get_db)):
    # Query the database for the OTP record based on the OTP code
    statement = select(OTP).where(OTP.otp_code == request.otp, OTP.is_valid == True)
    result = await db.execute(statement)
    otp_record = result.scalars().first()

    if not otp_record:
        raise HTTPException(status_code=404, detail="Invalid or expired OTP.")

    # Check if the phone number matches
    if otp_record.phone_number != request.phone_number:
        raise HTTPException(status_code=400, detail="The provided phone number does not match the OTP.")

    # Ensure created_date is timezone-aware
    created_date = otp_record.created_date


    # Check if five minutes have elapsed since `created_date`
    current_time = datetime.now(timezone.utc)
    elapsed_time = current_time - created_date
    print(f"the created date is {created_date}")
    print(f"the current date is {current_time}")
    print(f"the remaining date is {elapsed_time}")

    if elapsed_time > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="OTP has expired.")

    # Delete the OTP record after successful verification
    await db.delete(otp_record)
    await db.commit()

    # Query the User table using the phone number
    user_query = select(User).where(User.phone_number == request.phone_number)
    user_result = await db.execute(user_query)
    user_record = user_result.scalars().first()

    if not user_record:
        raise HTTPException(status_code=404, detail="User not found.")

    user_record.device_id = request.device_id
    db.add(user_record)
    await db.commit()

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
async def forgot_login_pin(request: ForgotLoginPin, db: AsyncSession = Depends(get_db)):
    # Step 1: Verify user exists
    statement = select(User).where(User.phone_number == request.phone_number)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User with this phone number does not exist.")

    # Step 2: Generate OTP and store it in the OTP table

    # Step 3: Send OTP to user
    response = await send_user_otp(request.phone_number, db)
    if not response.get("success"):
        raise HTTPException(status_code=500, detail="Failed to send OTP.")

    return {"message": "OTP sent successfully."}


@router.post("/reset-login-pin/")
async def reset_login_pin(request: ResetLoginPin, db: AsyncSession = Depends(get_db)):
    # Step 1: Validate the OTP
    statement = select(OTP).where(OTP.phone_number == request.phone_number, OTP.otp_code == request.otp)
    result = await db.execute(statement)
    otp_record = result.scalars().first()
    print(request)

    print(request.phone_number)
    print(otp_record)

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    # Ensure OTP is not expired
    created_date = otp_record.expire_date

    current_time = datetime.now(timezone.utc)
    print(f"this is your {created_date}")
    print(f"this your {current_time}")
    print(current_time - created_date > timedelta(minutes=5))
    if current_time - created_date > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="OTP has expired.")

    # Step 2: Invalidate OTP
    otp_record.is_valid = False
    db.add(otp_record)

    # Step 3: Update the user's login pin
    statement = select(User).where(User.phone_number == request.phone_number)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.login_pin = await hash_password(request.new_login_pin)
    db.add(user)
    await db.delete(otp_record)
    await db.commit()

    return {"message": "Login PIN reset successfully."}


@router.post("/resend-otp/")
async def resend_otp(request: ResendOTP, db: AsyncSession = Depends(get_db)):
    """
    Resend OTP to the given phone number.
    """
    # Step 1: Verify user exists

    statement = select(OTP).where(OTP.phone_number == request.phone_number)

    result = await db.execute(statement)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Invalid request.")

    response = await send_user_otp(request.phone_number, db)
    if not response.get("success"):
        raise HTTPException(status_code=500, detail="Failed to resend OTP.")

    return {"message": "OTP resent successfully."}


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Query user by phone number
    statement = select(User).where(User.phone_number == login_data.phone_number)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not await verify_password(login_data.pin, user.login_pin):
        raise HTTPException(status_code=401, detail="Invalid PIN")

    # Generate tokens
    access_token = create_access_token({"sub": user.phone_number})
    refresh_token = create_refresh_token({"sub": user.phone_number})

    print(f"{login_data.device_id}  deviceID")
    print(f"{login_data.google_id}  googleID")


    # Save refresh token in the database
    user.refresh_token = refresh_token
    db.add(user)
    await db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_token, REFRESH_SECRET_KEY)
    phone_number = payload.get("sub")

    if not phone_number:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Query user by phone number and validate refresh token
    statement = select(User).where(User.phone_number == phone_number)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user or user.refresh_token != refresh_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Generate new access token
    access_token = create_access_token({"sub": user.phone_number})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get("/secure-data")
async def secure_data(current_user: User = Depends(get_current_user)):
    return {
        "message": f"Welcome {current_user.phone_number}, here is your secure data."
    }
