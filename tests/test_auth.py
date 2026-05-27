from app.models import User

from .conftest import csrf_token, login


def test_register_hashes_password_and_assigns_regular_role(client, app):
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
    with app.app_context():
        user = User.query.filter_by(username="newuser").first()
        assert user is not None
        assert user.role == "regular"
        assert user.password_hash != "SecurePass123"
        assert user.check_password("SecurePass123")


def test_login_rejects_invalid_password(client):
    response = login(client, password="wrong-password")
    assert b"Invalid username or password" in response.data


def test_csrf_required_for_post_requests(client):
    response = client.post("/login", data={"username": "adminuser", "password": "AdminPass123!"})
    assert response.status_code == 400

