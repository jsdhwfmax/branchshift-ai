import json
from datetime import datetime

from sample_app.models import Bundle, Receipt, as_json, as_payload, bundle_payload


def receipt():
    return Receipt(id=7, issued_at=datetime(2026, 1, 2, 3, 4, 5))


def test_dictionary_alias():
    payload = as_payload(receipt())
    assert payload["id"] == 7 and "receipt_id" not in payload


def test_none_is_omitted():
    assert "note" not in as_payload(receipt())


def test_json_datetime_contract():
    assert json.loads(as_json(receipt())) == {"id": 7, "issued_at": "2026-01-02T03:04:05"}


def test_nested_alias_and_exclusion():
    payload = bundle_payload(Bundle(receipt=receipt()))
    assert payload["receipt"]["id"] == 7 and "note" not in payload["receipt"]
