"""Orchestrates a user's connected encashment provider (Qonto / Stripe).

Owns the stateful side the provider clients deliberately stay out of: the OAuth
handshake and token lifecycle for Qonto, the Account-Links onboarding for
Stripe, and the connect/disconnect bookkeeping on :class:`PaymentAccount`.

Qonto is admin-only at the route layer; this service stays provider-symmetric.
The one subtlety it must get right is Qonto's rotating refresh token: every
refresh invalidates the old refresh token and returns a new one, so
:meth:`get_valid_qonto_access_token` re-persists both halves on every refresh.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.config import settings
from enums.payment_provider import PaymentEnvironment, PaymentProvider
from models.payment_account import PaymentAccount
from models.user import User
from schemas.payment_account import PaymentAccountStatus
from services.encryption_service import encryption_service
from services.qonto_oauth_service import QontoOAuthService

logger = logging.getLogger(__name__)

# Refresh a Qonto access token slightly before it actually expires.
_TOKEN_REFRESH_BUFFER = timedelta(seconds=60)


class PaymentAccountService:
    """Connect, disconnect and keep fresh a user's encashment provider."""

    def get_for_user(self, db: Session, user_id: int) -> PaymentAccount | None:
        """
        Return the user's payment account, or ``None`` when none is connected.

        Args:
            db: Active database session.
            user_id: Owner of the account.

        Returns:
            The user's :class:`PaymentAccount`, or ``None``.
        """
        return db.query(PaymentAccount).filter(PaymentAccount.user_id == user_id).first()

    def build_status(self, db: Session, user: User) -> PaymentAccountStatus:
        """
        Build the settings-page status for a user.

        Args:
            db: Active database session.
            user: The current user (its role gates Qonto availability).

        Returns:
            A secret-free :class:`PaymentAccountStatus`.
        """
        from enums.user_role import UserRole

        qonto_available = user.role == UserRole.ADMIN.value
        account = self.get_for_user(db, user.id)
        if account is None:
            return PaymentAccountStatus(qonto_available=qonto_available)
        return PaymentAccountStatus(
            connected_provider=account.provider if account.is_connected else None,
            is_connected=account.is_connected,
            environment=account.environment,
            display_name=account.display_name,
            qonto_available=qonto_available,
            qonto_iban=account.qonto_iban,
            has_qonto_api_key=bool(account.qonto_api_login and account.qonto_api_secret),
            stripe_charges_enabled=account.stripe_charges_enabled,
            stripe_details_submitted=account.stripe_details_submitted,
        )

    # ------------------------------------------------------------------ #
    # Row lifecycle
    # ------------------------------------------------------------------ #

    def _get_or_create_row(self, db: Session, user_id: int, provider: PaymentProvider) -> PaymentAccount:
        """
        Return the user's single account row, creating/retargeting it to ``provider``.

        Switching provider clears the other provider's stored credentials so a
        stale token can never be picked up for the wrong provider.

        Args:
            db: Active database session.
            user_id: Owner of the account.
            provider: Provider being connected.

        Returns:
            The account row, set to ``provider`` (not yet committed).
        """
        account = self.get_for_user(db, user_id)
        if account is None:
            account = PaymentAccount(user_id=user_id, provider=provider.value)
            db.add(account)
        elif account.provider != provider.value:
            self._clear_credentials(account)
            account.provider = provider.value
            account.is_connected = False
        return account

    def _clear_credentials(self, account: PaymentAccount) -> None:
        """
        Wipe every provider credential on an account (on switch/disconnect).

        Args:
            account: The account to clear (not committed here).
        """
        account.qonto_access_token = None
        account.qonto_refresh_token = None
        account.qonto_token_expires_at = None
        account.qonto_api_login = None
        account.qonto_api_secret = None
        account.qonto_iban = None
        account.stripe_account_id = None
        account.stripe_charges_enabled = False
        account.stripe_details_submitted = False
        account.display_name = None

    def disconnect(self, db: Session, user_id: int) -> None:
        """
        Disconnect and forget the user's encashment provider.

        Args:
            db: Active database session.
            user_id: Owner of the account.
        """
        account = self.get_for_user(db, user_id)
        if account is not None:
            db.delete(account)
            db.commit()

    # ------------------------------------------------------------------ #
    # Qonto (OAuth) — admin only at the route layer
    # ------------------------------------------------------------------ #

    def qonto_authorize_url(self, user_id: int) -> str:
        """
        Build the Qonto authorization URL for a user.

        Args:
            user_id: Owner initiating the connection (echoed back as state).

        Returns:
            The authorization URL to redirect the browser to.
        """
        return QontoOAuthService().get_authorization_url(state=f"user_{user_id}")

    async def complete_qonto_oauth(self, db: Session, user_id: int, code: str) -> PaymentAccount:
        """
        Finish the Qonto OAuth flow: exchange the code and store the tokens.

        Args:
            db: Active database session.
            user_id: Owner resolved from the callback state.
            code: Authorization code from the callback.

        Returns:
            The connected Qonto account.
        """
        tokens = await QontoOAuthService().exchange_code_for_tokens(code)
        account = self._get_or_create_row(db, user_id, PaymentProvider.QONTO)
        account.environment = settings.qonto_environment
        account.qonto_access_token = encryption_service.encrypt(tokens["access_token"])
        account.qonto_refresh_token = encryption_service.encrypt(tokens.get("refresh_token", ""))
        account.qonto_token_expires_at = tokens["expires_at"]
        account.is_connected = True
        db.commit()
        db.refresh(account)
        return account

    async def get_valid_qonto_access_token(self, db: Session, account: PaymentAccount) -> str:
        """
        Return a usable Qonto access token, refreshing (and rotating) if needed.

        Qonto refresh tokens are one-time use: a refresh returns a *new* refresh
        token that replaces the stored one, so both halves are re-persisted.

        Args:
            db: Active database session.
            account: The connected Qonto account.

        Returns:
            A valid (decrypted) access token.

        Raises:
            ValueError: When the account has no stored Qonto tokens.
        """
        if not account.qonto_access_token or not account.qonto_refresh_token:
            raise ValueError("Qonto account is not connected (no tokens stored).")

        expires_at = account.qonto_token_expires_at
        if expires_at is not None and expires_at - _TOKEN_REFRESH_BUFFER > datetime.utcnow():
            return encryption_service.decrypt(account.qonto_access_token)

        refresh_token = encryption_service.decrypt(account.qonto_refresh_token)
        tokens = await QontoOAuthService().refresh_access_token(refresh_token)
        account.qonto_access_token = encryption_service.encrypt(tokens["access_token"])
        account.qonto_refresh_token = encryption_service.encrypt(tokens["refresh_token"])
        account.qonto_token_expires_at = tokens["expires_at"]
        db.commit()
        return tokens["access_token"]

    def set_qonto_api_key(self, db: Session, user_id: int, login: str, secret: str) -> PaymentAccount:
        """
        Store the admin-only Qonto API-key fallback (encrypted).

        Args:
            db: Active database session.
            user_id: Owner of the account.
            login: Qonto API-key login.
            secret: Qonto API-key secret.

        Returns:
            The updated account.
        """
        account = self._get_or_create_row(db, user_id, PaymentProvider.QONTO)
        account.environment = settings.qonto_environment
        account.qonto_api_login = encryption_service.encrypt(login)
        account.qonto_api_secret = encryption_service.encrypt(secret)
        account.is_connected = True
        db.commit()
        db.refresh(account)
        return account

    def set_qonto_iban(self, db: Session, user_id: int, iban: str) -> PaymentAccount:
        """
        Store the IBAN printed on Qonto invoices (captured manually).

        Args:
            db: Active database session.
            user_id: Owner of the account.
            iban: The IBAN as entered.

        Returns:
            The updated account.

        Raises:
            ValueError: When no Qonto account is connected yet.
        """
        account = self.get_for_user(db, user_id)
        if account is None or account.provider != PaymentProvider.QONTO.value:
            raise ValueError("Connect Qonto before setting its IBAN.")
        account.qonto_iban = iban.replace(" ", "")
        db.commit()
        db.refresh(account)
        return account

    # ------------------------------------------------------------------ #
    # Stripe (Connect Standard, Account Links onboarding)
    # ------------------------------------------------------------------ #

    def start_stripe_onboarding(self, db: Session, user_id: int, return_url: str, refresh_url: str) -> str:
        """
        Create/resume a Stripe Connect Standard account and return its onboarding URL.

        Args:
            db: Active database session.
            user_id: Owner of the account.
            return_url: Where Stripe sends the user once onboarding is done.
            refresh_url: Where Stripe sends the user if the link expires.

        Returns:
            The hosted onboarding URL to redirect the browser to.
        """
        import stripe

        stripe.api_key = settings.stripe_secret_key
        account = self._get_or_create_row(db, user_id, PaymentProvider.STRIPE)
        if not account.stripe_account_id:
            connected = stripe.Account.create(type="standard")
            account.stripe_account_id = connected.id
            account.environment = self._stripe_environment()
            db.commit()
        link = stripe.AccountLink.create(
            account=account.stripe_account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return link.url

    def refresh_stripe_status(self, db: Session, account: PaymentAccount) -> PaymentAccount:
        """
        Re-read the connected Stripe account and update its capability flags.

        Args:
            db: Active database session.
            account: The user's Stripe account.

        Returns:
            The updated account.
        """
        import stripe

        stripe.api_key = settings.stripe_secret_key
        connected = stripe.Account.retrieve(account.stripe_account_id)
        account.stripe_charges_enabled = bool(connected.charges_enabled)
        account.stripe_details_submitted = bool(connected.details_submitted)
        account.is_connected = account.stripe_charges_enabled
        db.commit()
        db.refresh(account)
        return account

    def _stripe_environment(self) -> str:
        """
        Derive the environment tag from the platform Stripe key.

        Returns:
            ``sandbox`` for a test key, ``production`` otherwise.
        """
        if settings.stripe_secret_key.startswith("sk_test"):
            return PaymentEnvironment.SANDBOX.value
        return PaymentEnvironment.PRODUCTION.value


payment_account_service = PaymentAccountService()
