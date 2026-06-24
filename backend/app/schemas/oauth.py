from pydantic import BaseModel


class OAuthStartResponse(BaseModel):
    authorization_url: str
