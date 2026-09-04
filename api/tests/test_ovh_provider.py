"""OVH registrar provider: signed auth, the purchase cart flow, and apex DNS pointing.

The real purchase spends money and depends on the operator's account, so it is validated live
on a first order; these tests pin what can be pinned offline — the signature format, the inert
guard when unconfigured, and the exact request sequence/shape of register + DNS (mocked OVH).
"""

import asyncio

import pytest

import services.domain.ovh_provider as ovh_module
from services.domain.ovh_provider import DomainProviderError, OvhDomainProvider


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, json_body: object = None, text: str = "") -> None:
        self.status_code = status_code
        self._json = json_body
        self.text = text
        self.content = b"x" if json_body is not None else b""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._json


class _FakeClient:
    """Records API calls and returns canned responses keyed by ``(method, url-substring)``.

    Routes are tried in insertion order (most specific first), so the ambiguous pair — POST
    ``/order/cart`` (create) vs the deeper POST paths, and GET offers (``?domain=``) vs the add
    path — resolve to the intended response.
    """

    def __init__(self, routes: dict[tuple[str, str], object]) -> None:
        self._routes = routes
        self.calls: list[tuple[str, str, str | None]] = []

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def get(self, url: str) -> _FakeResponse:
        if url.endswith("/auth/time"):
            return _FakeResponse(text="1700000000")
        return await self.request("GET", url)

    async def request(self, method: str, url: str, headers: dict | None = None, content: str | None = None):
        self.calls.append((method, url, content))
        for (route_method, suffix), body in self._routes.items():
            if route_method == method and suffix in url:
                return _FakeResponse(json_body=body)
        return _FakeResponse(json_body=None)


def _provider() -> OvhDomainProvider:
    provider = OvhDomainProvider()
    provider._app_key = "ak"
    provider._app_secret = "as"
    provider._consumer_key = "ck"
    provider._subsidiary = "FR"
    return provider


class TestConfigAndSignature:
    def test_inert_without_credentials(self) -> None:
        provider = OvhDomainProvider()
        provider._app_key = provider._app_secret = provider._consumer_key = None
        assert provider.is_configured is False
        with pytest.raises(DomainProviderError):
            asyncio.run(provider.register("tacos-maru.fr"))

    def test_signature_format_and_body_sensitivity(self) -> None:
        provider = _provider()
        sig = provider._sign("GET", "https://eu.api.ovh.com/1.0/me", "", 1700000000)
        assert sig.startswith("$1$") and len(sig) == 43  # "$1$" (3) + 40 hex chars
        other = provider._sign("GET", "https://eu.api.ovh.com/1.0/me", '{"x":1}', 1700000000)
        assert sig != other  # the body is part of the signed payload


class TestRegister:
    def test_runs_the_cart_flow_and_returns_the_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            ("POST", "/assign"): None,
            ("POST", "/order/cart/c1/domain"): {"itemId": 5},
            ("GET", "/domain?domain="): [
                {"action": "create", "premium": False, "planCode": "fr", "pricingMode": "create-default"}
            ],
            ("GET", "/requiredConfiguration"): [{"label": "OWNER_CONTACT", "required": True}],
            ("POST", "/configuration"): None,
            ("POST", "/checkout"): {"orderId": 999},
            ("POST", "/order/cart"): {"cartId": "c1"},
            ("GET", "/me"): {"nichandle": "ab1234-ovh"},
        }
        fake = _FakeClient(routes)
        monkeypatch.setattr(ovh_module.httpx, "AsyncClient", lambda **_kw: fake)

        order = asyncio.run(_provider().register("tacos-maru.fr"))

        assert order == {"orderId": 999}
        # The owner contact was defaulted to the account nichandle, and checkout was reached.
        config_call = next(c for c in fake.calls if "/configuration" in c[1])
        assert '"/me/contact/ab1234-ovh"' in (config_call[2] or "")
        assert any("/checkout" in c[1] for c in fake.calls)

    def test_refuses_when_no_standard_offer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            ("POST", "/assign"): None,
            ("POST", "/order/cart"): {"cartId": "c1"},
            ("GET", "/domain?domain="): [
                {"action": "create", "premium": True, "planCode": "fr", "pricingMode": "create-premium"}
            ],
        }
        monkeypatch.setattr(ovh_module.httpx, "AsyncClient", lambda **_kw: _FakeClient(routes))
        with pytest.raises(DomainProviderError):
            asyncio.run(_provider().register("premium.fr"))


class TestPointToVercel:
    def test_sets_apex_a_record_then_refreshes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeClient({("POST", "/record"): None, ("POST", "/refresh"): None})
        monkeypatch.setattr(ovh_module.httpx, "AsyncClient", lambda **_kw: fake)

        asyncio.run(_provider().point_to_vercel("tacos-maru.fr", ip="76.76.21.21"))

        record_call = next(c for c in fake.calls if c[1].endswith("/record"))
        assert '"fieldType": "A"' in (record_call[2] or "")
        assert '"target": "76.76.21.21"' in (record_call[2] or "")
        assert any(c[1].endswith("/refresh") for c in fake.calls)
