"""Background worker for the opt-in SMS automations (auto-relance + cold SMS).

Off by default: a user turns each automation on in Paramètres → Relance SMS. On each
pass, for every user who enabled one, it sends a throttled batch — always inside the
legal window, capped per pass and per day (warm-up), never texting a prospect twice.
Relance (emailed, no reaction) is preferred; cold (mobile, no email) fills the rest.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from services.sms.smsmode_provider import smsmode_provider
from services.sms_relance_service import SmsRelanceCandidate, sms_relance_service
from services.sms_service import sms_service

logger = logging.getLogger(__name__)


class SmsAutomationService:
    """Send the opt-in automated SMS (auto-relance + cold), throttled and legal."""

    def enabled_configs(self, db: Session) -> list[SmsConfig]:
        """Configs of users who enabled any SMS automation (with a sender, provider ready)."""
        if not smsmode_provider.is_configured:
            return []
        return (
            db.query(SmsConfig)
            .filter(
                SmsConfig.sender != "",
                or_(SmsConfig.auto_relance_enabled.is_(True), SmsConfig.cold_sms_enabled.is_(True)),
            )
            .all()
        )

    def _sent_today(self, db: Session, user_id: int) -> int:
        """Number of SMS (any source) the user sent since midnight UTC — the daily-cap base."""
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return int(
            db.query(func.count(SmsMessage.id))
            .filter(SmsMessage.user_id == user_id, SmsMessage.created_at >= day_start)
            .scalar()
            or 0
        )

    def _gather(self, db: Session, config: SmsConfig, budget: int) -> list[SmsRelanceCandidate]:
        """Collect up to *budget* candidates for a user: relance first, then cold to fill."""
        candidates: list[SmsRelanceCandidate] = []
        if config.auto_relance_enabled:
            candidates += sms_relance_service.find_candidates(
                db, config.user_id, after_days=config.auto_relance_after_days, limit=budget
            )
        if config.cold_sms_enabled and len(candidates) < budget:
            candidates += sms_relance_service.find_cold_candidates(db, config.user_id, limit=budget - len(candidates))
        return candidates[:budget]

    async def run_pass(self, db: Session) -> int:
        """Send one throttled batch of automated SMS across all opted-in users.

        Args:
            db: Active database session.

        Returns:
            The number of SMS sent in this pass.
        """
        # Outside the legal window nothing goes out — wait silently for the next window.
        if sms_service.legal_window_refusal() is not None:
            return 0

        total_sent = 0
        for config in self.enabled_configs(db):
            budget = min(
                settings.sms_auto_per_run, max(0, settings.sms_auto_daily_cap - self._sent_today(db, config.user_id))
            )
            if budget <= 0:
                continue
            for candidate in self._gather(db, config, budget):
                try:
                    if await sms_relance_service.send_relance(db, config.user_id, candidate):
                        total_sent += 1
                except Exception as exc:
                    logger.warning("Auto-SMS failed for prospect %s: %s", candidate.prospect.id, exc)
        return total_sent

    async def run_loop(self, interval_seconds: int = 1800) -> None:
        """Run an automated-SMS pass on a periodic loop (legal window + caps enforced per pass)."""
        while True:
            db = SessionLocal()
            try:
                sent = await self.run_pass(db)
                if sent:
                    logger.info("Auto-SMS pass sent %s message(s)", sent)
            except Exception as exc:
                logger.exception("Auto-SMS pass failed: %s", exc)
            finally:
                db.close()
            await asyncio.sleep(interval_seconds)


sms_automation_service = SmsAutomationService()


async def run_sms_automation_loop(interval_seconds: int = 1800) -> None:
    """Entrypoint used by the API lifespan to run the auto-SMS loop."""
    await sms_automation_service.run_loop(interval_seconds)
