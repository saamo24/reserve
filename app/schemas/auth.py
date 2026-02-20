"""Auth request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr = Field(..., min_length=1, description="Admin email")
    password: str = Field(..., min_length=1, description="Admin password")


class RefreshRequest(BaseModel):
    """Refresh token request body."""

    refresh_token: str = Field(..., min_length=1, description="Refresh JWT")


class TokenResponse(BaseModel):
    """JWT token response (login and refresh)."""

    access_token: str = Field(..., description="Short-lived access JWT")
    refresh_token: str = Field(..., description="Long-lived refresh JWT")
    token_type: str = Field(default="bearer", description="Token type")
