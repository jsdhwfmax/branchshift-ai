from sample_app.api import parse_project_json, parse_user, serialize_user


def test_parse_obj_boundary():
    assert parse_user({"id": 3, "name": "Lin", "email": "L@E.COM"}).email == "l@e.com"


def test_dict_boundary():
    payload = serialize_user(parse_user({"id": 3, "name": "Lin", "email": "l@e.com"}))
    assert payload == {"id": 3, "name": "Lin", "email": "l@e.com", "created_at": payload["created_at"]}


def test_parse_raw_boundary():
    project = parse_project_json(
        '{"slug":"branchshift","owner":{"id":3,"name":"Lin","email":"l@e.com"}}'
    )
    assert project.slug == "branchshift"

