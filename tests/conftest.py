import pytest

from app import create_app, db
from app.models import Book, User


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": True,
        }
    )
    with app.app_context():
        db.create_all()
        admin = User(username="adminuser", role="admin")
        admin.set_password("AdminPass123!")
        regular = User(username="regularuser", role="regular")
        regular.set_password("RegularPass123!")
        db.session.add_all([admin, regular])
        db.session.commit()
        db.session.add(
            Book(
                title="Clean Code",
                author="Robert C. Martin",
                publication_year=2008,
                isbn="9780132350884",
                created_by_id=admin.id,
            )
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf_token(client):
    with client.session_transaction() as sess:
        token = sess.get("_csrf_token")
        if not token:
            token = "test-csrf-token"
            sess["_csrf_token"] = token
        return token


def login(client, username="adminuser", password="AdminPass123!"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

