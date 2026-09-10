import pytest

from sample_app.models import bridge_payload, current_payload, legacy_payload


def test_current_import_coercion():
    assert current_payload({"quantity": "2"}) == {"quantity": 2}


def test_compatibility_import_coercion():
    assert legacy_payload({"quantity": "3"}) == {"quantity": 3}


def test_dictionary_bridge():
    assert bridge_payload({"quantity": "4"}) == {"quantity": 4}


def test_both_boundaries_reject_invalid_integer():
    # The v1 and v2 ValidationError classes need not be identical.
    for parse in (current_payload, legacy_payload):
        with pytest.raises(ValueError):
            parse({"quantity": "not-an-integer"})
