from pydantic import BaseModel, Field


class Account(BaseModel):
    account_id: int = Field(alias="id")
    name: str

    class Config:
        allow_population_by_field_name = True
        anystr_strip_whitespace = True
        extra = "forbid"
        orm_mode = True


def from_attributes(record):
    return Account.from_orm(record)
