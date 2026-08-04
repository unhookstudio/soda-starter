from listening_journal.api import api


def test_browser_cookie_auth_routes_are_not_exposed():
    paths = api.get_openapi_schema()["paths"]

    assert not any("/auth/browser" in path for path in paths)
