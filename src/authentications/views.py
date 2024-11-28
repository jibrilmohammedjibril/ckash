from .models import User
from .schemas import SigninRequest, SignupRequest
from .services import send_user_otp
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

    # Send OTP
    response = await send_user_otp(request.phone_number, db)
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
