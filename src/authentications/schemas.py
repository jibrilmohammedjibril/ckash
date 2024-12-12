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
    otp: str


class LoginRequest(BaseModel):
    phone_number: str
    pin: str
    device_id: str
    google_id: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class VerifyOTPSignup(BaseModel):
    phone_number: str
    otp: str


class VerifyOTPSignin(BaseModel):
    phone_number: str
    otp: str
    device_id: str


class ForgotLoginPin(BaseModel):
    phone_number: str


class ResetLoginPin(BaseModel):
    phone_number: str
    otp: str
    new_login_pin: str


class ResendOTP(BaseModel):
    phone_number: str
