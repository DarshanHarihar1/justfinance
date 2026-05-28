from pydantic import BaseModel


class LoginBody(BaseModel):
    password: str


class MeOut(BaseModel):
    authenticated: bool = True
