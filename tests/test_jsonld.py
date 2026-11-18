from pathlib import Path
from recipe_scraper.jsonld import extract_recipe, ingredient_lines

FIX = Path(__file__).parent / "fixtures" / "cookies.html"


def test_recipe_found_when_type_is_a_list():
    r = extract_recipe(FIX.read_text())
    assert r is not None


def test_ingredient_lines():
    lines = ingredient_lines(extract_recipe(FIX.read_text()))
    assert "1 cup butter, softened" in lines
    assert len(lines) >= 5


def test_graph_wrapper_and_bad_blocks():
    html = ('<script type="application/ld+json">{oops</script>'
            '<script type="application/ld+json">{"@graph":[{"@type":"WebSite"},{"@type":"Recipe","recipeIngredient":["2 eggs"]}]}</script>')
    assert ingredient_lines(extract_recipe(html)) == ["2 eggs"]


def test_no_recipe():
    assert extract_recipe("<html></html>") is None
