"""Unit tests for the module service — base tenant, activation, scoping, guards."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from enums.app_module import AppModule
from models.user_module import UserModule
from services.module_service import ModuleError, module_service


@pytest.fixture
def session() -> Iterator[Session]:
    """A session on an isolated in-memory SQLite with the user_modules table."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[UserModule.__table__])
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_base_module_is_always_active(session: Session) -> None:
    """The websites module is on without any stored row."""
    assert module_service.is_active(session, 1, AppModule.WEBSITES.value) is True


def test_wallet_module_is_off_by_default_then_activatable(session: Session) -> None:
    """Apple Wallet starts off and turns on once activated."""
    assert module_service.is_active(session, 1, AppModule.APPLE_WALLET.value) is False
    record = module_service.activate(session, 1, AppModule.APPLE_WALLET.value)
    assert record.is_active is True
    assert record.activated_at is not None
    assert module_service.is_active(session, 1, AppModule.APPLE_WALLET.value) is True


def test_deactivate_turns_the_module_off_in_place(session: Session) -> None:
    """Deactivating flips the same row rather than creating a duplicate."""
    module_service.activate(session, 1, AppModule.APPLE_WALLET.value)
    module_service.deactivate(session, 1, AppModule.APPLE_WALLET.value)
    assert module_service.is_active(session, 1, AppModule.APPLE_WALLET.value) is False
    assert session.query(UserModule).count() == 1


def test_active_modules_lists_base_plus_activated(session: Session) -> None:
    """The active list always includes the base module, plus what was turned on."""
    assert module_service.active_modules(session, 1) == [AppModule.WEBSITES.value]
    module_service.activate(session, 1, AppModule.APPLE_WALLET.value)
    assert module_service.active_modules(session, 1) == sorted([AppModule.WEBSITES.value, AppModule.APPLE_WALLET.value])


def test_activation_is_scoped_per_user(session: Session) -> None:
    """One user's activation does not leak to another."""
    module_service.activate(session, 1, AppModule.APPLE_WALLET.value)
    assert module_service.is_active(session, 1, AppModule.APPLE_WALLET.value) is True
    assert module_service.is_active(session, 2, AppModule.APPLE_WALLET.value) is False


def test_base_module_cannot_be_deactivated(session: Session) -> None:
    """The base module cannot be turned off."""
    with pytest.raises(ModuleError):
        module_service.deactivate(session, 1, AppModule.WEBSITES.value)


def test_unknown_module_raises(session: Session) -> None:
    """An unknown module value is rejected on read and on write."""
    with pytest.raises(ModuleError):
        module_service.is_active(session, 1, "does-not-exist")
    with pytest.raises(ModuleError):
        module_service.activate(session, 1, "does-not-exist")
