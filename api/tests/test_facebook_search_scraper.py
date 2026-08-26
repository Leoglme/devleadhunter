"""Unit tests for the Facebook discovery scraper — pure parsers, no network."""

import base64

from scrappers.facebook_search_scraper import (
    _decode_bing_redirect,
    _unwrap_redirect,
    clean_serp_title,
    extract_facebook_results,
    humanize_facebook_slug,
    normalize_facebook_page_url,
)


class TestNormalizeFacebookPageUrl:
    def test_plain_handle_drops_trailing_slash(self) -> None:
        assert (
            normalize_facebook_page_url("https://www.facebook.com/PizzaFlam44/")
            == "https://www.facebook.com/PizzaFlam44"
        )

    def test_mobile_host_and_subtab_collapse_to_page(self) -> None:
        assert (
            normalize_facebook_page_url("https://m.facebook.com/PizzaFlam44/photos")
            == "https://www.facebook.com/PizzaFlam44"
        )

    def test_post_url_collapses_to_page(self) -> None:
        assert (
            normalize_facebook_page_url("https://www.facebook.com/bandbfoodtruck/posts/123456")
            == "https://www.facebook.com/bandbfoodtruck"
        )

    def test_pg_prefix_normalizes_to_handle(self) -> None:
        assert (
            normalize_facebook_page_url("https://www.facebook.com/pg/PizzaFlam44/about")
            == "https://www.facebook.com/PizzaFlam44"
        )

    def test_profile_php_kept_with_id(self) -> None:
        raw = "https://www.facebook.com/profile.php?id=100057123456789&sk=about"
        assert normalize_facebook_page_url(raw) == "https://www.facebook.com/profile.php?id=100057123456789"

    def test_pages_slug_id_form_kept(self) -> None:
        raw = "https://www.facebook.com/pages/Chez-Marcel/123456789"
        assert normalize_facebook_page_url(raw) == "https://www.facebook.com/pages/Chez-Marcel/123456789"

    def test_reserved_segments_rejected(self) -> None:
        for raw in (
            "https://www.facebook.com/login/",
            "https://www.facebook.com/groups/12345",
            "https://www.facebook.com/watch/",
            "https://www.facebook.com/sharer/sharer.php?u=x",
            "https://www.facebook.com/events/999",
        ):
            assert normalize_facebook_page_url(raw) is None

    def test_non_facebook_host_rejected(self) -> None:
        assert normalize_facebook_page_url("https://example.com/PizzaFlam44") is None


class TestCleanSerpTitle:
    def test_strips_facebook_suffix(self) -> None:
        assert clean_serp_title("PIZZ'A FLAM | Facebook") == "PIZZ'A FLAM"

    def test_strips_subtab_then_facebook(self) -> None:
        assert clean_serp_title("B&B le Food truck - Posts | Facebook") == "B&B le Food truck"

    def test_strips_notification_prefix(self) -> None:
        assert clean_serp_title("(3) PIZZ'A FLAM | Facebook") == "PIZZ'A FLAM"

    def test_strips_french_subtab(self) -> None:
        assert clean_serp_title("Tacos Maru - Avis | Facebook") == "Tacos Maru"


class TestHumanizeSlug:
    def test_hyphenated_slug(self) -> None:
        assert humanize_facebook_slug("https://www.facebook.com/le-fournil-des-halles") == "Le Fournil Des Halles"

    def test_profile_php_has_no_name(self) -> None:
        assert humanize_facebook_slug("https://www.facebook.com/profile.php?id=123") == "Page Facebook"


class TestRedirectUnwrap:
    def test_google_url_redirect(self) -> None:
        href = "/url?q=https://www.facebook.com/PizzaFlam44/&sa=U&ved=abc"
        assert _unwrap_redirect(href) == "https://www.facebook.com/PizzaFlam44/"

    def test_facebook_lphp_redirect(self) -> None:
        href = "https://l.facebook.com/l.php?u=https%3A%2F%2Fwww.facebook.com%2FPizzaFlam44%2F&h=AT1"
        assert _unwrap_redirect(href) == "https://www.facebook.com/PizzaFlam44/"

    def test_bing_ck_redirect(self) -> None:
        target = "https://www.facebook.com/PizzaFlam44/"
        encoded = "a1" + base64.urlsafe_b64encode(target.encode()).decode().rstrip("=")
        href = f"https://www.bing.com/ck/a?!&&p=abc&u={encoded}"
        assert _decode_bing_redirect(href) == target
        assert _unwrap_redirect(href) == target


class TestExtractFacebookResults:
    _GOOGLE_HTML = """
    <div id="search">
      <div class="g"><a href="/url?q=https://www.facebook.com/PizzaFlam44/&sa=U"><h3>PIZZ'A FLAM | Facebook</h3></a></div>
      <div class="g"><a href="/url?q=https://www.facebook.com/bandbfoodtruck/posts/42&sa=U"><h3>B&amp;B le Food truck - Posts | Facebook</h3></a></div>
      <div class="g"><a href="/url?q=https://www.facebook.com/login/&sa=U"><h3>Log into Facebook</h3></a></div>
      <div class="g"><a href="/url?q=https://www.tripadvisor.fr/xyz&sa=U"><h3>A directory | TripAdvisor</h3></a></div>
    </div>
    """

    def test_extracts_pages_collapses_posts_drops_chrome(self) -> None:
        results = extract_facebook_results(self._GOOGLE_HTML)
        urls = {url for url, _ in results}
        assert "https://www.facebook.com/PizzaFlam44" in urls
        assert "https://www.facebook.com/bandbfoodtruck" in urls
        assert "https://www.facebook.com/login" not in urls
        # No non-facebook link leaks in.
        assert all("facebook.com" in url for url in urls)

    def test_titles_are_carried(self) -> None:
        titles = dict(extract_facebook_results(self._GOOGLE_HTML))
        assert "PIZZ'A FLAM" in titles["https://www.facebook.com/PizzaFlam44"]

    def test_bing_direct_anchor(self) -> None:
        html = '<li class="b_algo"><h2><a href="https://www.facebook.com/PizzaFlam44/">PIZZ\'A FLAM - Facebook</a></h2></li>'
        results = extract_facebook_results(html)
        assert ("https://www.facebook.com/PizzaFlam44", "PIZZ'A FLAM - Facebook") in results
