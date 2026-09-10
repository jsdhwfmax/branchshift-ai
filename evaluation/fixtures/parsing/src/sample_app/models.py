from pydantic import BaseModel, Field


class Item(BaseModel):
    quantity: int = Field(gt=0)


class Order(BaseModel):
    item: Item


def parse_item(payload):
    return Item.parse_obj(payload)


def parse_item_json(payload):
    return Item.parse_raw(payload)


def parse_order(payload):
    return Order.parse_obj(payload)
