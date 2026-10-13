import pytest
import requests

from conftest import login, make_member


class FakeResponse:
    def __init__(self, payload=None, status=200, bad_json=False):
        self.payload, self.status, self.bad_json = payload, status, bad_json

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"{self.status}")

    def json(self):
        if self.bad_json:
            raise ValueError("not JSON")
        return self.payload


@pytest.fixture
def fake_get(monkeypatch):
    """Replace requests.get with a recorder that returns `fake_get.response` (or raises it)."""
    calls = []

    def _get(url, params=None, headers=None, timeout=None):
        calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        if isinstance(_get.response, Exception):
            raise _get.response
        return _get.response

    _get.calls = calls
    _get.response = FakeResponse({"docs": []})
    monkeypatch.setattr("app.books.routes.requests.get", _get)
    return _get


@pytest.fixture(autouse=True)
def logged_in(client):
    login(client, make_member("alice"))


def doc(title, isbns=(), key="/works/OL1W", author="Author"):
    return {"title": title, "author_name": [author], "isbn": list(isbns), "key": key, "cover_i": 7}


# --- /books/api/lookup ---------------------------------------------------------------------

def test_lookup_without_params(client, fake_get):
    assert client.get("/books/api/lookup").get_json() == {"error": "No match found"}
    assert fake_get.calls == []


def test_invalid_isbn_never_calls_out(client, fake_get):
    assert "error" in client.get("/books/api/lookup?isbn=1234567890").get_json()
    assert fake_get.calls == []


def test_isbn_lookup_exact_match(client, fake_get):
    fake_get.response = FakeResponse({"docs": [
        doc("Wrong Book", isbns=["0000000000"]),
        doc("Right Book", isbns=["9780306406157"]),
    ]})
    body = client.get("/books/api/lookup?isbn=978-0-306-40615-7").get_json()
    assert body["match"]["title"] == "Right Book"
    assert body["match"]["isbn"] == "978-0-306-40615-7"  # echoes what the user typed
    call = fake_get.calls[0]
    assert call["params"]["isbn"] == "9780306406157"
    assert call["timeout"] == 5
    assert call["headers"]["User-Agent"].startswith("sb-bookclub-app/")


def test_isbn_lookup_rejects_loose_match(client, fake_get):
    fake_get.response = FakeResponse({"docs": [doc("Closest Match", isbns=["1111111111"])]})
    assert "error" in client.get("/books/api/lookup?isbn=9780306406157").get_json()


def test_title_lookup_returns_up_to_five_candidates(client, fake_get):
    fake_get.response = FakeResponse({"docs": [doc(f"Book {i}") for i in range(8)]})
    body = client.get("/books/api/lookup?title=Book&author=Someone").get_json()
    assert len(body["candidates"]) == 5
    assert fake_get.calls[0]["params"]["title"] == "Book"
    assert fake_get.calls[0]["params"]["author"] == "Someone"


def test_title_lookup_no_results(client, fake_get):
    assert "error" in client.get("/books/api/lookup?title=Nothing").get_json()


@pytest.mark.parametrize("response", [
    requests.ConnectionError("down"),
    requests.Timeout("slow"),
    FakeResponse(status=503),
    FakeResponse(bad_json=True),
])
def test_lookup_failures_collapse_to_error(client, fake_get, response):
    fake_get.response = response
    resp = client.get("/books/api/lookup?title=Dune")
    assert resp.status_code == 200
    assert resp.get_json() == {"error": "No match found"}


# --- /books/api/lookup/covers --------------------------------------------------------------

@pytest.mark.parametrize("work", ["", "/works/../authors", "/works/OL1W/../x", "https://evil/works/OL1W", "OL1W"])
def test_covers_rejects_bad_work_key(client, fake_get, work):
    assert client.get("/books/api/lookup/covers", query_string={"work": work}).get_json() == {"covers": []}
    assert fake_get.calls == []


def test_covers_filters_and_pairs_isbns(client, fake_get):
    fake_get.response = FakeResponse({"entries": [
        {"covers": [1], "languages": [{"key": "/languages/fre"}], "isbn_13": ["french"]},
        {"covers": [], "isbn_13": ["no-cover"]},
        {"covers": [-1], "isbn_13": ["placeholder-cover"]},
        {"covers": [2], "languages": [{"key": "/languages/eng"}], "isbn_13": ["isbn13"], "isbn_10": ["isbn10"]},
        {"covers": [3], "isbn_10": ["only10"]},
        {"covers": [4]},
    ]})
    body = client.get("/books/api/lookup/covers?work=/works/OL123W").get_json()
    assert fake_get.calls[0]["url"] == "https://openlibrary.org/works/OL123W/editions.json"
    assert body["covers"] == [
        {"cover_url": "https://covers.openlibrary.org/b/id/2-L.jpg", "isbn": "isbn13"},
        {"cover_url": "https://covers.openlibrary.org/b/id/3-L.jpg", "isbn": "only10"},
        {"cover_url": "https://covers.openlibrary.org/b/id/4-L.jpg", "isbn": ""},
    ]


def test_covers_capped_at_twelve(client, fake_get):
    fake_get.response = FakeResponse({"entries": [{"covers": [i + 1]} for i in range(20)]})
    assert len(client.get("/books/api/lookup/covers?work=/works/OL1W").get_json()["covers"]) == 12


def test_covers_failure_returns_empty(client, fake_get):
    fake_get.response = requests.ConnectionError("down")
    assert client.get("/books/api/lookup/covers?work=/works/OL1W").get_json() == {"covers": []}


def test_author_only_lookup(client, fake_get):
    fake_get.response = FakeResponse({"docs": [doc("Dune", author="Frank Herbert")]})
    body = client.get("/books/api/lookup?author=Frank Herbert").get_json()
    assert body["candidates"][0]["author"] == "Frank Herbert"
    assert "title" not in fake_get.calls[0]["params"]


def test_isbn10_with_check_digit_x(client, fake_get):
    fake_get.response = FakeResponse({"docs": [doc("Right Book", isbns=["080442957X"])]})
    body = client.get("/books/api/lookup?isbn=0-8044-2957-X").get_json()
    assert body["match"]["title"] == "Right Book"
    assert fake_get.calls[0]["params"]["isbn"] == "080442957X"
