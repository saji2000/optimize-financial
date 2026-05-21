from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUserRead(BaseModel):
    username: str
    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserRead
