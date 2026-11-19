from pathlib import Path

from recipe_scraper.crawl import crawl, links
from recipe_scraper.ingredients import CATEGORIES, normalize, parse

FIX = Path(__file__).parent / "fixtures" / "cookies.html"


def test_parse_quantity_unit_name():
    i = parse("1 1/2 cups packed brown sugar, divided")
    assert (i.quantity, i.unit, i.name) == (1.5, "cups", "brown sugar")
    i = parse("2 large eggs")
    assert (i.quantity, i.unit, i.name) == (2.0, None, "eggs")
    assert parse("1 cup butter, softened").name == "butter"


def test_table_hit_and_alias():
    i = normalize("2 large eggs")
    assert (i.name, i.category, i.source) == ("egg", "dairy", "table")


def test_model_fallback_validated():
    calls = []

    def model(name):
        calls.append(name)
        return "Spice "

    i = normalize("1 tsp sumac", model=model)
    assert (i.category, i.source, calls) == ("spice", "model", ["sumac"])


def test_invalid_model_answer_becomes_other_flagged():
    i = normalize("1 tsp sumac", model=lambda n: "condiments")
    assert i.category == "other" and i.needs_review and i.category in CATEGORIES


def test_no_model_unknown_flagged():
    assert normalize("1 tsp sumac").needs_review


class FakeSite:
    pages = {
        "https://x.test/": '<a href="/list">l</a><a href="https://other.test/">o</a>',
        "https://x.test/list": '<a href="/r1">1</a><a href="/r2#frag">2</a><a href="/">home</a>',
        "https://x.test/r1": FIX.read_text(),
        "https://x.test/r2": FIX.read_text(),
    }

    def __init__(self):
        self.fetched = []

    def get(self, url):
        self.fetched.append(url)
        return self.pages.get(url)


def test_links_same_host_and_defrag():
    assert links('<a href="/a#x">a</a><a href="https://o.test/">o</a>', "https://x.test/") == ["https://x.test/a"]


def test_crawl_finds_recipes_once():
    site, got = FakeSite(), []
    fr = crawl(["https://x.test/"], site, lambda u, r: got.append(u))
    assert sorted(got) == ["https://x.test/r1", "https://x.test/r2"]
    assert len(site.fetched) == len(set(site.fetched)) == 4
    assert fr.pages == 4


def test_depth_limit():
    got = []
    crawl(["https://x.test/"], FakeSite(), lambda u, r: got.append(u), max_depth=1)
    assert got == []  # recipes sit at depth 2


def test_resume_from_state(tmp_path):
    state, got = tmp_path / "s.json", []
    crawl(["https://x.test/"], FakeSite(), lambda u, r: got.append(u), state_path=state, max_pages=2)
    assert got == []
    site2 = FakeSite()
    crawl(["https://x.test/"], site2, lambda u, r: got.append(u), state_path=state, max_pages=10)
    assert sorted(got) == ["https://x.test/r1", "https://x.test/r2"]
    assert "https://x.test/" not in site2.fetched  # already done before the "crash"
