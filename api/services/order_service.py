"""
Order / sales orchestration.

Covers the end-of-tunnel: create a sale (manual for now), generate a Stripe
payment link, email it to the client (with preview), mark it paid (manually or
via the Stripe webhook), then fulfil it (deploy to prod + hand over CMS access).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from enums.order_status import WON_STATUSES, OrderStatus
from enums.product_type import PRODUCT_DEFAULT_AMOUNT_CENTS, PRODUCT_LABELS, ProductType
from models.order import Order
from models.prospect_db import ProspectDB
from models.user import User

if TYPE_CHECKING:
    from models.demo_site import DemoSite

logger = logging.getLogger(__name__)

# Post-payment fulfilment recovery bounds.
# A paid order that never went live is retried by the background recovery loop up to
# this many times, but only while it is recent enough (older ones need a human).
MAX_FULFILMENT_ATTEMPTS: int = 8
FULFILMENT_MAX_AGE_DAYS: int = 14
# Statuses that mean "paid but not yet fully delivered" → eligible for a retry.
_RETRYABLE_STATUSES: tuple[str, ...] = (OrderStatus.PAID.value, OrderStatus.DEPLOYING.value)
# Terminal states that must never be re-fulfilled.
_TERMINAL_STATUSES: tuple[str, ...] = (
    OrderStatus.DELIVERED.value,
    OrderStatus.REFUNDED.value,
    OrderStatus.CANCELLED.value,
)
_FRENCH_ZIP_PATTERN: re.Pattern[str] = re.compile(r"\b(\d{5})\b")


def _split_postal_address(address: str | None, city: str | None) -> tuple[str | None, str | None, str | None]:
    """
    Split a free-form scraped address into (street, zip code, city).

    Scrapers return a single line ("12 rue de la Paix, 75002 Paris"), whereas the
    payment providers want the parts separately. The last 5-digit group is the
    zip code — a leading one would be a street number.

    Args:
        address: The scraped street address, if any.
        city: The prospect's city, used when the address carries none.

    Returns:
        Tuple of (street, zip code, city), each None when undeterminable.
    """
    if not address:
        return None, None, (city or None)

    single_line = " ".join(address.split())
    zip_matches = list(_FRENCH_ZIP_PATTERN.finditer(single_line))
    if not zip_matches:
        return single_line or None, None, (city or None)

    zip_match = zip_matches[-1]
    street = single_line[: zip_match.start()].strip(" ,")
    trailing_city = single_line[zip_match.end() :].strip(" ,")
    return (street or None), zip_match.group(1), (city or trailing_city or None)


def format_amount(amount_cents: int, currency: str = "eur") -> str:
    """Format an amount in cents as a human string (e.g. "500 €")."""
    symbol = "€" if (currency or "eur").lower() == "eur" else currency.upper()
    euros = amount_cents / 100
    text = f"{euros:.0f}" if euros == int(euros) else f"{euros:.2f}"
    return f"{text} {symbol}"


class OrderService:
    """Manage commercial orders scoped to a user."""

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def list_for_user(self, db: Session, user_id: int) -> list[Order]:
        """List a user's orders, newest first."""
        return (
            db.query(Order)
            .filter(Order.user_id == user_id, Order.deleted_at.is_(None))
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_for_user(self, db: Session, user_id: int, order_id: int) -> Order | None:
        """Fetch a user's order by id."""
        return (
            db.query(Order).filter(Order.id == order_id, Order.user_id == user_id, Order.deleted_at.is_(None)).first()
        )

    def get_by_id(self, db: Session, order_id: int) -> Order | None:
        """Fetch an order by id (used by webhook / fulfilment)."""
        return db.query(Order).filter(Order.id == order_id, Order.deleted_at.is_(None)).first()

    def get_by_payment_link_id(self, db: Session, payment_link_id: str) -> Order | None:
        """Resolve an order from a Stripe payment link id."""
        if not payment_link_id:
            return None
        return (
            db.query(Order).filter(Order.stripe_payment_link_id == payment_link_id, Order.deleted_at.is_(None)).first()
        )

    # ------------------------------------------------------------------ #
    # Mutations
    # ------------------------------------------------------------------ #

    def create(
        self,
        db: Session,
        *,
        user_id: int,
        product_type: str = ProductType.WEBSITE.value,
        prospect_id: int | None = None,
        demo_site_id: int | None = None,
        amount_cents: int | None = None,
        business_name: str | None = None,
        customer_name: str | None = None,
        customer_email: str | None = None,
        domain: str | None = None,
        notes: str | None = None,
    ) -> Order:
        """Create a manual order, pre-filling client info from the prospect when given."""
        if prospect_id and (not business_name or not customer_email):
            prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id, ProspectDB.user_id == user_id).first()
            if prospect:
                business_name = business_name or prospect.name
                customer_email = customer_email or prospect.email

        resolved_amount = (
            amount_cents if amount_cents is not None else PRODUCT_DEFAULT_AMOUNT_CENTS.get(product_type, 50000)
        )

        order = Order(
            user_id=user_id,
            product_type=product_type,
            prospect_id=prospect_id,
            demo_site_id=demo_site_id,
            amount_cents=resolved_amount,
            currency="eur",
            business_name=business_name,
            customer_name=customer_name,
            customer_email=customer_email,
            domain=domain,
            notes=notes,
            status=OrderStatus.DRAFT.value,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    def update(self, db: Session, order: Order, updates: dict[str, Any]) -> Order:
        """Apply editable updates (amount, status, notes, domain, client info, links)."""
        editable = {
            "product_type",
            "amount_cents",
            "status",
            "business_name",
            "customer_name",
            "customer_email",
            "domain",
            "notes",
            "demo_site_id",
            "prospect_id",
        }
        for key, value in updates.items():
            if key in editable:
                setattr(order, key, value)
        db.commit()
        db.refresh(order)
        return order

    def delete(self, db: Session, order: Order) -> None:
        """Soft-delete an order and deactivate its Stripe payment link."""
        if order.stripe_payment_link_id:
            try:
                from services.stripe_payment_service import get_stripe_service

                service = get_stripe_service()
                if service:
                    service.deactivate_payment_link(order.stripe_payment_link_id)
            except Exception:
                logger.warning("Failed to deactivate payment link for order %s", order.id)
        order.deleted_at = datetime.now(UTC)
        order.status = OrderStatus.CANCELLED.value
        db.commit()

    # ------------------------------------------------------------------ #
    # Stripe payment link
    # ------------------------------------------------------------------ #

    def create_payment_link(self, db: Session, order: Order) -> Order:
        """Create (or refresh) the Stripe payment link for an order."""
        from services.stripe_payment_service import get_stripe_service

        service = get_stripe_service()
        if not service:
            raise ValueError("Stripe n'est pas configuré.")
        if not order.amount_cents or order.amount_cents <= 0:
            raise ValueError("Le montant de la commande doit être supérieur à 0.")

        result = service.create_order_payment_link(
            order_id=order.id,
            user_id=order.user_id,
            amount_cents=order.amount_cents,
            currency=order.currency,
            product_label=PRODUCT_LABELS.get(order.product_type, "Site web"),
            business_name=order.business_name,
        )
        order.stripe_payment_link_id = result["payment_link_id"]
        order.stripe_payment_url = result["url"]
        if order.status == OrderStatus.DRAFT.value:
            order.status = OrderStatus.PAYMENT_PENDING.value
        db.commit()
        db.refresh(order)
        return order

    # ------------------------------------------------------------------ #
    # Billing details (reviewed before the invoice is issued)
    # ------------------------------------------------------------------ #

    def billing_details_for_order(self, db: Session, order: Order) -> dict[str, str | None]:
        """
        Return the invoice's billing counterpart, pre-filled from the prospect.

        Stored details win once the operator has reviewed them; otherwise the
        prospect's scraped address is split into street / zip / city so the
        drawer opens on something editable rather than empty.

        Args:
            db: Active database session.
            order: The order being finalized.

        Returns:
            The billing fields expected by the « Finaliser la vente » drawer.
        """
        address, zip_code, city = order.billing_address, order.billing_zip_code, order.billing_city
        if not any((address, zip_code, city)) and order.prospect_id:
            prospect = db.query(ProspectDB).filter(ProspectDB.id == order.prospect_id).first()
            if prospect:
                address, zip_code, city = _split_postal_address(prospect.address, prospect.city)

        return {
            "name": order.business_name or order.customer_name,
            "email": order.customer_email,
            "address": address,
            "city": city,
            "zip_code": zip_code,
            "country_code": order.billing_country_code or "FR",
            "tax_id": order.billing_tax_id,
            "vat_number": order.billing_vat_number,
        }

    def connected_provider(self, db: Session, user: User) -> str | None:
        """
        The encashment provider that will issue the invoice, if any.

        Args:
            db: Active database session.
            user: Owner of the order.

        Returns:
            The provider value, or ``None`` for a fully manual sale.
        """
        from services.payment_account_service import payment_account_service

        account = payment_account_service.get_for_user(db, user.id)
        return account.provider if account is not None and account.is_connected else None

    def missing_billing_fields(self, db: Session, user: User, billing: dict[str, str | None]) -> list[str]:
        """
        List the human labels of the billing fields still required.

        Requirements follow the provider that will invoice: both reject a client
        without a postal address, and Qonto additionally rejects one without a TIN
        (``tin_number`` — the SIREN/SIRET). A fully manual sale (cash, transfer)
        just needs someone to bill and an address to email. The email is checked
        here so a missing one blocks *before* an invoice number is burned.

        Args:
            db: Active database session.
            user: Owner of the order.
            billing: The billing fields to validate.

        Returns:
            The labels of the missing fields (empty when complete).
        """
        from enums.payment_provider import PaymentProvider

        required: dict[str, str] = {"name": "la raison sociale", "email": "l'email du client"}
        provider = self.connected_provider(db, user)
        if provider is not None:
            required |= {"address": "l'adresse", "zip_code": "le code postal", "city": "la ville"}
        if provider == PaymentProvider.QONTO.value:
            required["tax_id"] = "le SIREN / SIRET"
        return [label for key, label in required.items() if not (billing.get(key) or "").strip()]

    def save_billing_details(self, db: Session, order: Order, billing: dict[str, str | None]) -> Order:
        """
        Persist the reviewed billing details on the order.

        Args:
            db: Active database session.
            order: The order being finalized.
            billing: The reviewed billing fields.

        Returns:
            The refreshed order.
        """
        order.business_name = billing.get("name") or order.business_name
        order.customer_email = billing.get("email") or order.customer_email
        order.billing_address = billing.get("address")
        order.billing_city = billing.get("city")
        order.billing_zip_code = billing.get("zip_code")
        order.billing_country_code = (billing.get("country_code") or "FR").upper()
        order.billing_tax_id = billing.get("tax_id")
        order.billing_vat_number = billing.get("vat_number")
        db.commit()
        db.refresh(order)
        return order

    def build_billing_client(self, db: Session, order: Order):
        """
        Build the provider-side billing counterpart from the order.

        Args:
            db: Active database session.
            order: The order being invoiced.

        Returns:
            The :class:`BillingClient` handed to the provider.
        """
        from services.payment_providers import BillingClient

        details = self.billing_details_for_order(db, order)
        return BillingClient(
            name=details["name"] or "Client",
            email=details["email"],
            address=details["address"],
            city=details["city"],
            zip_code=details["zip_code"],
            country_code=details["country_code"] or "FR",
            vat_number=details["vat_number"],
            tax_id=details["tax_id"],
        )

    async def finalize_sale(
        self, db: Session, user: User, order: Order, billing: dict[str, str | None], amount_cents: int
    ) -> Order:
        """
        Save the reviewed billing + amount, then issue the invoice at the provider.

        Args:
            db: Active database session.
            user: Owner of the order (holds the connected provider).
            order: The order being finalized.
            billing: The reviewed billing fields.
            amount_cents: The negotiated amount, in cents.

        Returns:
            The order carrying its issued invoice.

        Raises:
            ValueError: When a provider-required billing field is missing.
        """
        missing = self.missing_billing_fields(db, user, billing)
        if missing:
            raise ValueError(f"Facturation incomplète : renseignez {', '.join(missing)}.")
        if amount_cents <= 0:
            raise ValueError("Le montant de la vente doit être supérieur à 0.")

        self.save_billing_details(db, order, billing)
        if order.amount_cents != amount_cents and not order.invoice_id:
            order.amount_cents = amount_cents
            db.commit()
            db.refresh(order)
        return await self.ensure_invoice(db, user, order)

    # ------------------------------------------------------------------ #
    # Invoice generation (through the user's connected provider)
    # ------------------------------------------------------------------ #

    def platform_commission_cents(self, db: Session, amount_cents: int) -> int | None:
        """
        The platform's cut on a sale, in cents: a percentage plus a fixed part.

        The fixed part is what keeps a small sale worth invoicing (10 % of 10 €
        is 1 €); the total is capped at the sale itself, since Stripe rejects an
        application fee larger than the amount charged.

        Args:
            db: Active database session.
            amount_cents: The invoiced amount.

        Returns:
            The commission in cents, or ``None`` when nothing is configured —
            Stripe then charges the connected account with no application fee.
        """
        from models.credit_settings import CreditSettings

        settings = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
        if settings is None:
            return None
        percent = Decimal(settings.platform_commission_percent)
        fixed_cents = settings.platform_commission_fixed_cents or 0
        if percent <= 0 and fixed_cents <= 0:
            return None
        variable_cents = int((Decimal(amount_cents) * percent / Decimal(100)).to_integral_value(rounding=ROUND_HALF_UP))
        return min(variable_cents + fixed_cents, amount_cents)

    async def _resolve_provider(self, db: Session, user: User):
        """Return the user's connected encashment provider client, or None (manual sale)."""
        from enums.payment_provider import PaymentProvider
        from services.payment_account_service import payment_account_service
        from services.payment_providers import get_payment_provider

        account = payment_account_service.get_for_user(db, user.id)
        if account is None or not account.is_connected:
            return None
        if account.provider == PaymentProvider.QONTO.value:
            token = await payment_account_service.get_valid_qonto_access_token(db, account)
            return get_payment_provider(account, qonto_access_token=token)
        return get_payment_provider(account)

    async def ensure_invoice(self, db: Session, user: User, order: Order) -> Order:
        """
        Ensure the order carries an issued invoice + payment link, reusing any existing one.

        A finalized invoice consumes a number, so an order that already has one is
        never re-issued. With no connected provider, falls back to the legacy platform
        Stripe payment link (no invoice PDF), preserving the previous behaviour.
        """
        if order.invoice_id:
            return order

        provider = await self._resolve_provider(db, user)
        if provider is None:
            if not order.stripe_payment_url:
                self.create_payment_link(db, order)
            if not order.payment_url:
                order.payment_url = order.stripe_payment_url
                db.commit()
                db.refresh(order)
            return order

        from enums.payment_provider import PaymentProvider
        from services.payment_providers import InvoiceRequest

        counterpart = self.build_billing_client(db, order)
        client_id = await provider.ensure_client(counterpart)
        product = PRODUCT_LABELS.get(order.product_type, "Site web")
        label = product if not order.business_name else f"{product} — {order.business_name}"
        # The platform only takes a cut on sales it invoices for someone else.
        commission = (
            self.platform_commission_cents(db, order.amount_cents)
            if provider.provider == PaymentProvider.STRIPE
            else None
        )
        issued = await provider.create_invoice(
            client_id,
            InvoiceRequest(
                client=counterpart,
                amount_cents=order.amount_cents,
                currency=order.currency,
                label=label,
                application_fee_amount=commission,
            ),
        )
        order.payment_provider = issued.provider
        order.invoice_id = issued.invoice_id
        order.invoice_number = issued.invoice_number
        order.payment_url = issued.payment_url
        if order.status == OrderStatus.DRAFT.value:
            order.status = OrderStatus.PAYMENT_PENDING.value
        db.commit()
        db.refresh(order)
        return order

    async def _fetch_invoice_pdf(self, db: Session, user: User, order: Order) -> bytes | None:
        """Best-effort fetch of the invoice PDF for the sale email (None when unavailable)."""
        if not order.invoice_id or not order.payment_provider:
            return None
        try:
            provider = await self._resolve_provider(db, user)
            if provider is None:
                return None
            return await provider.get_invoice_pdf(order.invoice_id)
        except Exception as exc:
            logger.warning("Invoice PDF unavailable for order %s: %s", order.id, exc)
            return None

    async def check_and_mark_paid(self, db: Session, user: User, order: Order) -> bool:
        """
        Reconcile an order against its provider, marking it paid when the invoice is.

        The provider-agnostic complement to the Stripe webhook: Qonto has no "invoice
        paid" webhook, so payment is confirmed by reading the invoice status.

        Args:
            db: Active database session.
            user: Owner of the order (holds the connected provider).
            order: The order to reconcile.

        Returns:
            ``True`` when this call transitioned the order to paid.
        """
        if order.paid_at or not order.invoice_id or not order.payment_provider:
            return False
        provider = await self._resolve_provider(db, user)
        if provider is None:
            return False
        state = await provider.check_paid(order.invoice_id)
        if state.is_paid:
            self.mark_paid(db, order)
            return True
        return False

    # ------------------------------------------------------------------ #
    # Payment-link email (with preview)
    # ------------------------------------------------------------------ #

    def build_payment_email(self, order: Order, sender_name: str) -> dict[str, str]:
        """
        Render the subject + HTML body of the payment-link email for an order.

        Reads as a one-to-one message rather than a campaign: everything is flush
        left, the call to action names the invoice it opens (a stranger asking for
        500 € online is exactly what a scam looks like), and the raw URL sits under
        the button for clients that strip its styling.

        Args:
            order: The order being invoiced.
            sender_name: Display name signing the email.

        Returns:
            The rendered ``subject`` and ``body_html``.
        """
        business = order.business_name or "votre entreprise"
        amount = format_amount(order.amount_cents, order.currency)
        product = PRODUCT_LABELS.get(order.product_type, "site web")
        url = order.payment_url or order.stripe_payment_url or "#"
        attachment_note = " Vous trouverez la facture en pièce jointe." if order.invoice_id else ""
        # Naming the invoice ties the button to the attached PDF — a reference an
        # impersonator would not have.
        action = f"Régler la facture {order.invoice_number}" if order.invoice_number else "Procéder au paiement"

        subject = f"Votre {product} est prêt — finalisons ensemble"
        body_html = f"""
        <div style="font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:#1a1a1a; max-width:560px; margin:0 auto; text-align:left;">
          <p>Bonjour,</p>
          <p>
            Comme convenu, le <strong>{product}</strong> de <strong>{business}</strong> est prêt.
            Pour le mettre en ligne sur votre nom de domaine et vous transmettre vos accès,
            il vous suffit de finaliser le paiement unique de <strong>{amount}</strong> (pas d'abonnement, site à vie).{attachment_note}
          </p>
          <p style="margin:32px 0 12px;">
            <a href="{url}" style="background:#111111; color:#ffffff; text-decoration:none; padding:14px 28px; border-radius:8px; font-weight:600; display:inline-block;">
              {action}
            </a>
          </p>
          <p style="font-size:12px; color:#777; margin:0 0 28px; word-break:break-all;">
            Si le bouton ne s'ouvre pas, copiez ce lien dans votre navigateur :<br/>
            <a href="{url}" style="color:#777;">{url}</a>
          </p>
          <p style="font-size:13px; color:#555;">
            Le règlement se fait sur une page sécurisée, directement depuis la facture.
            Dès réception, je mets votre site en ligne et je vous envoie vos identifiants pour gérer vous-même
            votre contenu.
          </p>
          <p>Une question avant de valider ? Répondez simplement à cet email.</p>
          <p>Bien à vous,<br/>{sender_name}</p>
        </div>
        """.strip()
        return {"subject": subject, "body_html": body_html}

    async def send_payment_email(self, db: Session, user: User, order: Order) -> dict[str, Any]:
        """Send the payment-link email to the client via the user's active sending identity.

        Issues (or reuses) the invoice through the user's provider, attaches its PDF,
        and BCCs the user so the thread lands in their own mailbox (Resend/Gmail send
        via API — nothing reaches their Sent folder otherwise).
        """
        if not order.customer_email:
            raise ValueError("Aucune adresse email client sur la commande.")

        await self.ensure_invoice(db, user, order)

        from services.email_attachment import EmailAttachment
        from services.email_sending_service import EmailSendingService

        attachments: list[EmailAttachment] | None = None
        pdf = await self._fetch_invoice_pdf(db, user, order)
        if pdf:
            label = order.invoice_number or f"commande-{order.id}"
            attachments = [EmailAttachment(filename=f"facture-{label}.pdf", content=pdf)]

        rendered = self.build_payment_email(order, sender_name=user.name)
        sending = EmailSendingService(db)
        result = await sending.send_via_user_identity(
            user_id=user.id,
            recipient_email=order.customer_email,
            recipient_name=order.customer_name or order.business_name,
            subject=rendered["subject"],
            body_html=rendered["body_html"],
            prospect_id=str(order.prospect_id) if order.prospect_id else None,
            bcc=[user.email] if user.email else None,
            attachments=attachments,
            is_transactional=True,
        )
        if result.get("success"):
            order.payment_link_sent_at = datetime.now(UTC)
            if order.status == OrderStatus.DRAFT.value:
                order.status = OrderStatus.PAYMENT_PENDING.value
            db.commit()
            db.refresh(order)
        return result

    # ------------------------------------------------------------------ #
    # Payment confirmation + fulfilment
    # ------------------------------------------------------------------ #

    def mark_paid(
        self,
        db: Session,
        order: Order,
        *,
        stripe_session_id: str | None = None,
        stripe_payment_intent_id: str | None = None,
    ) -> Order:
        """Mark an order as paid (manual or webhook). Idempotent."""
        if order.paid_at:
            return order
        order.paid_at = datetime.now(UTC)
        order.status = OrderStatus.PAID.value
        if stripe_session_id:
            order.stripe_session_id = stripe_session_id
        if stripe_payment_intent_id:
            order.stripe_payment_intent_id = stripe_payment_intent_id
        db.commit()
        db.refresh(order)
        return order

    def mark_refunded(self, db: Session, order: Order) -> Order:
        """Mark an order as refunded (manual or Stripe webhook). Idempotent."""
        if order.status == OrderStatus.REFUNDED.value:
            return order
        order.status = OrderStatus.REFUNDED.value
        order.refunded_at = datetime.now(UTC)
        db.commit()
        db.refresh(order)
        return order

    async def capture_sale_event(self, db: Session, order_id: int) -> None:
        """
        Push a ``sale`` event to PostHog (best-effort) so it closes the funnel
        email → démo → vente. distinct_id = the prospect's demo slug (same identity
        as the email/demo events).
        """
        from services.posthog_service import posthog_service

        if not posthog_service.can_capture:
            return
        order = self.get_by_id(db, order_id)
        if not order:
            return

        slug: str | None = None
        if order.demo_site_id:
            from models.demo_site import DemoSite

            site = db.query(DemoSite).filter(DemoSite.id == order.demo_site_id).first()
            slug = site.slug if site else None
        distinct_id = slug or (f"prospect_{order.prospect_id}" if order.prospect_id else f"order_{order.id}")
        await posthog_service.capture(
            distinct_id=distinct_id,
            event="sale",
            properties={
                "amount_cents": order.amount_cents,
                "currency": order.currency,
                "product_type": order.product_type,
                "prospect_id": order.prospect_id,
                "demo_slug": slug,
                "order_id": order.id,
            },
        )

    def get_by_payment_intent_id(self, db: Session, payment_intent_id: str) -> Order | None:
        """Resolve an order from a Stripe payment intent id."""
        if not payment_intent_id:
            return None
        return (
            db.query(Order)
            .filter(Order.stripe_payment_intent_id == payment_intent_id, Order.deleted_at.is_(None))
            .first()
        )

    def try_mark_paid_from_event(self, db: Session, event: dict[str, Any]) -> int | None:
        """
        If a Stripe event is an order payment, mark the order paid and return its id.

        Returns None when the event is not an order payment (e.g. a credits purchase),
        so the caller can fall back to the credits handler.
        """
        if event.get("type") != "checkout.session.completed":
            return None
        session = event.get("data", {}).get("object", {})
        if session.get("payment_status") not in ("paid", "no_payment_required"):
            return None

        metadata = session.get("metadata", {}) or {}
        order: Order | None = None
        if metadata.get("type") == "order" and metadata.get("order_id"):
            order = self.get_by_id(db, int(metadata["order_id"]))
        if order is None:
            payment_link = session.get("payment_link")
            link_id = payment_link.get("id") if isinstance(payment_link, dict) else payment_link
            if link_id:
                order = self.get_by_payment_link_id(db, str(link_id))

        if order is None:
            return None

        payment_intent = session.get("payment_intent")
        intent_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
        self.mark_paid(
            db,
            order,
            stripe_session_id=session.get("id"),
            stripe_payment_intent_id=str(intent_id) if intent_id else None,
        )
        return order.id

    def try_handle_refund_from_event(self, db: Session, event: dict[str, Any]) -> int | None:
        """
        If a Stripe event is a refund, mark the matching order refunded.

        Handles ``charge.refunded`` and ``refund.created`` / ``refund.updated``.
        Returns the order id when handled, else None (so the caller can fall back).
        """
        event_type = event.get("type", "")
        if event_type not in ("charge.refunded", "refund.created", "refund.updated"):
            return None

        obj = event.get("data", {}).get("object", {})
        # charge.refunded → object is a Charge (has payment_intent + refunded flag)
        # refund.* → object is a Refund (has payment_intent + status)
        payment_intent = obj.get("payment_intent")
        intent_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
        if not intent_id:
            return None

        if event_type.startswith("refund.") and obj.get("status") not in ("succeeded", None):
            return None

        order = self.get_by_payment_intent_id(db, str(intent_id))
        if order is None:
            return None

        self.mark_refunded(db, order)
        return order.id

    async def _verify_delivery(self, order: Order, demo_site: DemoSite) -> tuple[bool, str]:
        """
        Verify the client truly has a working site on their domain AND CMS access.

        Returns ``(ok, message)``. ``ok`` is True only when the custom domain
        serves a page (HTTP < 400) and the Storyblok CMS handover is real — a
        space exists and the invite was sent (not mock mode).

        Args:
            order: The paid order being fulfilled (provides the domain).
            demo_site: The linked demo site (provides CMS state).

        Returns:
            Tuple of (delivered_ok, human-readable reason).
        """
        from services.demo_site_verification_service import demo_site_verification_service

        problems: list[str] = []

        if not order.domain:
            domain_live = False
            problems.append("aucun domaine défini")
        else:
            domain_live = await demo_site_verification_service.check_domain_live(order.domain)
            if not domain_live:
                problems.append(f"le domaine {order.domain} ne répond pas encore (DNS/Vercel)")

        cms_ready: bool = bool(demo_site.storyblok_space_id) and bool(demo_site.storyblok_invite_sent)
        if not cms_ready:
            if not demo_site.storyblok_space_id:
                problems.append("espace CMS Storyblok non créé (mode mock ?)")
            else:
                problems.append("invitation CMS non envoyée au client")

        if domain_live and cms_ready:
            return True, "Site en ligne sur le domaine client et accès CMS transmis."
        return False, "Livraison incomplète : " + " ; ".join(problems)

    async def fulfill_order_async(self, order_id: int) -> None:
        """
        One tracked fulfilment attempt in its own DB session (safe for background tasks):
        deploy the site to prod (Vercel + domain) and hand over CMS access.

        Increments ``fulfillment_attempts`` and records ``fulfillment_last_error`` so a
        paid-but-undelivered order is retried by the recovery loop (bounded) instead of
        silently stuck. Terminal orders (delivered/refunded/cancelled) are skipped.
        """
        from core.database import SessionLocal

        db = SessionLocal()
        try:
            order = self.get_by_id(db, order_id)
            if not order or order.product_type != ProductType.WEBSITE.value:
                return
            if order.status in _TERMINAL_STATUSES:
                return

            order.fulfillment_attempts = (order.fulfillment_attempts or 0) + 1
            order.fulfillment_last_error = None
            db.commit()

            try:
                await self.fulfill_order(db, order)
            except Exception as exc:
                logger.exception("Order fulfilment attempt failed for order_id=%s", order_id)
                order = self.get_by_id(db, order_id)
                if order is not None:
                    order.fulfillment_last_error = str(exc)[:500]
                    db.commit()
        finally:
            db.close()

    def list_stuck_fulfilment_order_ids(self, db: Session) -> list[int]:
        """
        Ids of website orders that were paid but never fully delivered and are still
        within the auto-retry budget (attempts + age). Consumed by the recovery loop.

        Args:
            db: Database session.

        Returns:
            The order ids to retry.
        """
        cutoff: datetime = datetime.now(UTC) - timedelta(days=FULFILMENT_MAX_AGE_DAYS)
        rows = (
            db.query(Order.id)
            .filter(
                Order.product_type == ProductType.WEBSITE.value,
                Order.status.in_(_RETRYABLE_STATUSES),
                Order.deleted_at.is_(None),
                Order.fulfillment_attempts < MAX_FULFILMENT_ATTEMPTS,
                Order.created_at >= cutoff,
            )
            .all()
        )
        return [row[0] for row in rows]

    async def fulfill_order(self, db: Session, order: Order) -> Order:
        """Deploy the linked demo site to prod and hand over Storyblok access."""
        from models.demo_site import DemoSite
        from services.demo_site_service import demo_site_service

        if not order.demo_site_id:
            logger.info("Order %s has no linked demo site — skipping deploy", order.id)
            return order

        demo_site = (
            db.query(DemoSite).filter(DemoSite.id == order.demo_site_id, DemoSite.user_id == order.user_id).first()
        )
        if not demo_site:
            return order

        order.status = OrderStatus.DEPLOYING.value
        db.commit()

        # 1) Deploy to production (Vercel + domain) — best effort.
        try:
            from services.vercel_service import vercel_service

            await vercel_service.deploy_demo_site(db, demo_site, domain=order.domain)
        except Exception:
            logger.exception("Vercel deployment failed for order_id=%s", order.id)

        # 2) Take the demo offline (demo.dibodev.fr 404) and promote the site to
        #    the client's production domain (served via host→slug, permanent).
        if order.domain:
            try:
                await demo_site_service.mark_delivered(db, demo_site, order.domain)
            except Exception:
                logger.warning("mark_delivered failed for order_id=%s", order.id, exc_info=True)

        # 3) Hand over CMS access (Storyblok invite) now that the sale is closed.
        try:
            if not demo_site.storyblok_invite_sent:
                await demo_site_service.invite_client_to_cms(db, demo_site)
        except Exception:
            logger.warning("Storyblok handover failed for order_id=%s", order.id, exc_info=True)

        db.refresh(demo_site)

        # 4) Only declare the order delivered once the client truly has a working
        #    site on their domain AND real CMS access. Otherwise keep it DEPLOYING
        #    with a reason — the operator fixes DNS/CMS and re-runs
        #    POST /orders/{id}/deploy to re-verify.
        delivered_ok, message = await self._verify_delivery(order, demo_site)
        demo_site.verification_message = message
        if delivered_ok:
            order.status = OrderStatus.DELIVERED.value
            order.delivered_at = datetime.now(UTC)
        else:
            order.status = OrderStatus.DEPLOYING.value
            logger.warning("Order %s kept in DEPLOYING — %s", order.id, message)
        db.commit()
        db.refresh(order)
        return order

    # ------------------------------------------------------------------ #
    # Commercial tracking
    # ------------------------------------------------------------------ #

    def stats_for_user(self, db: Session, user_id: int, since: datetime | None = None) -> dict[str, Any]:
        """Aggregate sales KPIs for a user (counts + revenue).

        Args:
            db: Database session.
            user_id: Owner of the orders.
            since: When set, only count orders created after this moment
                (drives the dashboard period filter).
        """
        orders = self.list_for_user(db, user_id)
        if since is not None:
            orders = [o for o in orders if o.created_at is not None and o.created_at >= since]
        won = [o for o in orders if o.status in WON_STATUSES]
        revenue_cents = sum(o.amount_cents for o in won)
        pending = [o for o in orders if o.status == OrderStatus.PAYMENT_PENDING.value]
        pipeline_cents = sum(o.amount_cents for o in pending)
        return {
            "total_orders": len(orders),
            "won_count": len(won),
            "pending_count": len(pending),
            "revenue_cents": revenue_cents,
            "pipeline_cents": pipeline_cents,
            "currency": "eur",
        }


order_service = OrderService()
