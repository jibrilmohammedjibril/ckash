from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import UUID, uuid4


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    first_name: str = Field(nullable=False, index=True)
    last_name: str = Field(nullable=False, index=True)
    phone_number: str = Field(nullable=False, unique=True)
    login_pin: str = Field(nullable=False)
    device_id: Optional[str] = Field(default=None)
    profile_picture: Optional[str] = Field(default=None)
    created_date: datetime = Field(default_factory=lambda: datetime.now())


class InitUser(SQLModel, table=True):
    __tablename__ = "initusers"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    first_name: str = Field(nullable=False, index=True)
    last_name: str = Field(nullable=False, index=True)
    phone_number: str = Field(nullable=False, unique=True)
    login_pin: str = Field(nullable=False)
    profile_picture: Optional[str] = Field(default=None)


class OTP(SQLModel, table=True):
    __tablename__ = "otp"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    phone_number: str = Field(nullable=False, index=True)
    otp_code: str = Field(nullable=False, index=True)
    created_date: datetime = Field(default_factory=lambda: datetime.now())
    is_valid: bool = Field(default=True)
