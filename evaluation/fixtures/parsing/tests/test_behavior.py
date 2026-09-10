import pytest
from pydantic import ValidationError

from sample_app.models import parse_item, parse_item_json, parse_order


def test_mapping_input_coercion():
    assert parse_item({"quantity": "3"}).quantity == 3


def test_json_input():
    assert parse_item_json('{"quantity": 4}').quantity == 4


def test_nested_input():
    assert parse_order({"item": {"quantity": 5}}).item.quantity == 5


def test_invalid_quantity_is_rejected():
    with pytest.raises(ValidationError):
        parse_item({"quantity": 0})
