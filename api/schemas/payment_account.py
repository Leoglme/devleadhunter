"""Pydantic schemas for the payment (encashment) account settings page."""

from pydantic import BaseModel, Field


class PaymentAccountStatus(BaseModel):
    """What the Facturation & paiement settings page needs to render.

    Never carries secrets: OAuth tokens and the API secret stay server-side.
    The IBAN is returned because it is printed on every invoice — not a secret.
    """

    connected_provider: str | None = None
    is_connected: bool = False
    environment: str | None = None
    display_name: str | None = None

    # Qonto specifics
    qonto_available: bool = False
    qonto_iban: str | None = None
    has_qonto_api_key: bool = False

    # Stripe specifics
    stripe_charges_enabled: bool = False
    stripe_details_submitted: bool = False


class ConnectUrlResponse(BaseModel):
    """A URL to redirect the user to (OAuth authorize or Stripe onboarding)."""

    url: str


class QontoApiKeyRequest(BaseModel):
    """Admin-only fallback: connect Qonto with an API key instead of OAuth."""

    login: str = Field(..., min_length=1)
    secret: str = Field(..., min_length=1)


class QontoIbanRequest(BaseModel):
    """The IBAN to print on Qonto invoices (captured manually, unread by API)."""

    iban: str = Field(..., min_length=1, max_length=64)
