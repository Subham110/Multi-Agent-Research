from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    tenant_slug: str = Field(default="default", min_length=2, max_length=80)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    full_name: str = Field(min_length=2, max_length=160)
    tenant_slug: str = Field(default="default", min_length=2, max_length=80)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    tenant_id: str
    tenant_slug: str


class WSTicketResponse(BaseModel):
    ticket: str
    expires_in: int = 60
