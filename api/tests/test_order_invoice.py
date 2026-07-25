"""Unit tests for order invoice generation and the sale email.

The provider is faked (its live calls are covered by ``test_qonto_provider``);
here we assert the order plumbing: columns filled from the issued invoice, an
existing invoice reused (never re-issued — a finalized invoice burns a number),
and the email copy (no "Stripe", black button, generic payment URL).
"""

import asyncio
from types import SimpleNamespace

import pytest

from enums.order_status import OrderStatus
from services.order_service import OrderService
from services.payment_providers.base import IssuedInvoice


class _FakeDB:
    """No-op session: the service only calls commit/refresh on it."""

    def commit(self) -> None:
        return None

    def refresh(self, _obj: object) -> None:
        return None


class _FakeProvider:
    """Records the invoice request and returns a canned issued invoice."""

    def __init__(self) -> None:
        self.ensure_client_called_with: object = None
        self.create_invoice_called_with: object = None

    async def ensure_client(self, billing: object) -> str:
        self.ensure_client_called_with = billing
        return "cli_1"

    async def create_invoice(self, client_id: str, request: object) -> IssuedInvoice:
        self.create_invoice_called_with = request
        return IssuedInvoice(
            provider="qonto",
            invoice_id="inv_1",
            invoice_number="F-2026-006",
            payment_url="https://pay.qonto.com/invoices/inv_1",
        )


def _order(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 7,
        "product_type": "website",
        "business_name": "Plomberie Durand",
        "customer_name": None,
        "customer_email": "durand@example.fr",
        "amount_cents": 50000,
        "currency": "eur",
        "status": OrderStatus.DRAFT.value,
        "invoice_id": None,
        "invoice_number": None,
        "payment_provider": None,
        "payment_url": None,
        "stripe_payment_url": None,
        "prospect_id": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_ensure_invoice_fills_columns_from_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """A connected provider issues the invoice and its artifacts land on the order."""
    service = OrderService()
    provider = _FakeProvider()

    async def _fake_resolve(_db: object, _user: object) -> _FakeProvider:
        return provider

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    order = _order()
    result = asyncio.run(service.ensure_invoice(_FakeDB(), SimpleNamespace(id=1), order))

    assert result.payment_provider == "qonto"
    assert result.invoice_id == "inv_1"
    assert result.invoice_number == "F-2026-006"
    assert result.payment_url == "https://pay.qonto.com/invoices/inv_1"
    assert result.status == OrderStatus.PAYMENT_PENDING.value
    # The line item carries the business name and the order amount.
    assert provider.create_invoice_called_with.amount_cents == 50000
    assert "Plomberie Durand" in provider.create_invoice_called_with.label


def test_ensure_invoice_reuses_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An order that already has an invoice is never re-issued."""
    service = OrderService()

    async def _must_not_run(_db: object, _user: object) -> None:
        raise AssertionError("provider must not be resolved when an invoice already exists")

    monkeypatch.setattr(service, "_resolve_provider", _must_not_run)
    order = _order(invoice_id="inv_existing", invoice_number="F-2026-005")
    result = asyncio.run(service.ensure_invoice(_FakeDB(), SimpleNamespace(id=1), order))
    assert result.invoice_id == "inv_existing"


def test_build_payment_email_has_no_stripe_black_button_and_generic_url() -> None:
    """The sale email drops the Stripe mention, uses a black button and the generic URL."""
    order = _order(invoice_id="inv_1", payment_url="https://pay.qonto.com/invoices/inv_1")
    rendered = OrderService().build_payment_email(order, sender_name="Léo")

    body = rendered["body_html"]
    assert "Stripe" not in body
    assert "#111111" in body
    assert "https://pay.qonto.com/invoices/inv_1" in body
    assert "pièce jointe" in body  # an invoice exists → the attachment is announced


def test_build_payment_email_omits_attachment_note_without_invoice() -> None:
    """Without an issued invoice, the email doesn't promise an attachment."""
    order = _order(payment_url="https://buy.stripe.com/x")
    body = OrderService().build_payment_email(order, sender_name="Léo")["body_html"]
    assert "pièce jointe" not in body


def test_check_and_mark_paid_marks_when_provider_reports_paid(monkeypatch: pytest.MonkeyPatch) -> None:
    """A provider-confirmed payment transitions the order to paid."""
    service = OrderService()
    order = _order(invoice_id="inv_1", payment_provider="qonto", paid_at=None)

    async def _fake_resolve(_db: object, _user: object) -> SimpleNamespace:
        async def _check_paid(_invoice_id: str) -> SimpleNamespace:
            return SimpleNamespace(is_paid=True, raw_status="paid")

        return SimpleNamespace(check_paid=_check_paid)

    marked: dict[str, bool] = {"done": False}

    def _fake_mark_paid(_db: object, target: SimpleNamespace) -> SimpleNamespace:
        marked["done"] = True
        target.paid_at = "now"
        return target

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    monkeypatch.setattr(service, "mark_paid", _fake_mark_paid)
    assert asyncio.run(service.check_and_mark_paid(_FakeDB(), SimpleNamespace(id=1), order)) is True
    assert marked["done"] is True


def test_check_and_mark_paid_noop_when_unpaid(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unpaid invoice leaves the order untouched."""
    service = OrderService()
    order = _order(invoice_id="inv_1", payment_provider="qonto", paid_at=None)

    async def _fake_resolve(_db: object, _user: object) -> SimpleNamespace:
        async def _check_paid(_invoice_id: str) -> SimpleNamespace:
            return SimpleNamespace(is_paid=False, raw_status="unpaid")

        return SimpleNamespace(check_paid=_check_paid)

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    assert asyncio.run(service.check_and_mark_paid(_FakeDB(), SimpleNamespace(id=1), order)) is False
