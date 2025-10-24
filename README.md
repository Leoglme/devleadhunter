# DevLeadHunter

**Hunt down freelance web dev clients — automatically.**

> *"No website? No problem. I’ll find them."*

Scrape, cross-check, and rank businesses **without a website** — ready to pitch.

### Features
- Multi-source scraping (Google Business, PagesJaunes, Mappy, Yelp)
- AI-powered "needs a website" detection
- Confidence scoring (1–4 stars)
- Email guessing + website gap detection
- REST API (FastAPI) — 20 leads in 2 seconds

```bash
GET /api/hunt?category=restaurant&city=Paris&max=20
→ 20 high-confidence leads with name, phone, address, email
