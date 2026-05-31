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


def test_admin_can_delete_user_profile(client, app):
    login(client)
    response = client.post(
        "/users/2/delete",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

    assert b"deleted" in response.data
    assert app.config["REPOSITORY"].get_user(2) is None


def test_admin_deleting_user_returns_their_books(client, app):
    login(client, "regularuser", "RegularPass123!")
    client.post(
        "/books/1/checkout",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

    login(client)
    response = client.post(
        "/users/2/delete",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

    book = app.config["REPOSITORY"].get_book(1)
    assert b"deleted" in response.data
    assert book["status"] == "available"
    assert book["checked_out_by_id"] is None
    assert app.config["REPOSITORY"].loans[0]["returned_at"] is not None
    assert app.config["REPOSITORY"].loans[0]["actioned_by_id"] == 1


def test_regular_user_can_delete_own_account(client, app):
    login(client, "regularuser", "RegularPass123!")
    response = client.post(
        "/account/delete",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

    assert b"Your account has been deleted" in response.data
    assert app.config["REPOSITORY"].get_user(2) is None


def test_self_deleting_user_returns_their_books(client, app):
    login(client, "regularuser", "RegularPass123!")
    client.post(
        "/books/1/checkout",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )
    response = client.post(
        "/account/delete",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

    book = app.config["REPOSITORY"].get_book(1)
    assert b"Your account has been deleted" in response.data
    assert book["status"] == "available"
    assert book["checked_out_by_id"] is None
    assert app.config["REPOSITORY"].loans[0]["returned_at"] is not None
    assert app.config["REPOSITORY"].loans[0]["actioned_by_id"] == 2
