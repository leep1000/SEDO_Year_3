import os

from werkzeug.security import generate_password_hash

from .repository import get_repository


def seed_database():
    repo = get_repository()

    admin_username = os.getenv("ADMIN_USERNAME", "adminuser")
    admin_password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")

    admin = repo.find_user_by_username(admin_username)
    if not admin:
        admin = repo.create_user(admin_username, generate_password_hash(admin_password), "admin")

    regular = repo.find_user_by_username("regularuser")
    if not regular:
        repo.create_user("regularuser", generate_password_hash("RegularPass123!"), "regular")

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
        if not any(book["isbn"] == isbn for book in repo.list_books()):
            repo.create_book(
                {
                    "title": title,
                    "author": author,
                    "publication_year": year,
                    "isbn": isbn,
                    "created_by_id": admin["id"],
                    "status": "available",
                    "checked_out_by_id": None,
                }
            )
