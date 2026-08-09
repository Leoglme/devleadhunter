"""Unit tests for the Stripe Connect payment provider.

The Stripe SDK is faked: each test drives canned objects and asserts the calls
the provider builds — every operation carries ``stripe_account`` (direct charges
on the connected account), the invoice is finalized, and the platform commission
(``application_fee_amount``) is passed only when set.
"""

import asyncio
from types import SimpleNamespace

import pytest

import services.payment_providers.stripe_provider as stripe_module
from core.config import settings
from services.payment_providers.base import BillingClient, InvoiceRequest
from services.payment_providers.stripe_provider import StripeConnectError, StripePaymentProvider


class _Obj(dict):
    """Dict with attribute access, mimicking a Stripe SDK object."""

    def __getattr__(self, name: str) -> object:
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error


class _FakeHttpxResponse:
    content = b"%PDF stripe"

    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClient:
    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get(self, _url: str, **_kwargs: object) -> _FakeHttpxResponse:
        return _FakeHttpxResponse()


@pytest.fixture(autouse=True)
def _fake_stripe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a platform key and a fake httpx for the PDF download."""
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(stripe_module.httpx, "AsyncClient", _FakeAsyncClient)


def _provider() -> StripePaymentProvider:
    account = SimpleNamespace(stripe_account_id="acct_1", stripe_charges_enabled=True, environment="sandbox")
    return StripePaymentProvider(account)


def test_init_refuses_account_without_charges() -> None:
    """An account that can't accept charges yet is refused."""
    account = SimpleNamespace(stripe_account_id="acct_1", stripe_charges_enabled=False, environment="sandbox")
    with pytest.raises(StripeConnectError):
        StripePaymentProvider(account)


def test_ensure_client_reuses_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An existing customer (matched by email) is reused, none is created."""
    monkeypatch.setattr(stripe_module.stripe.Customer, "list", lambda **_: _Obj(data=[_Obj(id="cus_existing")]))

    def _must_not_create(**_: object) -> None:
        raise AssertionError("customer must not be created when one exists")

    monkeypatch.setattr(stripe_module.stripe.Customer, "create", _must_not_create)
    result = asyncio.run(_provider().ensure_client(BillingClient(name="X", email="x@example.fr")))
    assert result == "cus_existing"


def test_ensure_client_creates_on_connected_account(monkeypatch: pytest.MonkeyPatch) -> None:
    """No match → a customer is created with the connected-account header."""
    monkeypatch.setattr(stripe_module.stripe.Customer, "list", lambda **_: _Obj(data=[]))
    captured: dict = {}

    def _create(**kwargs: object) -> _Obj:
        captured.update(kwargs)
        return _Obj(id="cus_new")

    monkeypatch.setattr(stripe_module.stripe.Customer, "create", _create)
    result = asyncio.run(_provider().ensure_client(BillingClient(name="Plomberie X", email="x@example.fr")))
    assert result == "cus_new"
    assert captured["stripe_account"] == "acct_1"
    assert captured["name"] == "Plomberie X"


def test_create_invoice_finalizes_and_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Draft invoice, attach one line item, finalize, and parse the response."""
    invoice_kwargs: dict = {}
    invoice_item_kwargs: dict = {}

    def _invoice_item_create(**kwargs: object) -> _Obj:
        invoice_item_kwargs.update(kwargs)
        return _Obj(id="ii_1")

    monkeypatch.setattr(stripe_module.stripe.InvoiceItem, "create", _invoice_item_create)

    def _invoice_create(**kwargs: object) -> _Obj:
        invoice_kwargs.update(kwargs)
        return _Obj(id="in_1")

    monkeypatch.setattr(stripe_module.stripe.Invoice, "create", _invoice_create)
    monkeypatch.setattr(
        stripe_module.stripe.Invoice,
        "finalize_invoice",
        lambda _id, **_: _Obj(id="in_1", number="ABC-001", hosted_invoice_url="https://pay.stripe.com/i/in_1"),
    )

    request = InvoiceRequest(client=BillingClient(name="X"), amount_cents=50000, currency="eur", label="Site web")
    issued = asyncio.run(_provider().create_invoice("cus_1", request))

    assert issued.invoice_id == "in_1"
    assert issued.invoice_number == "ABC-001"
    assert issued.payment_url == "https://pay.stripe.com/i/in_1"
    assert issued.provider == "stripe"
    assert invoice_kwargs["stripe_account"] == "acct_1"
    assert invoice_kwargs["collection_method"] == "send_invoice"
    assert invoice_kwargs["pending_invoice_items_behavior"] == "exclude"
    assert invoice_kwargs["auto_advance"] is False
    assert "application_fee_amount" not in invoice_kwargs
    assert invoice_item_kwargs["invoice"] == "in_1"
    assert invoice_item_kwargs["amount"] == 50000
    assert invoice_item_kwargs["description"] == "Site web"
    assert invoice_kwargs["payment_settings"]["payment_method_types"] == ["card", "link", "customer_balance"]
    assert (
        invoice_kwargs["payment_settings"]["payment_method_options"]["customer_balance"]["bank_transfer"]["type"]
        == "eu_bank_transfer"
    )


