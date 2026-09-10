from pydantic import BaseModel
from pydantic.v1 import BaseModel as LegacyBaseModel


class CurrentItem(BaseModel):
    quantity: int


class LegacyItem(LegacyBaseModel):
    quantity: int


def current_payload(payload):
    return CurrentItem.parse_obj(payload).dict()


def legacy_payload(payload):
    return LegacyItem.parse_obj(payload).dict()


def bridge_payload(payload):
    # A plain dictionary is the explicit boundary between model generations.
    return current_payload(legacy_payload(payload))
