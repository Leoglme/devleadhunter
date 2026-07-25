"""Payment-account routes — connect/disconnect a user's encashment provider.

Qonto is admin-only (its OAuth app only covers its owner's organization); Stripe
Connect is open to every user. The provider does all invoicing — these routes
only manage the connection.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from enums.payment_provider import PaymentProvider
from models.user import User
from schemas.payment_account import (
    ConnectUrlResponse,
    PaymentAccountStatus,
    QontoApiKeyRequest,
    QontoIbanRequest,
)
from services.auth_service import require_admin, require_auth
from services.payment_account_service import payment_account_service

router = APIRouter(prefix="/payment-accounts", tags=["payment-accounts"])
logger = logging.getLogger(__name__)

_BILLING_SETTINGS_PATH = "/dashboard/settings/billing"


def _billing_redirect(outcome_param: str) -> RedirectResponse:
    """
    Redirect the browser back to the billing settings page with an outcome flag.

    Args:
        outcome_param: Query string such as ``qonto=connected`` or ``qonto=error``.

    Returns:
        A 302 redirect to the billing settings page.
    """
    base = (getattr(settings, "frontend_url", "") or "http://localhost:3000").rstrip("/")
    return RedirectResponse(url=f"{base}{_BILLING_SETTINGS_PATH}?{outcome_param}")


@router.get("/status", response_model=PaymentAccountStatus)
async def get_status(current_user: User = Depends(require_auth), db: Session = Depends(get_db)) -> PaymentAccountStatus:
    """Return the current user's encashment-provider status (no secrets)."""
    return payment_account_service.build_status(db, current_user)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(current_user: User = Depends(require_auth), db: Session = Depends(get_db)) -> None:
    """Disconnect and forget the current user's encashment provider."""
    payment_account_service.disconnect(db, current_user.id)


# ---------------------------------------------------------------------- #
# Qonto — admin only
# ---------------------------------------------------------------------- #


@router.post("/qonto/authorize", response_model=ConnectUrlResponse)
async def qonto_authorize(current_user: User = Depends(require_admin)) -> ConnectUrlResponse:
    """Return the Qonto OAuth authorization URL to redirect the admin to."""
    return ConnectUrlResponse(url=payment_account_service.qonto_authorize_url(current_user.id))


@router.get("/qonto/callback")
async def qonto_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """
    Qonto OAuth redirect target: exchange the code and store the tokens.

    Hit by the browser without a JWT, so the owner is carried in ``state``
    (``user_<id>``, set at authorize time) — same pattern as the Gmail callback.
    """
    if error or not code:
        logger.warning("[Qonto OAuth] Callback without code (error=%r)", error)
        return _billing_redirect("qonto=error")
    if not state.startswith("user_"):
        logger.warning("[Qonto OAuth] Callback with unexpected state=%r", state)
        return _billing_redirect("qonto=error")
    try:
        user_id = int(state.removeprefix("user_"))
    except ValueError:
        return _billing_redirect("qonto=error")

    try:
        await payment_account_service.complete_qonto_oauth(db, user_id, code)
        return _billing_redirect("qonto=connected")
    except Exception as exc:
        logger.error("[Qonto OAuth] Callback failed for user %s: %s", user_id, exc)
        return _billing_redirect("qonto=error")


@router.post("/qonto/api-key", response_model=PaymentAccountStatus)
async def set_qonto_api_key(
    body: QontoApiKeyRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaymentAccountStatus:
    """Admin-only fallback: connect Qonto with an API key instead of OAuth."""
    payment_account_service.set_qonto_api_key(db, current_user.id, body.login, body.secret)
    return payment_account_service.build_status(db, current_user)


@router.put("/qonto/iban", response_model=PaymentAccountStatus)
async def set_qonto_iban(
    body: QontoIbanRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaymentAccountStatus:
    """Store the IBAN printed on Qonto invoices (captured manually, unread by API)."""
    try:
        payment_account_service.set_qonto_iban(db, current_user.id, body.iban)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return payment_account_service.build_status(db, current_user)


# ---------------------------------------------------------------------- #
# Stripe — open to every user
# ---------------------------------------------------------------------- #


@router.post("/stripe/onboard", response_model=ConnectUrlResponse)
async def stripe_onboard(
    current_user: User = Depends(require_auth), db: Session = Depends(get_db)
) -> ConnectUrlResponse:
    """
    Create/resume the user's Stripe Connect account and return its onboarding URL.

    Stripe sends the browser back to the billing settings page (no JWT on that
    redirect); the page then calls ``/stripe/refresh`` to pull the final status.
    """
    base = (getattr(settings, "frontend_url", "") or "http://localhost:3000").rstrip("/")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe n'est pas configuré.")
    try:
        url = payment_account_service.start_stripe_onboarding(
            db,
            current_user.id,
            return_url=f"{base}{_BILLING_SETTINGS_PATH}?stripe=return",
            refresh_url=f"{base}{_BILLING_SETTINGS_PATH}?stripe=refresh",
        )
    except Exception as exc:
        logger.error("[Stripe Connect] Onboarding start failed for user %s: %s", current_user.id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ConnectUrlResponse(url=url)


@router.post("/stripe/refresh", response_model=PaymentAccountStatus)
async def stripe_refresh(
    current_user: User = Depends(require_auth), db: Session = Depends(get_db)
) -> PaymentAccountStatus:
    """Re-read the user's Stripe account status after onboarding returns."""
    account = payment_account_service.get_for_user(db, current_user.id)
    if account is None or account.provider != PaymentProvider.STRIPE.value or not account.stripe_account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun compte Stripe à rafraîchir.")
    payment_account_service.refresh_stripe_status(db, account)
    return payment_account_service.build_status(db, current_user)
