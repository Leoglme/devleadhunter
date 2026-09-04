"""Domain routes — suggest a ``.fr`` for a prospect and check availability.

Both endpoints are credential-free (AFNIC RDAP + Groq): they power the "pre-filled,
ideally-available domain" step of the post-sale go-live. The actual registration + DNS
(per-user ``DomainProvider``) come in a later increment, gated on the operator's OVH keys.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from models.prospect_db import ProspectDB
from models.user import User
from services.auth_service import require_auth, require_super_admin
from services.domain.availability import is_fr_available
from services.domain.ovh_catalog import fr_first_year_price_eur
from services.domain.ovh_provider import DomainProviderError, ovh_domain_provider
from services.domain.suggestion_service import domain_suggestion_service
from services.organization_service import organization_service

router = APIRouter(prefix="/domains", tags=["domains"])


class DomainAvailability(BaseModel):
    """Availability + estimated price for one ``.fr`` domain."""

    domain: str = Field(..., description="Full .fr domain, e.g. « tacos-maru.fr »")
    available: bool | None = Field(..., description="True = free, False = taken, null = could not check")
    price_eur: float | None = Field(..., description="Estimated first-year price (TTC), null when unknown")


class DomainSuggestionsResponse(BaseModel):
    """The best pre-fill plus every candidate considered."""

    suggested: str | None = Field(..., description="Best domain to pre-fill, null when none could be built")
    candidates: list[DomainAvailability] = Field(default_factory=list, description="All candidates, best first")


def _normalize_fr(name: str) -> str:
    """Coerce raw input to a single ``<label>.fr`` (accepts « chezmimon » or « chezmimon.fr »)."""
    cleaned = (name or "").strip().lower().rstrip(".")
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de domaine vide")
    if cleaned.endswith(".fr"):
        cleaned = cleaned[:-3]
    label = cleaned.split(".")[0]
    if not label:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de domaine invalide")
    return f"{label}.fr"


@router.get(
    "/availability",
    response_model=DomainAvailability,
    summary="Check whether a .fr domain is free",
    description="Query the AFNIC registry (RDAP) for a single .fr domain.",
)
async def check_availability(name: str, current_user: User = Depends(require_auth)) -> DomainAvailability:
    """Return the availability of one ``.fr`` domain (best-effort)."""
    del current_user
    domain = _normalize_fr(name)
    return DomainAvailability(
        domain=domain,
        available=await is_fr_available(domain),
        price_eur=await fr_first_year_price_eur(),
    )


@router.get(
    "/suggestions",
    response_model=DomainSuggestionsResponse,
    summary="Suggest a .fr domain for a prospect",
    description="Build logical .fr candidates from the prospect (name/city/trade), enrich with AI, check availability.",
)
async def suggest_domains(
    prospect_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DomainSuggestionsResponse:
    """Suggest a pre-fillable ``.fr`` domain for a prospect the caller can see.

    Raises:
        HTTPException: 404 when the prospect does not exist or is not visible to the caller.
    """
    # Visibility: the prospect must belong to the caller or their organization (no cross-org leak).
    row = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")
    if row.user_id != current_user.id:
        org_id = organization_service.user_org_id(db, current_user.id)
        if org_id is None or row.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")

    suggestion = await domain_suggestion_service.suggest(name=row.name, city=row.city, category=row.category)
    return DomainSuggestionsResponse(
        suggested=suggestion.suggested,
        candidates=[
            DomainAvailability(domain=c.domain, available=c.available, price_eur=c.price_eur)
            for c in suggestion.candidates
        ],
    )


class RegistrarStatus(BaseModel):
    """Whether the OVH registrar is wired, and which account it points at."""

    configured: bool = Field(..., description="True when the OVH credentials are present")
    account: str | None = Field(None, description="OVH account id (nichandle) when the signed check succeeds")


class DomainActionRequest(BaseModel):
    """Payload naming a single .fr domain for a registrar action."""

    domain: str = Field(..., description="Full .fr domain, e.g. « tacos-maru.fr »")


@router.get(
    "/registrar-status",
    response_model=RegistrarStatus,
    summary="Check the OVH registrar connection (no spend)",
    description="Super-admin. Does a signed GET /me to prove the keys + signature work, without ordering anything.",
)
async def registrar_status(current_user: User = Depends(require_super_admin)) -> RegistrarStatus:
    """Return whether OVH is configured and reachable (a safe, no-spend auth check)."""
    del current_user
    if not ovh_domain_provider.is_configured:
        return RegistrarStatus(configured=False, account=None)
    return RegistrarStatus(configured=True, account=await ovh_domain_provider.account_id())


class DomainRegisterResult(BaseModel):
    """Outcome of a registrar purchase."""

    domain: str = Field(..., description="The domain ordered")
    ovh_order_id: int | None = Field(None, description="OVH order id, when returned")


@router.post(
    "/register",
    response_model=DomainRegisterResult,
    summary="Buy a .fr domain on the operator's OVH account (spends money)",
    description="Super-admin, deliberate action. Registration is async at OVH — point the DNS once the domain is active.",
)
async def register_domain(
    request: DomainActionRequest,
    current_user: User = Depends(require_super_admin),
) -> DomainRegisterResult:
    """Register a ``.fr`` domain via OVH (real purchase). Super-admin only.

    Raises:
        HTTPException: 503 when OVH is not configured, 502 when the OVH order fails.
    """
    del current_user
    domain = _normalize_fr(request.domain)
    if not ovh_domain_provider.is_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OVH n'est pas configuré")
    try:
        order = await ovh_domain_provider.register(domain)
    except DomainProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return DomainRegisterResult(domain=domain, ovh_order_id=order.get("orderId"))


@router.post(
    "/point-dns",
    summary="Point a domain's apex DNS at the Vercel demo-host",
    description="Super-admin. Run once the domain is active at OVH (registration is async).",
)
async def point_domain_dns(
    request: DomainActionRequest,
    current_user: User = Depends(require_super_admin),
) -> dict[str, str]:
    """Set the domain's apex ``A`` record to Vercel and refresh the zone. Super-admin only.

    Raises:
        HTTPException: 503 when OVH is not configured, 502 when the DNS update fails.
    """
    del current_user
    domain = _normalize_fr(request.domain)
    if not ovh_domain_provider.is_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OVH n'est pas configuré")
    try:
        await ovh_domain_provider.point_to_vercel(domain)
    except DomainProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"status": "ok", "domain": domain}
