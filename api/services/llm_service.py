"""
LLM helper backed by Groq (OpenAI-compatible API).

Used for the behaviour summary shown in the prospect drawer and for the
behaviour-based personalised follow-up. Every method degrades gracefully to a
rule-based output when ``GROQ_API_KEY`` is not configured, so the product works
without the LLM and lights up automatically once a key is provided.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _format_sender_identity(*, sender_name: str, company_name: str | None) -> str:
    """Build the « Name (Company) » label injected into outreach prompts."""
    name = (sender_name or "").strip() or "le commercial"
    company = (company_name or "").strip()
    return f"{name} ({company})" if company else name


class LLMService:
    """Thin Groq client with rule-based fallbacks."""

    @property
    def is_configured(self) -> bool:
        """True when a Groq API key is available."""
        return bool(settings.groq_api_key)

    async def _chat(
        self, messages: list[dict[str, str]], *, max_tokens: int = 600, temperature: float = 0.6
    ) -> str | None:
        """Call Groq chat completions. Returns the text, or None on failure."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                response = await client.post(
                    _GROQ_URL,
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json={
                        "model": settings.groq_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("Groq call failed: %s", exc)
            return None

    async def classify_reply_intent(self, reply_text: str) -> str | None:
        """
        Classify what a prospect's reply means, in one deterministic word.

        Called at most once per reply (the verdict is persisted by the caller);
        ``temperature=0`` so the same content always yields the same verdict.

        Args:
            reply_text: The reply as plain text (already stripped of HTML).

        Returns:
            The raw model output (single word expected), or ``None`` when Groq is
            not configured or the call failed. Validation happens in the caller.
        """
        excerpt = reply_text.strip()[:1500]
        if not excerpt:
            return None
        prompt = (
            "Tu classes la réponse d'un prospect (artisan/commerçant français) à un email de "
            "prospection pour la création d'un site web. Réponds par UN SEUL mot, exactement "
            "parmi : interested, not_interested, later, question, unsubscribe, other.\n"
            "- interested : intérêt clair (oui, rdv, rappelez-moi, envoyez le devis…)\n"
            "- not_interested : refus (pas intéressé, j'ai déjà un site, non merci…)\n"
            "- later : pas maintenant mais ouvert (recontactez-moi en septembre, trop tôt…)\n"
            "- question : demande d'information (prix, délais, comment ça marche…)\n"
            "- unsubscribe : demande explicite d'arrêter les emails\n"
            "- other : tout le reste (hors sujet, illisible…)\n\n"
            f"Réponse du prospect :\n« {excerpt} »"
        )
        return await self._chat([{"role": "user", "content": prompt}], max_tokens=10, temperature=0.0)

    async def summarize_behavior(
        self,
        *,
        sender_name: str,
        company_name: str | None,
        business_name: str,
        temperature: str,
        signals: dict[str, Any],
    ) -> str:
        """Produce a short behavioural read + relance advice for a prospect."""
        sender = _format_sender_identity(sender_name=sender_name, company_name=company_name)
        prompt = (
            f"Tu es l'assistant commercial de {sender}, qui vend des sites web aux artisans. "
            "Voici le comportement d'un prospect : son activité sur la démo de site ET son engagement "
            "email (emails_sent/opened/clicked).\n"
            f"Entreprise : {business_name}\n"
            f"Température : {temperature}\n"
            f"Signaux (démo + email) : {signals}\n\n"
            "En 3-4 phrases max, en français, interprète ce comportement (démo + email) et conseille "
            "concrètement comment relancer ce prospect (angle, ton, urgence). Sois direct, pas de blabla."
        )
        result = await self._chat([{"role": "user", "content": prompt}], max_tokens=300)
        return result or self._fallback_summary(temperature, signals)

    async def draft_followup(
        self,
        *,
        sender_name: str,
        company_name: str | None,
        business_name: str,
        first_name: str,
        temperature: str,
        signals: dict[str, Any],
        base_subject: str,
        base_body_html: str,
    ) -> dict[str, str]:
        """Draft a behaviour-personalised follow-up, falling back to the base template."""
        sender = _format_sender_identity(sender_name=sender_name, company_name=company_name)
        prompt = (
            f"Tu écris un email de relance B2B court et naturel (français), de la part de {sender} "
            "qui a envoyé une démo de site web à un artisan.\n"
            f"Prénom du contact : {first_name or 'le contact'}\n"
            f"Entreprise : {business_name}\n"
            f"Température du lead : {temperature}\n"
            f"Comportement (démo + engagement email) : {signals}\n\n"
            "Relance existante (à personnaliser, garde l'esprit) :\n"
            f"Objet: {base_subject}\n{base_body_html}\n\n"
            "Réécris une relance personnalisée selon ce qu'il a regardé/cliqué sur la démo. "
            "Réponds STRICTEMENT au format:\n"
            "SUBJECT: <objet>\nBODY: <corps en HTML simple>"
        )
        result = await self._chat([{"role": "user", "content": prompt}], max_tokens=700)
        if not result:
            return {"subject": base_subject, "body_html": base_body_html}
        return self._parse_subject_body(result, base_subject, base_body_html)

    async def suggest_domain_names(self, *, business_name: str, city: str | None, category: str | None) -> list[str]:
        """Propose a few short, brandable domain labels for a business (no extension).

        Enriches the code-logic candidates when the exact business name is taken or ugly.
        Returns bare labels (no ``.fr``, no accents), lowercase — the caller validates and
        appends ``.fr``. Degrades to ``[]`` when Groq is off or the call fails, so the
        suggestion still works on the rule-based candidates alone.

        Args:
            business_name: The prospect's business name.
            city: The prospect's city, when known (helps disambiguate).
            category: The prospect's trade, when known (e.g. « restaurant »).

        Returns:
            Up to five candidate labels, or ``[]``.
        """
        name = (business_name or "").strip()
        if not name:
            return []
        context = f"Entreprise : {name}"
        if city:
            context += f"\nVille : {city}"
        if category:
            context += f"\nMétier : {category}"
        prompt = (
            "Propose 4 idées de nom de domaine pour le site de cette entreprise artisanale/commerçante "
            "française. Contraintes STRICTES : court, mémorable, SANS accent, SANS espace, uniquement "
            "lettres minuscules / chiffres / tirets, PAS d'extension (pas de .fr). Reste proche du nom de "
            "l'entreprise, évite le générique. Réponds UNIQUEMENT par les 4 labels, un par ligne, rien d'autre.\n\n"
            f"{context}"
        )
        result = await self._chat([{"role": "user", "content": prompt}], max_tokens=80, temperature=0.7)
        if not result:
            return []
        labels: list[str] = []
        for line in result.splitlines():
            cleaned = line.strip().strip("-•*0123456789. ").lower()
            if cleaned:
                labels.append(cleaned)
        return labels[:5]

    # ── Fallbacks / parsing ────────────────────────────────────────────────

    @staticmethod
    def _fallback_summary(temperature: str, signals: dict[str, Any]) -> str:
        """Rule-based summary when no LLM is available."""
        if temperature == "unknown":
            return "Aucune visite détectée sur la démo pour l'instant. Relancer sur l'intérêt d'avoir un site."
        bits: list[str] = []
        if signals.get("phone_clicks"):
            bits.append("a cliqué sur le téléphone (intérêt fort)")
        if signals.get("contact_clicks"):
            bits.append("a cliqué sur le contact")
        if signals.get("cta_clicks"):
            bits.append("a cliqué sur un bouton d'action")
        if signals.get("visits", 0) > 1:
            bits.append(f"est revenu {signals['visits']} fois sur la démo")
        if signals.get("total_seconds", 0) >= 60:
            bits.append("a passé du temps sur la page")
        if signals.get("video_completes"):
            bits.append("a regardé la vidéo en entier")
        elif signals.get("video_max_progress", 0) >= 50:
            bits.append(f"a regardé {signals['video_max_progress']}% de la vidéo")
        elif signals.get("video_plays"):
            bits.append("a lancé la vidéo")
        if signals.get("video_replays"):
            bits.append(f"a revu la vidéo {signals['video_replays']}x")
        if signals.get("video_fullscreen"):
            bits.append("a mis la vidéo en plein écran")
        if signals.get("emails_clicked"):
            bits.append("a cliqué le lien dans l'email")
        elif signals.get("emails_opened"):
            bits.append(f"a ouvert l'email ({signals['emails_opened']}x)")
        detail = ", ".join(bits) if bits else "a consulté la démo brièvement"
        advice = {
            "hot": "Lead chaud — relancer vite, proposer un appel ou finaliser la vente.",
            "warm": "Lead tiède — relancer en mettant en avant le bénéfice concret du site.",
            "cold": "Lead froid — relancer une fois avec un angle simple et une preuve sociale.",
        }.get(temperature, "")
        return f"Le prospect {detail}. {advice}"

    @staticmethod
    def _parse_subject_body(text: str, base_subject: str, base_body_html: str) -> dict[str, str]:
        """Parse a 'SUBJECT: ... BODY: ...' LLM response."""
        subject = base_subject
        body = base_body_html
        if "SUBJECT:" in text and "BODY:" in text:
            try:
                after_subject = text.split("SUBJECT:", 1)[1]
                subject_part, body_part = after_subject.split("BODY:", 1)
                subject = subject_part.strip() or base_subject
                body = body_part.strip() or base_body_html
            except (IndexError, ValueError):
                pass
        else:
            body = text.strip() or base_body_html
        return {"subject": subject, "body_html": body}


llm_service = LLMService()
