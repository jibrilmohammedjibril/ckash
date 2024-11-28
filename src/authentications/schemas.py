from pydantic import BaseModel


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    login_pin: str


class SigninRequest(BaseModel):
    phone_number: str


class OTPRequest(BaseModel):
    phone_number: str
    identifier: str


class VerifyOTPRequest(BaseModel):
    phone_number: str
    identifier: str
    otp: str
