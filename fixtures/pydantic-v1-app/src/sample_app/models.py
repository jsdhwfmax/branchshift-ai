from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, root_validator, validator


class User(BaseModel):
    user_id: int = Field(alias="id")
    name: str
    email: str
    nickname: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("name")
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()

    @validator("email")
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @root_validator(skip_on_failure=True)
    def nickname_differs_from_name(cls, values):
        if values.get("nickname") == values.get("name"):
            raise ValueError("nickname must differ from name")
        return values

    class Config:
        allow_population_by_field_name = True
        anystr_strip_whitespace = True
        orm_mode = True


class Project(BaseModel):
    slug: str
    owner: User
    archived: bool = False

    @validator("slug")
    def slug_is_lowercase(cls, value: str) -> str:
        if value != value.lower():
            raise ValueError("slug must be lowercase")
        return value
