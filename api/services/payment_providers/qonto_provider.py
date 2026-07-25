"""Qonto implementation of the encashment contract.

Real Business API calls (httpx) against the base host in ``settings``, with the
environment guard and staging-token header kept from the socle. The client is
found-or-created, the invoice is finalized (``status: unpaid``) so Qonto owns
its number, and the PDF is fetched after Qonto has generated it (async, ~10s).

Qonto is Léo's account only, so the VAT block is his franchise-en-base regime
(art. 293 B): rate 0, exemption reason ``S293B`` — matching his real invoices.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx

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
_VAT_RATE = "0"
_VAT_EXEMPTION_REASON = "S293B"
# The invoice PDF is generated asynchronously by Qonto — poll for its attachment.
_PDF_POLL_ATTEMPTS = 6
_PDF_POLL_DELAY_SECONDS = 3.0


class QontoEnvironmentError(RuntimeError):
    """Raised when the runtime and the stored credentials disagree on environment.

    Deliberately fatal: a silent fallback here is exactly the failure mode that
    would let a bug write into real accounting, so a mismatch stops the request.
    """


class QontoPaymentProvider(PaymentProviderClient):
    """Issues invoices and payment links through a user's Qonto organization."""

    provider = PaymentProvider.QONTO

    def __init__(self, account: PaymentAccount, access_token: str) -> None:
        """
        Build the provider for a connected account, guarding the environment.

        Args:
            account: The user's connected Qonto account.
            access_token: A valid (refreshed if needed) OAuth access token.

        Raises:
            QontoEnvironmentError: If the runtime environment is inconsistent
                with itself or with the account's stored environment.
        """
        self._account = account
        self._access_token = access_token
        self._assert_environment_consistent()

    def _assert_environment_consistent(self) -> None:
        """
        Fail loudly on any environment inconsistency before a call goes out.

        Raises:
            QontoEnvironmentError: On an unknown environment, a sandbox runtime
                with no staging token, or a runtime/account environment mismatch.
        """
        runtime = settings.qonto_environment
        valid = {environment.value for environment in PaymentEnvironment}
        if runtime not in valid:
            raise QontoEnvironmentError(f"QONTO_ENVIRONMENT is '{runtime}', expected one of {sorted(valid)}.")
        if runtime == PaymentEnvironment.SANDBOX.value and not settings.qonto_staging_token:
            raise QontoEnvironmentError("Sandbox runtime without QONTO_STAGING_TOKEN — refusing to call Qonto.")
        if self._account.environment != runtime:
            raise QontoEnvironmentError(
                f"Account credentials belong to '{self._account.environment}' but the runtime is '{runtime}'."
            )

    def _authorized_headers(self) -> dict[str, str]:
        """
        Build the request headers, adding the staging-token header in sandbox.

        Returns:
            Headers carrying the bearer token (+ ``X-Qonto-Staging-Token`` in sandbox).
        """
        headers = {"Authorization": f"Bearer {self._access_token}"}
        if settings.qonto_environment == PaymentEnvironment.SANDBOX.value:
            headers["X-Qonto-Staging-Token"] = settings.qonto_staging_token
        return headers

    async def _request(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> dict:
        """
        Call the Qonto Business API and return the parsed JSON body.

        Args:
            method: HTTP verb.
            path: Path under ``/v2`` (e.g. ``/clients``).
            params: Optional query parameters.
            json: Optional JSON request body.

        Returns:
            The parsed response body.

        Raises:
            Exception: With the response text when the call fails.
        """
        url = f"{settings.qonto_api_base_url}/v2{path}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method, url, headers=self._authorized_headers(), params=params, json=json, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as error:
            logger.error("Qonto API %s %s failed: %s", method, path, error.response.text)
            raise Exception(f"Qonto API error ({error.response.status_code}): {error.response.text}")

    async def ensure_client(self, client: BillingClient) -> str:
        """
        Find a Qonto client by email or create one, returning its id.

        Args:
            client: The billing counterpart details.

        Returns:
            The Qonto client id.
        """
        if client.email:
            found = await self._request("GET", "/clients", params={"filter[email]": client.email})
            existing = found.get("clients") or []
            if existing:
                return existing[0]["id"]

        body: dict = {"kind": "company", "name": client.name, "currency": "EUR", "locale": "FR"}
        if client.email:
            body["email"] = client.email
        address = {
            key: value
            for key, value in {
                "street_address": client.address,
                "city": client.city,
                "zip_code": client.zip_code,
                "country_code": client.country_code,
            }.items()
            if value
        }
        if address:
            body["billing_address"] = address
        if client.tax_id:
            body["tax_identification_number"] = client.tax_id
        if client.vat_number:
            body["vat_number"] = client.vat_number

        created = await self._request("POST", "/clients", json=body)
        return created["client"]["id"]

    async def create_invoice(self, client_id: str, request: InvoiceRequest) -> IssuedInvoice:
        """
        Issue a finalized Qonto invoice and return its artifacts.

        Args:
            client_id: Qonto client id from :meth:`ensure_client`.
            request: The invoice details.

        Returns:
            The issued invoice (``payment_url`` is the transfer-payable Qonto page;
            a card button is added best-effort when the payment-links provider is on).

        Raises:
            ValueError: When no IBAN is configured for the account.
        """
        if not self._account.qonto_iban:
            raise ValueError("Configurez l'IBAN Qonto dans les réglages avant d'émettre une facture.")

        today = datetime.now(UTC).date()
        currency = (request.currency or "EUR").upper()
        body = {
            "client_id": client_id,
            "issue_date": today.isoformat(),
            "due_date": (today + timedelta(days=_INVOICE_DUE_DAYS)).isoformat(),
            "currency": currency,
            "status": "unpaid",
            "payment_methods": {"iban": self._account.qonto_iban},
            "items": [
                {
                    "title": request.label,
                    "description": request.description or request.label,
                    "quantity": "1",
                    "unit": "unit",
                    "unit_price": {"value": f"{request.amount_cents / 100:.2f}", "currency": currency},
                    "vat_rate": _VAT_RATE,
                    "vat_exemption_reason": _VAT_EXEMPTION_REASON,
                }
            ],
        }
        invoice = (await self._request("POST", "/client_invoices", json=body))["client_invoice"]
        await self._enable_card_payment(invoice["id"])
        return IssuedInvoice(
            provider=self.provider.value,
            invoice_id=invoice["id"],
            invoice_number=invoice.get("number"),
            payment_url=invoice.get("invoice_url"),
        )

    async def _enable_card_payment(self, invoice_id: str) -> None:
        """
        Best-effort: attach a card payment link to the invoice's pay page.

        The invoice is transfer-payable without this; a card button only appears
        when the user's payment-links (Mollie) provider is connected, so a failure
        here is logged and swallowed rather than failing the sale.

        Args:
            invoice_id: The issued invoice's id.
        """
        try:
            await self._request(
                "POST",
                "/payment_links",
                json={"invoice_id": invoice_id, "potential_payment_methods": ["credit_card", "apple_pay"]},
            )
        except Exception:
            logger.info("Qonto card payment link not created for invoice %s — transfer only.", invoice_id)

    async def get_invoice_pdf(self, invoice_id: str) -> bytes:
        """
        Fetch the invoice PDF bytes once Qonto has generated it.

        Args:
            invoice_id: The Qonto invoice id.

        Returns:
            The raw PDF bytes.

        Raises:
            RuntimeError: When the PDF is still not ready after polling.
        """
        attachment_id = await self._await_attachment_id(invoice_id)
        attachment = (await self._request("GET", f"/attachments/{attachment_id}"))["attachment"]
        async with httpx.AsyncClient() as client:
            response = await client.get(attachment["url"], timeout=60.0)
            response.raise_for_status()
            return response.content

    async def _await_attachment_id(self, invoice_id: str) -> str:
        """
        Poll the invoice until its (asynchronously generated) PDF attachment exists.

        Args:
            invoice_id: The Qonto invoice id.

        Returns:
            The attachment id of the generated PDF.

        Raises:
            RuntimeError: When no attachment appears within the poll budget.
        """
        for attempt in range(_PDF_POLL_ATTEMPTS):
            invoice = (await self._request("GET", f"/client_invoices/{invoice_id}"))["client_invoice"]
            attachment_id = invoice.get("attachment_id")
            if attachment_id:
                return attachment_id
            if attempt < _PDF_POLL_ATTEMPTS - 1:
                await asyncio.sleep(_PDF_POLL_DELAY_SECONDS)
        raise RuntimeError(f"Qonto invoice {invoice_id} PDF not ready after {_PDF_POLL_ATTEMPTS} attempts.")

    async def check_paid(self, invoice_id: str) -> PaymentState:
        """
        Read the invoice status from Qonto.

        Args:
            invoice_id: The Qonto invoice id.

        Returns:
            The normalized payment state (``paid`` → paid).
        """
        invoice = (await self._request("GET", f"/client_invoices/{invoice_id}"))["client_invoice"]
        status = invoice.get("status")
        return PaymentState(is_paid=status == "paid", raw_status=status)
