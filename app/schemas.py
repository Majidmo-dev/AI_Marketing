from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl
from app.models.entities import ContentStatus
class LoginIn(BaseModel): email: EmailStr; password: str
class TokenOut(BaseModel): access_token: str; token_type: str = "bearer"
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; email: EmailStr; full_name: str; is_active: bool
class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=180)
    owner_email: EmailStr
    owner_name: str = Field(min_length=1, max_length=160)
class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; name: str; slug: str; status: str
class InvitationAccept(BaseModel): token: str = Field(min_length=32); full_name: str = Field(min_length=1, max_length=160); password: str = Field(min_length=12, max_length=128)
class BrandUpdate(BaseModel):
    brand_name: str = Field(default="", max_length=180)
    website_url: HttpUrl | None = None
    audience: str = ""
    tone_of_voice: str = Field(default="Clear, helpful, professional", max_length=500)
    prohibited_claims: str = ""
class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    client_id: str; brand_name: str; website_url: str | None; audience: str; tone_of_voice: str; prohibited_claims: str
class ContentGenerateIn(BaseModel):
    client_id: str; topic: str = Field(min_length=3, max_length=500)
    channel: str = Field(pattern=r"^(instagram|facebook|linkedin|tiktok|website)$")
    goal: str = Field(default="engagement", max_length=100); count: int = Field(default=1, ge=1, le=5)
class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; client_id: str; title: str; channel: str; body: str; status: ContentStatus
