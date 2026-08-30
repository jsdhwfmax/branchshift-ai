from .models import Project, User


def parse_user(payload: dict) -> User:
    return User.parse_obj(payload)


def serialize_user(user: User) -> dict:
    return user.dict(by_alias=True, exclude_none=True)


def parse_project_json(payload: str) -> Project:
    return Project.parse_raw(payload)

