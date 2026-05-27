from .conftest import csrf_token, login


def test_users_page_is_admin_only(client):
    login(client, "regularuser", "RegularPass123!")
    response = client.get("/users", follow_redirects=True)
    assert b"You do not have permission" in response.data


def test_admin_can_promote_user(client):
    login(client)
    response = client.post(
        "/users/2/edit",
        data={
            "username": "regularuser",
            "role": "admin",
            "_csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )
    assert b"User updated successfully" in response.data

