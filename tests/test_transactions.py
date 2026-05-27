from .conftest import csrf_token, login


def _results_html(response):
    html = response.data.decode()
    start = html.index('data-testid="transactions-results"')
    end = html.index("</tbody>", start)
    return html[start:end]


def _create_transaction_data(client, app):
    repo = app.config["REPOSITORY"]
    second_book = repo.create_book(
        {
            "title": "Accelerate",
            "author": "Nicole Forsgren",
            "publication_year": 2018,
            "isbn": "9781942788331",
            "created_by_id": 1,
        }
    )

    login(client, "regularuser", "RegularPass123!")
    client.post("/books/1/checkout", data={"_csrf_token": csrf_token(client)}, follow_redirects=True)
    client.post("/books/1/return", data={"_csrf_token": csrf_token(client)}, follow_redirects=True)
    client.post(
        f"/books/{second_book['id']}/checkout",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

    repo.loans[0]["checked_out_at"] = "2026-05-01T10:00:00+00:00"
    repo.loans[0]["returned_at"] = "2026-05-02T10:00:00+00:00"
    repo.loans[1]["checked_out_at"] = "2026-05-20T10:00:00+00:00"
    return second_book


def test_transactions_page_is_admin_only(client):
    login(client, "regularuser", "RegularPass123!")
    response = client.get("/transactions", follow_redirects=True)

    assert b"You do not have permission" in response.data


def test_admin_can_view_transactions(client, app):
    _create_transaction_data(client, app)
    login(client)
    response = client.get("/transactions")

    assert response.status_code == 200
    assert b"Transactions" in response.data
    assert b"Clean Code" in response.data
    assert b"Accelerate" in response.data


def test_admin_can_filter_transactions_by_book(client, app):
    second_book = _create_transaction_data(client, app)
    login(client)
    response = client.get(f"/transactions?book_id={second_book['id']}")
    results = _results_html(response)

    assert "Accelerate" in results
    assert "Clean Code" not in results


def test_admin_can_filter_transactions_by_user_and_date_range(client, app):
    _create_transaction_data(client, app)
    login(client)
    response = client.get("/transactions?user_id=2&start_date=2026-05-10&end_date=2026-05-31")
    results = _results_html(response)

    assert "Accelerate" in results
    assert "Clean Code" not in results


def test_regular_user_can_view_only_own_transactions(client, app):
    repo = app.config["REPOSITORY"]
    third_user = repo.create_user("thirduser", "hash", "regular")
    second_book = repo.create_book(
        {
            "title": "Third User Book",
            "author": "Example Author",
            "publication_year": 2024,
            "isbn": "1111111111",
            "created_by_id": 1,
        }
    )

    login(client, "regularuser", "RegularPass123!")
    client.post("/books/1/checkout", data={"_csrf_token": csrf_token(client)}, follow_redirects=True)
    repo.update_book(second_book["id"], {"status": "checked_out", "checked_out_by_id": third_user["id"]})
    repo.create_loan(second_book["id"], third_user["id"], third_user["id"])

    response = client.get("/my-transactions")
    results = _results_html(response)

    assert response.status_code == 200
    assert "Clean Code" in results
    assert "Third User Book" not in results


def test_my_transactions_ignores_user_id_query_parameter(client, app):
    repo = app.config["REPOSITORY"]
    third_user = repo.create_user("thirduser", "hash", "regular")
    second_book = repo.create_book(
        {
            "title": "Third User Book",
            "author": "Example Author",
            "publication_year": 2024,
            "isbn": "2222222222",
            "created_by_id": 1,
        }
    )

    login(client, "regularuser", "RegularPass123!")
    client.post("/books/1/checkout", data={"_csrf_token": csrf_token(client)}, follow_redirects=True)
    repo.update_book(second_book["id"], {"status": "checked_out", "checked_out_by_id": third_user["id"]})
    repo.create_loan(second_book["id"], third_user["id"], third_user["id"])

    response = client.get(f"/my-transactions?user_id={third_user['id']}")
    results = _results_html(response)

    assert "Clean Code" in results
    assert "Third User Book" not in results
