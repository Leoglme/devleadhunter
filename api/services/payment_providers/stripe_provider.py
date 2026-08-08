"""Stripe implementation of the encashment contract (Connect Standard).

Every call runs on the platform API key with ``stripe_account`` set to the
connected account (``acct_...``) — direct charges, so funds settle on the
connected account, never on the platform. The Stripe SDK is synchronous, so its
calls run in a worker thread to keep the async contract. Test vs live is decided
by the key itself (``sk_test`` / ``sk_live``), so there is no environment header
to manage as there is for Qonto.
"""

import asyncio
import logging

import httpx
import stripe

from core.config import settings
from enums.payment_provider import PaymentEnvironment, PaymentProvider
from models.payment_account import PaymentAccount
from services.payment_providers.base import (
    BillingClient,
    InvoiceRequest,
    IssuedInvoice,
    PaymentProviderClient,
    PaymentState,
)

logger = logging.getLogger(__name__)

_INVOICE_DUE_DAYS = 30


class StripeConnectError(RuntimeError):
    """Raised when a Stripe operation is attempted on an unusable connected account."""


class StripePaymentProvider(PaymentProviderClient):
    """Issues invoices through a user's Stripe Connect Standard account."""

    provider = PaymentProvider.STRIPE

    def __init__(self, account: PaymentAccount) -> None:
        """
        Build the provider for a connected Stripe account.

        Args:
            account: The user's connected Stripe account (holds ``acct_...``).

        Raises:
            StripeConnectError: If the account cannot yet accept charges, or the
                platform key is missing.
        """
        if not settings.stripe_secret_key:
            raise StripeConnectError("STRIPE_SECRET_KEY is not configured.")
        if not account.stripe_account_id:
            raise StripeConnectError("No Stripe connected account id on this payment account.")
        if not account.stripe_charges_enabled:
            raise StripeConnectError("Stripe connected account cannot accept charges yet (onboarding incomplete).")
        # Same fail-loudly rule as Qonto: a test-mode account is never invoiced live.
        runtime = (
            PaymentEnvironment.SANDBOX.value
            if settings.stripe_secret_key.startswith("sk_test")
            else PaymentEnvironment.PRODUCTION.value
        )
        if account.environment and account.environment != runtime:
            raise StripeConnectError(
                f"Stripe account was connected in '{account.environment}' but the platform key is '{runtime}'."
            )
        self._account = account
        self._connected_account_id = account.stripe_account_id
        stripe.api_key = settings.stripe_secret_key

    async def ensure_client(self, client: BillingClient) -> str:
        """
        Find (by email) or create the Stripe customer on the connected account.

        Args:
            client: The billing counterpart details.

        Returns:
            The Stripe customer id.
        """
        if client.email:
            found = await asyncio.to_thread(
                stripe.Customer.list, email=client.email, limit=1, stripe_account=self._connected_account_id
            )
            if found.data:
                return found.data[0].id

        address = {
            key: value
            for key, value in {
                "line1": client.address,
                "city": client.city,
                "postal_code": client.zip_code,
                "country": client.country_code,
            }.items()
            if value
        }
        customer = await asyncio.to_thread(
            stripe.Customer.create,
            name=client.name,
            email=client.email or None,
            address=address or None,
            stripe_account=self._connected_account_id,
        )
        return customer.id

    async def create_invoice(self, client_id: str, request: InvoiceRequest) -> IssuedInvoice:
        """
        Create, finalize and return a sendable Stripe invoice.

        Args:
            client_id: Stripe customer id from :meth:`ensure_client`.
            request: The invoice details (its ``application_fee_amount`` becomes
                the platform commission, transferred to the platform account).

        Returns:
            The issued invoice (``payment_url`` is the Stripe-hosted, card-payable page).
        """
        currency = (request.currency or "eur").lower()
        invoice_params: dict = {
            "customer": client_id,
            "collection_method": "send_invoice",
            "days_until_due": _INVOICE_DUE_DAYS,
            # Draft first — attach the line explicitly so orphaned pending items on the
            # customer (e.g. from a previous failed finalize) are never rolled in.
            "pending_invoice_items_behavior": "exclude",
            "auto_advance": False,
            "stripe_account": self._connected_account_id,
        }
        if request.application_fee_amount and request.application_fee_amount > 0:
            invoice_params["application_fee_amount"] = request.application_fee_amount
        invoice = await asyncio.to_thread(stripe.Invoice.create, **invoice_params)
        await asyncio.to_thread(
            stripe.InvoiceItem.create,
            customer=client_id,
            invoice=invoice.id,
            amount=request.amount_cents,
            currency=currency,
            description=request.label,
            stripe_account=self._connected_account_id,
        )
        finalized = await asyncio.to_thread(
            stripe.Invoice.finalize_invoice, invoice.id, stripe_account=self._connected_account_id
        )
        return IssuedInvoice(
            provider=self.provider.value,
            invoice_id=finalized.id,
            invoice_number=finalized.get("number"),
            payment_url=finalized.get("hosted_invoice_url"),
        )

    async def get_invoice_pdf(self, invoice_id: str) -> bytes:
        """
        Fetch the hosted invoice PDF bytes.

        Args:
            invoice_id: The Stripe invoice id.

        Returns:
            The raw PDF bytes.

        Raises:
            StripeConnectError: When the invoice exposes no PDF link.
        """
        invoice = await asyncio.to_thread(
            stripe.Invoice.retrieve, invoice_id, stripe_account=self._connected_account_id
        )
        pdf_url = invoice.get("invoice_pdf")
        if not pdf_url:
            raise StripeConnectError(f"Stripe invoice {invoice_id} has no PDF yet.")
        async with httpx.AsyncClient() as client:
            response = await client.get(pdf_url, timeout=60.0)
            response.raise_for_status()
            return response.content

    async def check_paid(self, invoice_id: str) -> PaymentState:
        """
        Read the invoice status on the connected account.

        Args:
            invoice_id: The Stripe invoice id.

        Returns:
            The normalized payment state (``paid`` status → paid).
        """
        invoice = await asyncio.to_thread(
            stripe.Invoice.retrieve, invoice_id, stripe_account=self._connected_account_id
        )
        status = invoice.get("status")
        return PaymentState(is_paid=status == "paid", raw_status=status)
