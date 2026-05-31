from copy import deepcopy
from datetime import datetime, timezone

from flask import current_app, has_request_context, session
from supabase import create_client
from werkzeug.security import check_password_hash, generate_password_hash


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class SupabaseRepository:
    def __init__(self, url, anon_key, service_role_key=None):
        self.url = url
        self.anon_key = anon_key
        self.service_role_key = service_role_key
        self.auth_client = create_client(url, anon_key)
        self.service_client = create_client(url, service_role_key) if service_role_key else None

    def _client(self, use_service=False):
        if use_service:
            if not self.service_client:
                raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for this operation.")
            return self.service_client

        client = create_client(self.url, self.anon_key)
        token = session.get("supabase_access_token") if has_request_context() else None
        if token:
            client.postgrest.auth(token)
        return client

    def _auth_email(self, username):
        return f"{username.strip().lower()}@sedo-library.local"

    def authenticate_user(self, username, password):
        response = self.auth_client.auth.sign_in_with_password(
            {"email": self._auth_email(username), "password": password}
        )
        if not response.session or not response.user:
            return None
        profile = self.find_user_by_auth_id(response.user.id, use_service=True)
        if not profile:
            return None
        return {
            "user": profile,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "expires_at": response.session.expires_at,
        }

    def refresh_auth_session(self, refresh_token):
        response = self.auth_client.auth.refresh_session(refresh_token)
        if not response.session:
            return None
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "expires_at": response.session.expires_at,
        }

    def find_user_by_username(self, username, use_service=False):
        response = (
            self._client(use_service=use_service)
            .table("users")
            .select("*")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def find_user_by_auth_id(self, auth_user_id, use_service=False):
        response = (
            self._client(use_service=use_service)
            .table("users")
            .select("*")
            .eq("auth_user_id", auth_user_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def list_users(self):
        return self._client().table("users").select("*").order("username").execute().data

    def get_user(self, user_id, use_service=False):
        response = (
            self._client(use_service=use_service)
            .table("users")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def create_user(self, username, password, role="regular"):
        if not self.service_client:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required to create Supabase Auth users.")
        auth_response = self.service_client.auth.admin.create_user(
            {
                "email": self._auth_email(username),
                "password": password,
                "email_confirm": True,
                "user_metadata": {"username": username},
            }
        )
        auth_user_id = auth_response.user.id
        try:
            response = (
                self._client(use_service=True)
                .table("users")
                .insert({"username": username, "auth_user_id": auth_user_id, "role": role})
                .execute()
            )
        except Exception:
            self.service_client.auth.admin.delete_user(auth_user_id)
            raise
        return response.data[0]

    def link_user_to_auth(self, user_id, username, password, role="regular"):
        if not self.service_client:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required to create Supabase Auth users.")
        auth_response = self.service_client.auth.admin.create_user(
            {
                "email": self._auth_email(username),
                "password": password,
                "email_confirm": True,
                "user_metadata": {"username": username},
            }
        )
        auth_user_id = auth_response.user.id
        try:
            response = (
                self._client(use_service=True)
                .table("users")
                .update({"auth_user_id": auth_user_id, "role": role})
                .eq("id", user_id)
                .execute()
            )
        except Exception:
            self.service_client.auth.admin.delete_user(auth_user_id)
            raise
        return response.data[0] if response.data else None

    def update_user(self, user_id, values):
        user = self.get_user(user_id)
        response = self._client().table("users").update(values).eq("id", user_id).execute()
        if (
            user
            and user.get("auth_user_id")
            and values.get("username")
            and self.service_client
        ):
            self.service_client.auth.admin.update_user_by_id(
                user["auth_user_id"],
                {
                    "email": self._auth_email(values["username"]),
                    "user_metadata": {"username": values["username"]},
                },
            )
        return response.data[0] if response.data else None

    def delete_user(self, user_id, actioned_by_id=None):
        user = self.get_user(user_id)
        self.return_books_for_user(user_id, actioned_by_id or user_id)
        self._client().table("users").delete().eq("id", user_id).execute()
        if user and user.get("auth_user_id") and self.service_client:
            self.service_client.auth.admin.delete_user(user["auth_user_id"])

    def list_books(self, query="", use_service=False):
        response = (
            self._client(use_service=use_service)
            .table("books")
            .select("*")
            .order("title")
            .execute()
        )
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
        return [self.enrich_book(book, use_service=use_service) for book in books]

    def get_book(self, book_id):
        response = self._client().table("books").select("*").eq("id", book_id).limit(1).execute()
        return self.enrich_book(response.data[0]) if response.data else None

    def create_book(self, values, use_service=False):
        response = self._client(use_service=use_service).table("books").insert(values).execute()
        return response.data[0]

    def update_book(self, book_id, values):
        values["updated_at"] = now_iso()
        response = self._client().table("books").update(values).eq("id", book_id).execute()
        return response.data[0] if response.data else None

    def delete_book(self, book_id):
        self._client().table("books").delete().eq("id", book_id).execute()

    def create_loan(self, book_id, user_id, actioned_by_id):
        response = (
            self._client()
            .table("loans")
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
            self._client()
            .table("loans")
            .select("*")
            .eq("book_id", book_id)
            .is_("returned_at", "null")
            .order("checked_out_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if active:
            self._client().table("loans").update(
                {"returned_at": now_iso(), "actioned_by_id": actioned_by_id}
            ).eq("id", active[0]["id"]).execute()

    def return_books_for_user(self, user_id, actioned_by_id):
        checked_out_books = (
            self._client()
            .table("books")
            .select("id")
            .eq("checked_out_by_id", user_id)
            .execute()
            .data
        )
        for book in checked_out_books:
            self.close_active_loan(book["id"], actioned_by_id)
        self._client().table("books").update(
            {"status": "available", "checked_out_by_id": None, "updated_at": now_iso()}
        ).eq("checked_out_by_id", user_id).execute()

    def list_loans(self, filters=None):
        filters = filters or {}
        query = self._client().table("loans").select("*").order("checked_out_at", desc=True)
        if filters.get("user_id"):
            query = query.eq("user_id", filters["user_id"])
        if filters.get("book_id"):
            query = query.eq("book_id", filters["book_id"])
        if filters.get("start_date"):
            query = query.gte("checked_out_at", f"{filters['start_date']}T00:00:00+00:00")
        if filters.get("end_date"):
            query = query.lte("checked_out_at", f"{filters['end_date']}T23:59:59+00:00")
        return [self.enrich_loan(loan) for loan in query.execute().data]

    def enrich_loan(self, loan):
        loan = dict(loan)
        loan["user"] = self.get_user(loan["user_id"]) if loan.get("user_id") else None
        loan["actioned_by"] = (
            self.get_user(loan["actioned_by_id"]) if loan.get("actioned_by_id") else None
        )
        book_response = (
            self._client().table("books").select("*").eq("id", loan["book_id"]).limit(1).execute()
        )
        loan["book"] = book_response.data[0] if book_response.data else None
        return loan

    def enrich_book(self, book, use_service=False):
        book = dict(book)
        book["checked_out_user"] = (
            self.get_user(book["checked_out_by_id"], use_service=use_service)
            if book.get("checked_out_by_id")
            else None
        )
        book["loans"] = (
            self._client(use_service=use_service)
            .table("loans")
            .select("*")
            .eq("book_id", book["id"])
            .execute()
            .data
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

    def find_user_by_username(self, username, use_service=False):
        return next((u for u in self.users if u["username"] == username), None)

    def authenticate_user(self, username, password):
        user = self.find_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            return {
                "user": deepcopy(user),
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "expires_at": None,
            }
        return None

    def refresh_auth_session(self, refresh_token):
        return {
            "access_token": "test-access-token",
            "refresh_token": refresh_token,
            "expires_at": None,
        }

    def list_users(self):
        return sorted(deepcopy(self.users), key=lambda u: u["username"])

    def get_user(self, user_id):
        user = next((u for u in self.users if u["id"] == int(user_id)), None)
        return deepcopy(user) if user else None

    def create_user(self, username, password, role="regular"):
        user = {
            "id": self._user_id,
            "username": username,
            "password_hash": generate_password_hash(password),
            "auth_user_id": f"test-auth-user-{self._user_id}",
            "role": role,
            "created_at": now_iso(),
        }
        self._user_id += 1
        self.users.append(user)
        return deepcopy(user)

    def link_user_to_auth(self, user_id, username, password, role="regular"):
        user = self._find(self.users, user_id)
        if user:
            user["username"] = username
            user["password_hash"] = generate_password_hash(password)
            user["role"] = role
            user["auth_user_id"] = user.get("auth_user_id") or f"test-auth-user-{user_id}"
        return deepcopy(user)

    def update_user(self, user_id, values):
        user = self._find(self.users, user_id)
        if user:
            user.update(values)
        return deepcopy(user)

    def delete_user(self, user_id, actioned_by_id=None):
        self.return_books_for_user(user_id, actioned_by_id or user_id)
        self.users = [u for u in self.users if u["id"] != int(user_id)]

    def list_books(self, query="", use_service=False):
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

    def create_book(self, values, use_service=False):
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

    def list_loans(self, filters=None):
        filters = filters or {}
        loans = deepcopy(self.loans)
        if filters.get("user_id"):
            loans = [loan for loan in loans if loan["user_id"] == int(filters["user_id"])]
        if filters.get("book_id"):
            loans = [loan for loan in loans if loan["book_id"] == int(filters["book_id"])]
        if filters.get("start_date"):
            loans = [loan for loan in loans if loan["checked_out_at"][:10] >= filters["start_date"]]
        if filters.get("end_date"):
            loans = [loan for loan in loans if loan["checked_out_at"][:10] <= filters["end_date"]]
        return [self.enrich_loan(loan) for loan in sorted(loans, key=lambda l: l["checked_out_at"], reverse=True)]

    def enrich_loan(self, loan):
        loan["user"] = self.get_user(loan["user_id"]) if loan.get("user_id") else None
        loan["actioned_by"] = self.get_user(loan["actioned_by_id"]) if loan.get("actioned_by_id") else None
        loan["book"] = deepcopy(self._find(self.books, loan["book_id"]))
        return loan

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
