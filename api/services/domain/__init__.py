"""Domain automation for the post-sale go-live: suggest a domain, check availability.

The registration + DNS pointing (per-user ``DomainProvider``) land in a later increment,
gated on the operator's registrar API credentials. This package already holds the two
pieces that need no credentials: availability (AFNIC RDAP) and suggestion (code logic + Groq).
"""
