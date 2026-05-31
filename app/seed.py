import os

from .repository import get_repository


def seed_database():
    repo = get_repository()

    admin_username = os.getenv("ADMIN_USERNAME", "adminuser")
    admin_password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")

    admin = _ensure_seed_user(repo, admin_username, admin_password, "admin")
    _ensure_seed_user(repo, "regularuser", "RegularPass123!", "regular")

    sample_books = [
        ("The C# Player's Guide", "RB Whitaker", 2022, "9780985580131"),
        ("PL-200 Exam Guide", "Julian Sharp", 2020, "9781803246617"),
        ("The Pragmatic Programmer", "David Thomas", 2019, "9780135957059"),
        ("Never Split the Difference", "Chris Voss", 2017, "9781847941497"),
        ("Cloud Computing Basics", "Anders Lisdorf", 2021, "9781484266053"),
        ("Python Programming Bible", "Philip Robbins", 2023, "9781800208700"),
        ("Thinking in Systems", "Donella Meadows", 2017, "9781603580557"),
        ("The Art of Unit Testing", "Roy Osherove", 2013, "9781617290893"),
        ("Clean Code", "Robert C. Martin", 2008, "9780132350884"),
        ("Accelerate", "Nicole Forsgren", 2018, "9781942788331"),
    ]

    for title, author, year, isbn in sample_books:
        if not any(book["isbn"] == isbn for book in repo.list_books(use_service=True)):
            repo.create_book(
                {
                    "title": title,
                    "author": author,
                    "publication_year": year,
                    "isbn": isbn,
                    "amazon_url": f"https://www.amazon.co.uk/s?k={isbn}",
                    "created_by_id": admin["id"],
                    "status": "available",
                    "checked_out_by_id": None,
                },
                use_service=True,
            )


def _ensure_seed_user(repo, username, password, role):
    user = repo.find_user_by_username(username, use_service=True)
    if not user:
        return repo.create_user(username, password, role)
    if not user.get("auth_user_id"):
        return repo.link_user_to_auth(user["id"], username, password, role)
    return user
