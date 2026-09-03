"""Unit tests for the pure SMS helpers — phone, segments, legal window."""

from datetime import datetime

from services.sms.gsm_segments import is_gsm7, segment_count
from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
from services.sms.send_window import is_within_window, next_send_slot
from services.sms_config_service import SmsConfigService
from services.sms_service import sms_service


class TestPhoneNormalizer:
    def test_national_mobile_to_e164(self) -> None:
        assert to_e164_fr("06 29 34 58 99") == "+33629345899"

    def test_compact_and_dotted(self) -> None:
        assert to_e164_fr("0629345899") == "+33629345899"
        assert to_e164_fr("06.29.34.58.99") == "+33629345899"

    def test_already_international(self) -> None:
        assert to_e164_fr("+33 6 29 34 58 99") == "+33629345899"
        assert to_e164_fr("0033629345899") == "+33629345899"

    def test_landline_normalises_but_is_not_mobile(self) -> None:
        assert to_e164_fr("01 42 68 53 00") == "+33142685300"
        assert is_mobile_fr("01 42 68 53 00") is False

    def test_mobile_detection(self) -> None:
        assert is_mobile_fr("06 29 34 58 99") is True
        assert is_mobile_fr("07 12 34 56 78") is True

    def test_invalid_returns_none(self) -> None:
        assert to_e164_fr("12345") is None
        assert to_e164_fr("") is None
        assert to_e164_fr(None) is None


class TestGsmSegments:
    def test_plain_ascii_is_gsm7_one_segment(self) -> None:
        assert is_gsm7("Bonjour, voici votre site : demo.dibodev.fr/xyz") is True
        assert segment_count("Bonjour, voici votre site : demo.dibodev.fr/xyz") == 1

    def test_accents_force_ucs2(self) -> None:
        # « é » is in GSM-7, but « ê »/« ô » are NOT → forces UCS-2.
        assert is_gsm7("aperçu prêt") is False

    def test_gsm7_160_boundary(self) -> None:
        assert segment_count("a" * 160) == 1
        assert segment_count("a" * 161) == 2

    def test_ucs2_70_boundary(self) -> None:
        body = "ê" * 70
        assert segment_count(body) == 1
        assert segment_count("ê" * 71) == 2

    def test_empty(self) -> None:
        assert segment_count("") == 0


class TestSendWindow:
    def test_weekday_inside(self) -> None:
        # Monday 2026-08-31 at 10:00 → open.
        assert is_within_window(datetime(2026, 8, 31, 10, 0)) is True

    def test_weekday_before_open(self) -> None:
        assert is_within_window(datetime(2026, 8, 31, 7, 30)) is False

    def test_saturday_hours(self) -> None:
        # Saturday 2026-08-29 — open 10:00–19:00.
        assert is_within_window(datetime(2026, 8, 29, 9, 30)) is False
        assert is_within_window(datetime(2026, 8, 29, 11, 0)) is True

    def test_sunday_closed(self) -> None:
        assert is_within_window(datetime(2026, 8, 30, 12, 0)) is False

    def test_public_holiday_closed(self) -> None:
        # 2026-05-01 (Fête du Travail) is a Friday but a holiday.
        assert is_within_window(datetime(2026, 5, 1, 11, 0)) is False

    def test_next_slot_defers_sunday_to_monday(self) -> None:
        slot = next_send_slot(datetime(2026, 8, 30, 12, 0))  # Sunday noon
        assert slot.weekday() == 0 and slot.hour == 8  # Monday 08:00

    def test_next_slot_before_open_returns_open(self) -> None:
        slot = next_send_slot(datetime(2026, 8, 31, 6, 0))  # Monday 06:00
        assert slot.hour == 8 and slot.date() == datetime(2026, 8, 31).date()

    def test_next_slot_inside_returns_same(self) -> None:
        moment = datetime(2026, 8, 31, 10, 0)
        assert next_send_slot(moment) == moment


class TestSenderValidation:
    def test_valid_sender(self) -> None:
        assert SmsConfigService.is_valid_sender("Dibodev") is True

    def test_too_short(self) -> None:
        assert SmsConfigService.is_valid_sender("ab") is False

    def test_too_long(self) -> None:
        assert SmsConfigService.is_valid_sender("DibodevProSMS") is False

    def test_numeric_only_rejected(self) -> None:
        assert SmsConfigService.is_valid_sender("12345") is False

    def test_symbols_rejected(self) -> None:
        assert SmsConfigService.is_valid_sender("Dibo-dev") is False


class TestManualBody:
    def test_appends_stop_mention(self) -> None:
        body = sms_service.compose_manual_body("Bonjour, votre site est prêt")
        assert body.endswith("STOP au 36180")

    def test_stop_mention_not_duplicated(self) -> None:
        # A user who already wrote the opt-out keeps a single mention.
        body = sms_service.compose_manual_body("Offre limitée STOP au 36180")
        assert body.count("36180") == 1

    def test_trims_surrounding_whitespace(self) -> None:
        body = sms_service.compose_manual_body("   Coucou   ")
        assert body.startswith("Coucou")
