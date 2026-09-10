from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from sample_app.models import Account, from_attributes


def test_alias_input():
    assert Account(id=4, name="Ada").account_id == 4


def test_field_name_input():
    assert Account(account_id=5, name="Ada").account_id == 5


def test_string_whitespace():
    assert Account(id=4, name="  Ada  ").name == "Ada"


def test_extra_is_rejected():
    with pytest.raises(ValidationError):
        Account(id=4, name="Ada", admin=True)


def test_attribute_record():
    account = from_attributes(SimpleNamespace(id=9, name="  Lin  "))
    assert (account.account_id, account.name) == (9, "Lin")
