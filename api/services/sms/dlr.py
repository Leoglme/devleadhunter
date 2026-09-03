"""Parsing of smsmode delivery-receipt (DLR) callbacks.

The smsmode REST v1 DLR ``status`` is one of ``ENROUTE`` / ``DELIVERED`` /
``UNDELIVERABLE`` / ``UNDELIVERED`` / ``UNKNOWN``. We also accept the legacy CR
synonyms and numeric status codes so a final status is never silently dropped —
``UNDELIVERABLE`` (the « NON LIVRABLE / spam » case) must map to a failure.

All helpers are pure and tolerate camelCase / snake_case and a ``status`` that is
a nested object, a plain string, or a numeric code.
"""

from __future__ import annotations

from typing import Any

from enums.sms_status import SmsStatus

# REST v1 DLR status strings that mean the handset received the SMS.
_DELIVERED: frozenset[str] = frozenset({"DELIVERED", "DELIVRED", "RECEIVED"})
# Terminal failure strings (UNDELIVERABLE = operator refused it, e.g. anti-spam).
_FAILED: frozenset[str] = frozenset(
    {"UNDELIVERABLE", "UNDELIVERED", "UNDELIVRED", "FAILED", "ERROR", "EXPIRED", "REJECTED"}
)
# Numeric smsmode codes (legacy CR / HTTP API) → terminal outcome.
_CODE_DELIVERED: frozenset[str] = frozenset({"11", "14"})
_CODE_FAILED: frozenset[str] = frozenset({"37", "3521", "3522", "3523", "3524", "3525", "3560", "3999"})

# Numeric code → human reason, so a failed SMS shows *why* it failed.
_CODE_LABELS: dict[str, str] = {
    "3524": "Spam (filtre anti-spam opérateur)",
    "3525": "Contenu refusé",
    "3560": "Numéro non routable",
    "3521": "Numéro non attribué",
    "3522": "Numéro non attribué",
    "3523": "Numéro non attribué",
    "3999": "Numéro blacklisté",
    "37": "Message expiré",
}


def dlr_message_id(payload: dict[str, Any]) -> str:
    """Provider message id, tolerating camelCase / snake_case field names."""
    for key in ("messageId", "message_id", "id"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def dlr_ref_client(payload: dict[str, Any]) -> str:
    """Client reference echoed back (``dlh-<id>``), used as a fallback match."""
    for key in ("refClient", "ref_client", "reference"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def dlr_status_value(payload: dict[str, Any]) -> str:
    """Raw status token, whether ``status`` is a dict, a string, or a numeric code."""
    raw = payload.get("status")
    if isinstance(raw, dict):
        return str(raw.get("value") or raw.get("code") or "").strip()
    if raw is not None:
        return str(raw).strip()
    return str(payload.get("statusCode") or "").strip()


def dlr_status_detail(payload: dict[str, Any]) -> str | None:
    """Human reason for the status (a smsmode label, or a mapped numeric code)."""
    raw = payload.get("status")
    detail = ""
    if isinstance(raw, dict):
        detail = str(raw.get("detail") or raw.get("label") or "").strip()
    detail = detail or str(payload.get("statusDetail") or payload.get("detail") or "").strip()
    if detail:
        return detail[:255]
    return _CODE_LABELS.get(dlr_status_value(payload))


def classify_dlr(status_value: str) -> str | None:
    """Map a smsmode DLR status to our lifecycle status.

    Args:
        status_value: The raw DLR status token.

    Returns:
        ``delivered`` / ``failed``, or ``None`` when the SMS is still in transit
        (``ENROUTE`` / ``UNKNOWN`` / unrecognised) so the row is left unchanged.
    """
    normalized = (status_value or "").strip().upper()
    if normalized in _DELIVERED or normalized in _CODE_DELIVERED:
        return SmsStatus.DELIVERED.value
    if normalized in _FAILED or normalized in _CODE_FAILED:
        return SmsStatus.FAILED.value
    return None
