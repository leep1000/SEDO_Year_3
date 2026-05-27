import os

from . import db
from .models import Book, Loan, User


def seed_database():
    db.create_all()

    admin_username = os.getenv("ADMIN_USERNAME", "adminuser")
    admin_password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(username=admin_username, role="admin")
        admin.set_password(admin_password)
        db.session.add(admin)

    regular = User.query.filter_by(username="regularuser").first()
    if not regular:
        regular = User(username="regularuser", role="regular")
        regular.set_password("RegularPass123!")
        db.session.add(regular)

    db.session.commit()

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
        if not Book.query.filter_by(isbn=isbn).first():
            db.session.add(
                Book(
                    title=title,
                    author=author,
                    publication_year=year,
                    isbn=isbn,
                    created_by_id=admin.id,
                )
            )
    db.session.commit()
