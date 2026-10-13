"""The add/edit form's live preview (shelf.js) recomputes a book's spine colour and size
client-side, so it must agree with the `title_seed` filter and the `spine` macro. Both this
test and tests/js/shelf.test.js check against the same fixture file."""
import json
import re
from pathlib import Path

import pytest

CASES = json.loads((Path(__file__).parent / "fixtures" / "spine_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["title"] for c in CASES])
def test_spine_macro_matches_fixture(app, case):
    template = app.jinja_env.from_string(
        '{% from "_macros.html" import spine %}{{ spine(title, "An Author", title|title_seed) }}'
    )
    with app.test_request_context():
        html = template.render(title=case["title"])

    assert app.jinja_env.filters["title_seed"](case["title"]) == case["seed"]
    assert re.search(r"width: ([^;]+);", html).group(1) == case["width"]
    assert re.search(r"height: ([^;]+);", html).group(1) == case["height"]