def test_create_invoice_passes_application_fee(monkeypatch: pytest.MonkeyPatch) -> None:
    """A platform commission is forwarded as application_fee_amount."""
    invoice_kwargs: dict = {}
    monkeypatch.setattr(stripe_module.stripe.InvoiceItem, "create", lambda **_: _Obj(id="ii_1"))
    monkeypatch.setattr(
        stripe_module.stripe.Invoice, "create", lambda **kwargs: (invoice_kwargs.update(kwargs), _Obj(id="in_1"))[1]
    )
    monkeypatch.setattr(
        stripe_module.stripe.Invoice, "finalize_invoice", lambda _id, **_: _Obj(id="in_1", number="ABC-002")
    )
    request = InvoiceRequest(
        client=BillingClient(name="X"),
        amount_cents=50000,
        currency="eur",
        label="Site web",
        application_fee_amount=5000,
    )
    asyncio.run(_provider().create_invoice("cus_1", request))
    assert invoice_kwargs["application_fee_amount"] == 5000
    assert invoice_kwargs["pending_invoice_items_behavior"] == "exclude"


def test_create_invoice_falls_back_without_bank_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    """A connected account that can't offer bank transfer finalizes with card + Link only."""
    monkeypatch.setattr(stripe_module.stripe.InvoiceItem, "create", lambda **_: _Obj(id="ii_1"))
    monkeypatch.setattr(stripe_module.stripe.Invoice, "create", lambda **_: _Obj(id="in_1"))

    finalize_calls: dict = {"count": 0}

    def _finalize(_id: str, **_: object) -> _Obj:
        finalize_calls["count"] += 1
        if finalize_calls["count"] == 1:
            raise stripe_module.stripe.error.InvalidRequestError("bank transfer not available", None)
        return _Obj(id="in_1", number="ABC-003", hosted_invoice_url="https://pay.stripe.com/i/in_1")

    monkeypatch.setattr(stripe_module.stripe.Invoice, "finalize_invoice", _finalize)

    modify_kwargs: dict = {}

    def _modify(_id: str, **kwargs: object) -> _Obj:
        modify_kwargs.update(kwargs)
        return _Obj(id="in_1")

    monkeypatch.setattr(stripe_module.stripe.Invoice, "modify", _modify)

    request = InvoiceRequest(client=BillingClient(name="X"), amount_cents=50000, currency="eur", label="Site web")
    issued = asyncio.run(_provider().create_invoice("cus_1", request))

    assert finalize_calls["count"] == 2
    assert issued.invoice_number == "ABC-003"
    assert modify_kwargs["payment_settings"]["payment_method_types"] == ["card", "link"]
    assert "payment_method_options" not in modify_kwargs["payment_settings"]
    assert modify_kwargs["stripe_account"] == "acct_1"


def test_get_invoice_pdf_downloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """The invoice PDF link is retrieved and downloaded."""
    monkeypatch.setattr(
        stripe_module.stripe.Invoice, "retrieve", lambda _id, **_: _Obj(invoice_pdf="https://pay.stripe.com/i/in_1.pdf")
    )
    pdf = asyncio.run(_provider().get_invoice_pdf("in_1"))
    assert pdf == b"%PDF stripe"


def test_check_paid_maps_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """A ``paid`` invoice status maps to is_paid=True."""
    monkeypatch.setattr(stripe_module.stripe.Invoice, "retrieve", lambda _id, **_: _Obj(status="paid"))
    state = asyncio.run(_provider().check_paid("in_1"))
    assert state.is_paid is True
    assert state.raw_status == "paid"
