"""
Payment routes for Stripe integration.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
import stripe

from core.database import get_db
from core.config import settings
from schemas.payment import CheckoutSessionCreate, CheckoutSessionResponse, PaymentStatusResponse
from services.auth_service import require_auth
from services.stripe_payment_service import StripePaymentService
from models.user import User

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    checkout_data: CheckoutSessionCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
) -> CheckoutSessionResponse:
    """
    Create a Stripe Checkout Session for credit purchase.
    
    Args:
        checkout_data: Checkout session creation data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Checkout session information with URL to redirect user
        
    Raises:
        HTTPException: If Stripe is not configured or creation fails
    """
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe payment service is not configured"
        )
    
    try:
        from services.stripe_payment_service import get_stripe_service
        payment_service = get_stripe_service()
        if not payment_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe payment service is not available"
            )
        
        # Use default URLs if not provided
        frontend_url = settings.frontend_url.rstrip('/')
        success_url = checkout_data.success_url or f"{frontend_url}/dashboard/buy-credits?success=true"
        cancel_url = checkout_data.cancel_url or f"{frontend_url}/dashboard/buy-credits?canceled=true"
        
        session_data = payment_service.create_checkout_session(
            db=db,
            user_id=current_user.id,
            credits=checkout_data.credits,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return CheckoutSessionResponse(
            session_id=session_data['id'],
            url=session_data['url'],
            amount=session_data['amount'],
            credits=session_data['credits']
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="stripe-signature")
) -> Dict[str, str]:
    """
    Handle Stripe webhook events.
    
    This endpoint processes payment completion events from Stripe
    and adds credits to user accounts.
    
    Args:
        request: FastAPI request object
        db: Database session
        stripe_signature: Stripe webhook signature from header
        
    Returns:
        Success response
        
    Raises:
        HTTPException: If webhook verification fails
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header"
        )
    
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook is not configured"
        )
    
    try:
        # Get raw request body
        payload = await request.body()
        
        # Verify webhook signature and get event
        from services.stripe_payment_service import get_stripe_service
        payment_service = get_stripe_service()
        if not payment_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe payment service is not available"
            )
        event = payment_service.verify_webhook_signature(payload, stripe_signature)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
        
        # Process webhook event
        success = payment_service.handle_webhook_event(db, event)
        
        if success:
            return {"status": "success", "message": "Webhook processed successfully"}
        else:
            return {"status": "ignored", "message": "Webhook event ignored"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/public-key")
async def get_stripe_public_key() -> Dict[str, str]:
    """
    Get Stripe public key for frontend.
    
    Returns:
        Stripe public key (safe to expose to frontend)
        
    Raises:
        HTTPException: If Stripe is not configured
    """
    if not settings.stripe_public_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe public key is not configured"
        )
    
    return {"public_key": settings.stripe_public_key}

