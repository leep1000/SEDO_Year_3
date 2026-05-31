from .conftest import csrf_token, login


def test_register_creates_supabase_auth_profile_and_assigns_regular_role(client, app):
    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "password": "SecurePass123",
            "_csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    user = app.config["REPOSITORY"].find_user_by_username("newuser")
    assert user is not None
    assert user["role"] == "regular"
    assert user["auth_user_id"]
    assert user["password_hash"] != "SecurePass123"


def test_login_rejects_invalid_password(client):
    response = login(client, password="wrong-password")
    assert b"Invalid username or password" in response.data


def test_login_stores_supabase_jwt_session(client):
    login(client)
    with client.session_transaction() as sess:
        assert sess["supabase_access_token"]
        assert sess["supabase_refresh_token"]


def test_csrf_required_for_post_requests(client):
    response = client.post("/login", data={"username": "adminuser", "password": "AdminPass123!"})
    assert response.status_code == 400
