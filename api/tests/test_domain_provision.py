"""One-action provisioning: register the domain, then point its DNS once OVH activates the zone.

The registration is validated live on a real order; here we pin the orchestration — register is
called and logged, and the background finalize points the DNS as soon as the zone is ready.
"""

import asyncio

import pytest

from services.domain import provision_service as ps_module
from services.domain.provision_service import domain_provision_service


class TestProvision:
    def test_registers_and_schedules_then_returns_the_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        recorded: list[dict[str, object]] = []

        async def _register(domain: str, **_kw: object) -> dict[str, object]:
            return {"orderId": 42}

        def _fake_create_task(coro: object) -> object:
            coro.close()  # do not run the background finalize in this unit test

            class _Task:
                def add_done_callback(self, _cb: object) -> None:
                    return None

            return _Task()

        monkeypatch.setattr(ps_module.ovh_domain_provider, "register", _register)
        monkeypatch.setattr(ps_module.asyncio, "create_task", _fake_create_task)
        monkeypatch.setattr(ps_module.activity_log_service, "record", lambda **kw: recorded.append(kw))

        order = asyncio.run(domain_provision_service.provision("tacos-maru.fr", user_id=1))

        assert order == {"orderId": 42}
        assert any(entry["action"] == "domain_registered" for entry in recorded)

    def test_finalize_points_dns_once_the_zone_is_ready(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import services.vercel_service as vercel_module

        state = {"polls": 0, "pointed": False, "attached": False}
        recorded: list[dict[str, object]] = []

        async def _sleep(_seconds: float) -> None:
            return None

        async def _zone_ready(_domain: str) -> bool:
            state["polls"] += 1
            return state["polls"] >= 2  # ready on the second poll

        async def _point(_domain: str, **_kw: object) -> None:
            state["pointed"] = True

        async def _attach(_domain: str) -> dict[str, object]:
            state["attached"] = True
            return {}

        monkeypatch.setattr(ps_module.asyncio, "sleep", _sleep)
        monkeypatch.setattr(ps_module.ovh_domain_provider, "zone_ready", _zone_ready)
        monkeypatch.setattr(ps_module.ovh_domain_provider, "point_to_vercel", _point)
        monkeypatch.setattr(vercel_module.vercel_service, "attach_domain", _attach)
        monkeypatch.setattr(ps_module.activity_log_service, "record", lambda **kw: recorded.append(kw))

        asyncio.run(domain_provision_service._finalize("tacos-maru.fr", 1))

        assert state["attached"] is True
        assert state["pointed"] is True
        assert any(entry["action"] == "domain_live" for entry in recorded)
