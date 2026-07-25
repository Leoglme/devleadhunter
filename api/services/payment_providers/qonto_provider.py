"""Qonto implementation of the encashment contract.

The invoice/payment-link/PDF/status calls land in the next ticket ("Facture,
lien de paiement et email de vente"); what lives here now is the safety-critical
foundation both those calls depend on: the environment guard and the authorized
request headers. The guard is what makes it impossible to hit Léo's real
organization from a sandbox-configured runtime, and vice versa.
"""

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

    async def ensure_client(self, client: BillingClient) -> str:
        """Create/find the Qonto client (``POST /v2/clients``). See ticket 2."""
        raise NotImplementedError("Qonto ensure_client — implemented in the invoice/email ticket.")

    async def create_invoice(self, client_id: str, request: InvoiceRequest) -> IssuedInvoice:
        """Create the client invoice (``POST /v2/client_invoices``). See ticket 2."""
        raise NotImplementedError("Qonto create_invoice — implemented in the invoice/email ticket.")

    async def get_invoice_pdf(self, invoice_id: str) -> bytes:
        """Fetch the invoice PDF via its ``attachment_id``. See ticket 2."""
        raise NotImplementedError("Qonto get_invoice_pdf — implemented in the invoice/email ticket.")

    async def check_paid(self, invoice_id: str) -> PaymentState:
        """Read the invoice status (``GET /v2/client_invoices/{id}``). See ticket 2."""
        raise NotImplementedError("Qonto check_paid — implemented in the invoice/email ticket.")
