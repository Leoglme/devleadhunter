"""Stripe implementation of the encashment contract (Connect Standard).

All calls run against the platform key with the ``Stripe-Account`` header set to
the connected account (``acct_...``) — direct charges, so funds settle on the
connected account, never on the platform. The invoice/PDF/status calls land in
the next ticket; the connection (Account Links onboarding) and the platform
commission (``application_fee``) are wired here in the socle.
"""

from enums.payment_provider import PaymentProvider
from models.payment_account import PaymentAccount
from services.payment_providers.base import (
    BillingClient,
    InvoiceRequest,
    IssuedInvoice,
    PaymentProviderClient,
    PaymentState,
)


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
            StripeConnectError: If the account cannot yet accept charges.
        """
        if not account.stripe_account_id:
            raise StripeConnectError("No Stripe connected account id on this payment account.")
        if not account.stripe_charges_enabled:
            raise StripeConnectError("Stripe connected account cannot accept charges yet (onboarding incomplete).")
        self._account = account
        self._connected_account_id = account.stripe_account_id

    async def ensure_client(self, client: BillingClient) -> str:
        """Create/find the Stripe customer on the connected account. See ticket 2."""
        raise NotImplementedError("Stripe ensure_client — implemented in the invoice/email ticket.")

    async def create_invoice(self, client_id: str, request: InvoiceRequest) -> IssuedInvoice:
        """Create + finalize the Stripe invoice (with any application_fee). See ticket 2."""
        raise NotImplementedError("Stripe create_invoice — implemented in the invoice/email ticket.")

    async def get_invoice_pdf(self, invoice_id: str) -> bytes:
        """Fetch the hosted invoice PDF. See ticket 2."""
        raise NotImplementedError("Stripe get_invoice_pdf — implemented in the invoice/email ticket.")

    async def check_paid(self, invoice_id: str) -> PaymentState:
        """Read the invoice status on the connected account. See ticket 2."""
        raise NotImplementedError("Stripe check_paid — implemented in the invoice/email ticket.")
