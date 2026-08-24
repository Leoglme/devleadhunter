"""Turn a raw provider bounce/failure reason into a French, human explanation."""

from __future__ import annotations

from dataclasses import dataclass

from enums.email_status import EmailStatus

# Statuses that mean the email never reached the recipient — the only ones we explain.
_FAILURE_STATUSES: frozenset[str] = frozenset(
    {
        EmailStatus.BOUNCED.value,
        EmailStatus.FAILED.value,
        EmailStatus.COMPLAINED.value,
        EmailStatus.SUPPRESSED.value,
    }
)


@dataclass(frozen=True)
class EmailFailureExplanation:
    """A classified send failure, ready to show to the operator.

    Attributes:
        category: Stable machine slug (e.g. ``invalid_recipient``) for the UI to branch on.
        reason: One-sentence French explanation of why the email did not go out.
        is_expected: True when nothing is wrong on our side (bad address, spam complaint…) — the
            operator only needs the right address; False when it warrants attention (blocked, send
            error); None when the raw reason is unknown.
    """

    category: str
    reason: str
    is_expected: bool | None


class EmailFailureExplainer:
    """Classify a send failure from its status and raw provider message into French."""

    _INVALID_RECIPIENT_HINTS: tuple[str, ...] = (
        "does not exist",
        "doesn't exist",
        "recipient not found",
        "no such user",
        "user unknown",
        "unknown user",
        "mailbox unavailable",
        "mailbox not found",
        "no mailbox",
        "invalid recipient",
        "address rejected",
        "recipient address rejected",
        "550 5.1.1",
    )
    _MAILBOX_FULL_HINTS: tuple[str, ...] = (
        "mailbox full",
        "over quota",
        "quota exceeded",
        "insufficient storage",
        "552",
    )
    _BLOCKED_HINTS: tuple[str, ...] = (
        "blocked",
        "blacklist",
        "reputation",
        "policy",
        "spam content",
        "rejected due to",
    )

    @classmethod
    def explain(cls, status: str, error_message: str | None) -> EmailFailureExplanation | None:
        """
        Return a French explanation for a failed send, or None when the email did not fail.

        Args:
            status: The EmailLog status value (e.g. ``bounced``, ``failed``).
            error_message: The raw provider reason stored on the log, if any.

        Returns:
            An :class:`EmailFailureExplanation`, or None when ``status`` is not a failure.
        """
        if status not in _FAILURE_STATUSES:
            return None

        if status == EmailStatus.COMPLAINED.value:
            return EmailFailureExplanation(
                "spam_complaint",
                "Le destinataire a marqué l'e-mail comme spam. L'adresse est à ne plus recontacter.",
                True,
            )
        if status == EmailStatus.SUPPRESSED.value:
            return EmailFailureExplanation(
                "suppressed",
                "Adresse désinscrite ou sur liste de suppression : l'envoi a été bloqué volontairement.",
                True,
            )

        haystack: str = (error_message or "").lower()
        if any(hint in haystack for hint in cls._INVALID_RECIPIENT_HINTS):
            return EmailFailureExplanation(
                "invalid_recipient",
                "L'adresse e-mail n'existe pas (faute de frappe, compte fermé ou domaine invalide). "
                "Ce n'est pas un problème d'envoi de notre côté : il faut la bonne adresse.",
                True,
            )
        if any(hint in haystack for hint in cls._MAILBOX_FULL_HINTS):
            return EmailFailureExplanation(
                "mailbox_full",
                "La boîte du destinataire est pleine. Problème temporaire côté destinataire.",
                True,
            )
        if any(hint in haystack for hint in cls._BLOCKED_HINTS):
            return EmailFailureExplanation(
                "blocked",
                "L'e-mail a été bloqué par le serveur du destinataire (réputation ou contenu). À surveiller.",
                False,
            )

        if status == EmailStatus.FAILED.value:
            return EmailFailureExplanation(
                "sending_error",
                "L'envoi a échoué côté service d'e-mail. À vérifier (configuration ou contenu du message).",
                False,
            )

        # A bounce with no matched reason: undeliverable, most often a bad address, but we don't assert why.
        return EmailFailureExplanation(
            "undeliverable",
            "L'e-mail n'a pas pu être délivré au destinataire."
            + (f" Détail : {error_message.strip()}" if error_message and error_message.strip() else ""),
            None,
        )


email_failure_explainer = EmailFailureExplainer()
