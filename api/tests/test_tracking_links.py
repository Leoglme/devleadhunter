"""Unit tests for the demo/video link attribution helper."""

from services.tracking_links import CHANNEL_EMAIL, CHANNEL_SMS, append_query_param


class TestAppendQueryParam:
    def test_first_param_uses_question_mark(self) -> None:
        assert (
            append_query_param("https://demo.dibodev.fr/x", "src", CHANNEL_SMS) == "https://demo.dibodev.fr/x?src=sms"
        )

    def test_second_param_uses_ampersand(self) -> None:
        # An SMS-tagged demo link, then an email link with the A/B variant chained on.
        url = append_query_param("https://demo.dibodev.fr/x", "src", CHANNEL_EMAIL)
        assert append_query_param(url, "v", "A") == "https://demo.dibodev.fr/x?src=email&v=A"
