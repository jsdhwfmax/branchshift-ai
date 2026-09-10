from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Receipt(BaseModel):
    receipt_id: int = Field(alias="id")
    issued_at: datetime
    note: Optional[str] = None


class Bundle(BaseModel):
    receipt: Receipt


def as_payload(receipt):
    return receipt.dict(by_alias=True, exclude_none=True)


def as_json(receipt):
    return receipt.json(by_alias=True, exclude_none=True)


def bundle_payload(bundle):
    return bundle.dict(by_alias=True, exclude_none=True)
