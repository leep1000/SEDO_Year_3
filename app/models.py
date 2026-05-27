from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="regular")
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_books = relationship(
        "Book",
        back_populates="created_by_user",
        foreign_keys="Book.created_by_id",
        passive_deletes=True,
    )
    checked_out_books = relationship(
        "Book",
        back_populates="checked_out_user",
        foreign_keys="Book.checked_out_by_id",
        passive_deletes=True,
    )
    loans = relationship(
        "Loan",
        back_populates="user",
        foreign_keys="Loan.user_id",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("role in ('regular', 'admin')", name="check_user_role"),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    publication_year = db.Column(db.Integer, nullable=False)
    isbn = db.Column(db.String(20), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="available")
    created_by_id = db.Column(db.Integer, ForeignKey("users.id", ondelete="SET NULL"))
    checked_out_by_id = db.Column(db.Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_by_user = relationship(
        "User",
        back_populates="created_books",
        foreign_keys=[created_by_id],
    )
    checked_out_user = relationship(
        "User",
        back_populates="checked_out_books",
        foreign_keys=[checked_out_by_id],
    )
    loans = relationship(
        "Loan",
        back_populates="book",
        foreign_keys="Loan.book_id",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "publication_year >= 1600 AND publication_year <= 2030",
            name="check_publication_year_range",
        ),
        CheckConstraint("status in ('available', 'checked_out')", name="check_book_status"),
        UniqueConstraint("isbn", name="uq_books_isbn"),
    )


class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, ForeignKey("users.id", ondelete="SET NULL"))
    checked_out_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    returned_at = db.Column(db.DateTime(timezone=True))
    actioned_by_id = db.Column(db.Integer, ForeignKey("users.id", ondelete="SET NULL"))

    book = relationship("Book", back_populates="loans", foreign_keys=[book_id])
    user = relationship("User", back_populates="loans", foreign_keys=[user_id])
    actioned_by = relationship("User", foreign_keys=[actioned_by_id])

    __table_args__ = (
        CheckConstraint(
            "returned_at is null or returned_at >= checked_out_at",
            name="check_loan_return_after_checkout",
        ),
    )
