import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone
from src.authentications.models import User, OTP
from src.authentications.services import generate_otp


@pytest.mark.asyncio
async def test_signup(async_client: AsyncClient, test_db):
    response = await async_client.post(
        "/auth/signup/",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "1234567890",
            "login_pin": "1234"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Signup successful. OTP sent."
    assert "profile_picture" in data
    assert data["response"]["success"]


@pytest.mark.asyncio
async def test_signin(async_client: AsyncClient, test_db):
    # Create a mock user in the test database
    user = User(
        first_name="John",
        last_name="Doe",
        phone_number="1234567890",
        login_pin="1234"
    )
    test_db.add(user)
    await test_db.commit()

    # Call the signin endpoint
    response = await async_client.post(
        "/auth/signin/",
        json={"phone_number": "1234567890"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Signin successful. OTP sent."


@pytest.mark.asyncio
async def test_verify_otp_signup(async_client: AsyncClient, test_db):
    # Create a mock OTP in the database
    otp = OTP(
        phone_number="1234567890",
        otp_code="567890",
        is_valid=True,
        created_date=datetime.now(timezone.utc)
    )
    test_db.add(otp)
    await test_db.commit()

    # Verify the OTP
    response = await async_client.post(
        "/auth/verify-otp_signup/",
        json={"phone_number": "1234567890", "otp": "567890"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert data["message"] == "OTP verified successfully."


@pytest.mark.asyncio
async def test_forgot_login_pin(async_client: AsyncClient, test_db):
    # Add a mock user to the database
    user = User(
        first_name="Jane",
        last_name="Doe",
        phone_number="0987654321",
        login_pin="5678"
    )
    test_db.add(user)
    await test_db.commit()

    # Call the forgot login pin endpoint
    response = await async_client.post(
        "/auth/forgot-login-pin/",
        json={"phone_number": "0987654321"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "OTP sent successfully."


@pytest.mark.asyncio
async def test_reset_login_pin(async_client: AsyncClient, test_db):
    # Create a mock user and OTP in the database
    user = User(
        first_name="Jane",
        last_name="Doe",
        phone_number="0987654321",
        login_pin="5678"
    )
    otp = OTP(
        phone_number="0987654321",
        otp_code="987654",
        is_valid=True,
        created_date=datetime.now(timezone.utc)
    )
    test_db.add(user)
    test_db.add(otp)
    await test_db.commit()

    # Reset the login pin
    response = await async_client.post(
        "/auth/reset-login-pin/",
        json={
            "phone_number": "0987654321",
            "otp": "987654",
            "new_login_pin": "4321"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login PIN reset successfully."
