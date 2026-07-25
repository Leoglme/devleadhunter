"""Payment-account routes — connect/disconnect a user's encashment provider.

Qonto is admin-only (its OAuth app only covers its owner's organization); Stripe
Connect is open to every user. The provider does all invoicing — these routes
only manage the connection.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
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


def _connection_result_page(*, provider: str, ok: bool) -> HTMLResponse:
    """
    Render a self-contained page shown at the end of a provider connection.

    The OAuth / onboarding flow runs in the system browser (especially in the
    desktop app), so instead of redirecting to a front-end route that the
    browser may not serve, we render a standalone "you can close this tab" page.
    The app itself detects the connection by polling its status.

    Args:
        provider: Human provider name (``Qonto`` / ``Stripe``).
        ok: Whether the connection succeeded.

    Returns:
        A minimal themed HTML page.
    """
    icon = "✅" if ok else "⚠️"
    title = f"{provider} connecté" if ok else f"Connexion {provider} échouée"
    message = (
        "Vous pouvez fermer cet onglet et revenir à DevLeadHunter."
        if ok
        else "Fermez cet onglet et réessayez depuis DevLeadHunter."
    )
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/><title>{title}</title></head>
<body style="margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#0d0d0f;color:#fff;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
<div style="text-align:center;max-width:420px;padding:2rem;">
<div style="font-size:3rem;line-height:1;">{icon}</div>
<h1 style="margin:1rem 0 .5rem;font-size:1.4rem;">{title}</h1>
<p style="margin:0;color:#a1a1aa;font-size:.95rem;line-height:1.5;">{message}</p>
</div></body></html>"""
    return HTMLResponse(content=html, status_code=200)


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
) -> HTMLResponse:
    """
    Qonto OAuth redirect target: exchange the code and store the tokens.

    Hit by the system browser without a JWT, so the owner is carried in ``state``
    (``user_<id>``, set at authorize time) — same pattern as the Gmail callback.
    Renders a standalone result page; the app polls its status to reflect it.
    """
    if error or not code:
        logger.warning("[Qonto OAuth] Callback without code (error=%r)", error)
        return _connection_result_page(provider="Qonto", ok=False)
    if not state.startswith("user_"):
        logger.warning("[Qonto OAuth] Callback with unexpected state=%r", state)
        return _connection_result_page(provider="Qonto", ok=False)
    try:
        user_id = int(state.removeprefix("user_"))
    except ValueError:
        return _connection_result_page(provider="Qonto", ok=False)

    try:
        await payment_account_service.complete_qonto_oauth(db, user_id, code)
        return _connection_result_page(provider="Qonto", ok=True)
    except Exception as exc:
        logger.error("[Qonto OAuth] Callback failed for user %s: %s", user_id, exc)
        return _connection_result_page(provider="Qonto", ok=False)


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

    Stripe sends the browser to a standalone result page (no JWT, and the desktop
    app doesn't serve a front-end route); the app polls ``/stripe/refresh`` to pull
    the final status.
    """
    api_base = (getattr(settings, "api_base_url", "") or "http://localhost:8000").rstrip("/")
    return_url = f"{api_base}/api/v1/payment-accounts/stripe/return"
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe n'est pas configuré.")
    try:
        url = payment_account_service.start_stripe_onboarding(
            db,
            current_user.id,
            return_url=return_url,
            refresh_url=return_url,
        )
    except Exception as exc:
        logger.error("[Stripe Connect] Onboarding start failed for user %s: %s", current_user.id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ConnectUrlResponse(url=url)


@router.get("/stripe/return")
async def stripe_return() -> HTMLResponse:
    """Standalone page shown when Stripe onboarding returns; the app polls the status."""
    return _connection_result_page(provider="Stripe", ok=True)


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
