def test_home_uses_bootstrap(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"cdn.jsdelivr.net/npm/bootstrap" in response.data
    assert b"Manage shared technical books securely" in response.data


def test_login_page_uses_bootstrap_form_classes(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b"class=\"form-control\"" in response.data
    assert b"class=\"btn btn-primary w-100\"" in response.data

