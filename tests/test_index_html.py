"""HTML template substitution tests."""

from app.main import _index_html


def test_index_html_base_path_substitution():
    html = _index_html()
    assert "window./sudokuheist" not in html
    assert "@@BASE_PATH@@" not in html
    assert 'window.__BASE_PATH__ = "/sudokuheist"' in html
    assert '<base href="/sudokuheist/" />' in html
