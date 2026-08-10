"""Background auto-detection of paid orders.

The Stripe invoice flow emits no webhook we handle and Qonto none at all, so a paid
sale would sit at "payment pending" until someone clicks "Vérifier le paiement". This
loop reconciles pending orders against their provider and, for each one that just went
paid, captures the sale event and kicks off fulfilment — the same follow-up the webhook
runs for the legacy checkout flow.
"""

from __future__ import annotations

import asyncio
import logging

from core.database import SessionLocal
from services.order_service import order_service

logger = logging.getLogger(__name__)


async def run_order_payment_reconciliation_loop(interval_seconds: int = 300) -> None:
    """
    Periodically mark paid the pending orders whose provider reports the invoice paid.

    Args:
        interval_seconds: Delay between reconciliation passes (default 5 min).
    """
    while True:
        db = SessionLocal()
        newly_paid: list[int] = []
        try:
            newly_paid = await order_service.reconcile_pending_orders(db)
            for order_id in newly_paid:
                try:
                    await order_service.capture_sale_event(db, order_id)
                except Exception as exc:
                    logger.exception("Sale event capture failed for order %s: %s", order_id, exc)
        except Exception as exc:
            logger.exception("Payment reconciliation pass failed: %s", exc)
        finally:
            db.close()

        for order_id in newly_paid:
            try:
                await order_service.fulfill_order_async(order_id)
            except Exception as exc:
                logger.exception("Fulfilment after reconciliation failed for order %s: %s", order_id, exc)

        if newly_paid:
            logger.info("Payment reconciliation marked %s order(s) paid", len(newly_paid))

        await asyncio.sleep(interval_seconds)
