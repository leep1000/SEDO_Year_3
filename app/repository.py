from copy import deepcopy
from datetime import datetime, timezone

from flask import current_app
from supabase import create_client


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class SupabaseRepository:
    def __init__(self, url, key):
        self.client = create_client(url, key)

    def find_user_by_username(self, username):
        response = (
            self.client.table("users")
            .select("*")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def list_users(self):
        return self.client.table("users").select("*").order("username").execute().data

    def get_user(self, user_id):
        response = self.client.table("users").select("*").eq("id", user_id).limit(1).execute()
        return response.data[0] if response.data else None

    def create_user(self, username, password_hash, role="regular"):
        response = (
            self.client.table("users")
            .insert({"username": username, "password_hash": password_hash, "role": role})
            .execute()
        )
        return response.data[0]

    def update_user(self, user_id, values):
        response = self.client.table("users").update(values).eq("id", user_id).execute()
        return response.data[0] if response.data else None

    def delete_user(self, user_id):
        self.return_books_for_user(user_id, user_id)
        self.client.table("users").delete().eq("id", user_id).execute()

    def list_books(self, query=""):
        response = self.client.table("books").select("*").order("title").execute()
        books = response.data
        if query:
            q = query.lower()
            books = [
                book
                for book in books
                if q in book["title"].lower()
                or q in book["author"].lower()
                or q in book["isbn"].lower()
            ]
        return [self.enrich_book(book) for book in books]

    def get_book(self, book_id):
        response = self.client.table("books").select("*").eq("id", book_id).limit(1).execute()
        return self.enrich_book(response.data[0]) if response.data else None

    def create_book(self, values):
        response = self.client.table("books").insert(values).execute()
        return response.data[0]

    def update_book(self, book_id, values):
        values["updated_at"] = now_iso()
        response = self.client.table("books").update(values).eq("id", book_id).execute()
        return response.data[0] if response.data else None

    def delete_book(self, book_id):
        self.client.table("books").delete().eq("id", book_id).execute()

    def create_loan(self, book_id, user_id, actioned_by_id):
        response = (
            self.client.table("loans")
            .insert(
                {
                    "book_id": book_id,
                    "user_id": user_id,
                    "actioned_by_id": actioned_by_id,
                }
            )
            .execute()
        )
        return response.data[0]

    def close_active_loan(self, book_id, actioned_by_id):
        active = (
            self.client.table("loans")
            .select("*")
            .eq("book_id", book_id)
            .is_("returned_at", "null")
            .order("checked_out_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if active:
            self.client.table("loans").update(
                {"returned_at": now_iso(), "actioned_by_id": actioned_by_id}
            ).eq("id", active[0]["id"]).execute()

    def return_books_for_user(self, user_id, actioned_by_id):
        checked_out_books = (
            self.client.table("books")
            .select("id")
            .eq("checked_out_by_id", user_id)
            .execute()
            .data
        )
        for book in checked_out_books:
            self.close_active_loan(book["id"], actioned_by_id)
        self.client.table("books").update(
            {"status": "available", "checked_out_by_id": None, "updated_at": now_iso()}
        ).eq("checked_out_by_id", user_id).execute()

    def enrich_book(self, book):
        book = dict(book)
        book["checked_out_user"] = (
            self.get_user(book["checked_out_by_id"]) if book.get("checked_out_by_id") else None
        )
        book["loans"] = (
            self.client.table("loans").select("*").eq("book_id", book["id"]).execute().data
        )
        return book


class InMemoryRepository:
    def __init__(self):
        self.users = []
        self.books = []
        self.loans = []
        self._user_id = 1
        self._book_id = 1
        self._loan_id = 1

    def find_user_by_username(self, username):
        return next((u for u in self.users if u["username"] == username), None)

    def list_users(self):
        return sorted(deepcopy(self.users), key=lambda u: u["username"])

    def get_user(self, user_id):
        user = next((u for u in self.users if u["id"] == int(user_id)), None)
        return deepcopy(user) if user else None

    def create_user(self, username, password_hash, role="regular"):
        user = {
            "id": self._user_id,
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "created_at": now_iso(),
        }
        self._user_id += 1
        self.users.append(user)
        return deepcopy(user)

    def update_user(self, user_id, values):
        user = self._find(self.users, user_id)
        if user:
            user.update(values)
        return deepcopy(user)

    def delete_user(self, user_id):
        self.return_books_for_user(user_id, user_id)
        self.users = [u for u in self.users if u["id"] != int(user_id)]

    def list_books(self, query=""):
        books = sorted(deepcopy(self.books), key=lambda b: b["title"])
        if query:
            q = query.lower()
            books = [
                b
                for b in books
                if q in b["title"].lower() or q in b["author"].lower() or q in b["isbn"].lower()
            ]
        return [self.enrich_book(book) for book in books]

    def get_book(self, book_id):
        book = self._find(self.books, book_id)
        return self.enrich_book(deepcopy(book)) if book else None

    def create_book(self, values):
        book = {
            "id": self._book_id,
            "status": "available",
            "checked_out_by_id": None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            **values,
        }
        self._book_id += 1
        self.books.append(book)
        return deepcopy(book)

    def update_book(self, book_id, values):
        book = self._find(self.books, book_id)
        if book:
            book.update(values)
            book["updated_at"] = now_iso()
        return deepcopy(book)

    def delete_book(self, book_id):
        self.books = [b for b in self.books if b["id"] != int(book_id)]
        self.loans = [l for l in self.loans if l["book_id"] != int(book_id)]

    def create_loan(self, book_id, user_id, actioned_by_id):
        loan = {
            "id": self._loan_id,
            "book_id": int(book_id),
            "user_id": int(user_id),
            "checked_out_at": now_iso(),
            "returned_at": None,
            "actioned_by_id": int(actioned_by_id),
        }
        self._loan_id += 1
        self.loans.append(loan)
        return deepcopy(loan)

    def close_active_loan(self, book_id, actioned_by_id):
        active = [
            loan
            for loan in self.loans
            if loan["book_id"] == int(book_id) and loan["returned_at"] is None
        ]
        if active:
            active[-1]["returned_at"] = now_iso()
            active[-1]["actioned_by_id"] = int(actioned_by_id)

    def return_books_for_user(self, user_id, actioned_by_id):
        for book in self.books:
            if book.get("checked_out_by_id") == int(user_id):
                self.close_active_loan(book["id"], actioned_by_id)
                book["checked_out_by_id"] = None
                book["status"] = "available"
                book["updated_at"] = now_iso()

    def enrich_book(self, book):
        book["checked_out_user"] = (
            self.get_user(book["checked_out_by_id"]) if book.get("checked_out_by_id") else None
        )
        book["loans"] = [deepcopy(l) for l in self.loans if l["book_id"] == book["id"]]
        return book

    def _find(self, records, record_id):
        return next((record for record in records if record["id"] == int(record_id)), None)


def get_repository():
    return current_app.config["REPOSITORY"]
