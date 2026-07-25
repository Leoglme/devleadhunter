"""Provider-agnostic contract for issuing a sales invoice and collecting payment.

Four operations, implemented once per provider:

* ``ensure_client``    — create/find the billing counterpart, return its id
* ``create_invoice``   — issue the invoice (+ payment link), return its artifacts
* ``get_invoice_pdf``  — fetch the invoice PDF bytes (for the email attachment)
* ``check_paid``       — read the current payment status (reconciliation)

The provider is the source of truth for numbering, legal mentions and payment
status; DevLeadHunter never invents an invoice number and never pushes a "paid"
state back to the provider.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from enums.payment_provider import PaymentProvider


@dataclass
class BillingClient:
    """The counterpart an invoice is billed to.

    Pre-filled from prospect enrichment and editable before issuing; a missing
    name/address blocks invoice creation upstream (both providers reject it).
    """

    name: str
    email: str | None = None
    address: str | None = None
    city: str | None = None
    zip_code: str | None = None
    country_code: str = "FR"
    vat_number: str | None = None


@dataclass
class InvoiceRequest:
    """Everything needed to issue one sales invoice for an order."""

    client: BillingClient
    amount_cents: int
    currency: str
    label: str
    description: str | None = None


@dataclass
class IssuedInvoice:
    """Artifacts returned once the provider has issued the invoice.

    ``payment_url`` may be ``None`` when only bank transfer is available (Qonto
    without a card payment link attached); ``payment_provider`` is stamped so a
    later status check hits the right provider.
    """

    provider: str
    invoice_id: str
    invoice_number: str | None
    payment_url: str | None
    pdf_url: str | None = None


@dataclass
class PaymentState:
    """Normalized payment status of an issued invoice."""

    is_paid: bool
    raw_status: str | None = None


class PaymentProviderClient(ABC):
    """Interface every encashment provider implements."""

    provider: PaymentProvider

    @abstractmethod
    async def ensure_client(self, client: BillingClient) -> str:
        """
        Create or find the billing counterpart and return its provider id.

        Args:
            client: The billing counterpart details.

        Returns:
            The provider-side client identifier.
        """

    @abstractmethod
    async def create_invoice(self, client_id: str, request: InvoiceRequest) -> IssuedInvoice:
        """
        Issue an invoice (and its payment link) for the given client.

        Args:
            client_id: Provider-side client id from :meth:`ensure_client`.
            request: The invoice details.

        Returns:
            The issued invoice's artifacts.
        """

    @abstractmethod
    async def get_invoice_pdf(self, invoice_id: str) -> bytes:
        """
        Fetch the invoice PDF bytes, for attaching to the sale email.

        Args:
            invoice_id: Provider-side invoice id.

        Returns:
            The raw PDF bytes.
        """

    @abstractmethod
    async def check_paid(self, invoice_id: str) -> PaymentState:
        """
        Read the current payment status of an issued invoice.

        Args:
            invoice_id: Provider-side invoice id.

        Returns:
            The normalized payment state.
        """
