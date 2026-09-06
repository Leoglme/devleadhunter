"""Unit tests for the SMS template library — integrity, rendering, one-segment budget."""

from enums.sms_template_category import SmsTemplateCategory
from services.sms.gsm_segments import is_gsm7, segment_count
from services.sms.templates import (
    DEFAULT_FIRST_CONTACT_KEY,
    SMS_TEMPLATE_LIBRARY,
    find_sms_template,
    list_sms_templates,
    render_sms_template,
)
from services.sms_service import sms_service
from services.sms_variables import SmsVariables

# A common case: a first name and an 18-character slug (the link is the heaviest variable).
_TYPICAL_VARIABLES: dict[str, str] = {
    "salutation": "Bonjour Geoffrey",
    "entreprise": "Garage Martin Auto",
    "ville": "Poitiers",
    "metier": "garagiste",
    "lien_demo": "demo.dibodev.fr/garage-martin-auto?src=sms",
    "lien_video": "demo.dibodev.fr/v/garage-martin-auto?src=sms",
    "ancien_site": "garage-martin.fr",
    "prix": "500 €",
    "signature": "Léo",
}


class TestLibraryIntegrity:
    def test_keys_are_unique(self) -> None:
        keys = [template.key for template in SMS_TEMPLATE_LIBRARY]
        assert len(keys) == len(set(keys))

    def test_default_first_contact_template_exists(self) -> None:
        template = find_sms_template(DEFAULT_FIRST_CONTACT_KEY)
        assert template is not None
        assert template.category is SmsTemplateCategory.FIRST_CONTACT

    def test_category_filter(self) -> None:
        first_contact = list_sms_templates(SmsTemplateCategory.FIRST_CONTACT)
        assert first_contact
        assert all(template.category is SmsTemplateCategory.FIRST_CONTACT for template in first_contact)
        assert len(list_sms_templates()) == len(SMS_TEMPLATE_LIBRARY)

    def test_unknown_key_is_none(self) -> None:
        assert find_sms_template("nope") is None

    def test_no_template_writes_the_stop_mention(self) -> None:
        assert all("36180" not in template.body for template in SMS_TEMPLATE_LIBRARY)

    def test_variables_are_declared_in_order(self) -> None:
        template = find_sms_template("video")
        assert template is not None
        assert template.variables == ["salutation", "entreprise", "lien_video", "signature"]
        assert template.uses("lien_video")
        assert not template.uses("lien_demo")


class TestRender:
    def test_substitutes_variables(self) -> None:
        rendered = render_sms_template("{salutation}, site pour {entreprise}", _TYPICAL_VARIABLES)
        assert rendered == "Bonjour Geoffrey, site pour Garage Martin Auto"

    def test_unknown_or_empty_variable_leaves_no_double_space(self) -> None:
        assert render_sms_template("Bonjour {inconnu} {signature}", {"signature": ""}) == "Bonjour"

    def test_compose_from_template_is_a_first_contact_with_stop_once(self) -> None:
        template = find_sms_template(DEFAULT_FIRST_CONTACT_KEY)
        assert template is not None
        body = sms_service.compose_from_template(template, _TYPICAL_VARIABLES)
        assert body.endswith("STOP au 36180")
        assert body.count("36180") == 1
        # A first contact must NOT claim a prior email.
        assert "par email" not in body
        assert "Garage Martin Auto" in body
        assert "demo.dibodev.fr/garage-martin-auto?src=sms" in body


class TestOneSegmentBudget:
    def test_every_first_contact_template_fits_one_gsm7_segment(self) -> None:
        for template in list_sms_templates(SmsTemplateCategory.FIRST_CONTACT):
            body = sms_service.compose_from_template(template, _TYPICAL_VARIABLES)
            assert is_gsm7(body), template.key
            assert segment_count(body) == 1, f"{template.key}: {len(body)} chars"


class TestSmsVariables:
    def test_as_sms_link_drops_scheme_and_keeps_query(self) -> None:
        assert (
            SmsVariables.as_sms_link("https://demo.dibodev.fr/chez-mimon?src=sms")
            == "demo.dibodev.fr/chez-mimon?src=sms"
        )
        assert SmsVariables.as_sms_link("http://demo.dibodev.fr/x") == "demo.dibodev.fr/x"
        assert SmsVariables.as_sms_link(None) == ""

    def test_signature_is_the_first_name(self) -> None:
        assert SmsVariables.signature_for("Léo Guillaume") == "Léo"
        assert SmsVariables.signature_for(" Marie ") == "Marie"
        assert SmsVariables.signature_for("") == ""
        assert SmsVariables.signature_for(None) == ""
