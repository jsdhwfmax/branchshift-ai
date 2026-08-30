import pytest
from pydantic import ValidationError

from sample_app.models import Project, User


def valid_user(**overrides):
    data = {"id": 7, "name": "Ada", "email": "ADA@EXAMPLE.COM"}
    data.update(overrides)
    return User.parse_obj(data)


def test_alias_populates_user_id():
    assert valid_user().user_id == 7


def test_field_name_can_populate_user_id():
    assert User(user_id=8, name="Ada", email="a@example.com").user_id == 8


def test_name_is_trimmed():
    assert valid_user(name="  Ada  ").name == "Ada"


def test_blank_name_is_rejected():
    with pytest.raises(ValidationError):
        valid_user(name="   ")


def test_email_is_normalized():
    assert valid_user().email == "ada@example.com"


def test_nickname_must_differ():
    with pytest.raises(ValidationError):
        valid_user(nickname="Ada")


def test_none_is_excluded_when_requested():
    assert "nickname" not in valid_user().dict(exclude_none=True)


def test_alias_is_used_during_serialization():
    payload = valid_user().dict(by_alias=True)
    assert payload["id"] == 7 and "user_id" not in payload


def test_project_accepts_nested_user():
    assert Project(slug="demo", owner=valid_user()).owner.name == "Ada"


def test_project_rejects_uppercase_slug():
    with pytest.raises(ValidationError):
        Project(slug="Demo", owner=valid_user())

