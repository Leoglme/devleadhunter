"""Module service — which tool modules a user has activated.

The websites module is the base tenant and is always active; other modules (Apple Wallet,
and future ones) are toggled per user. Everything downstream gates on ``is_active`` so the
tool behaves as a multi-module house rather than a single product.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from enums.app_module import BASE_MODULES, AppModule
from models.user_module import UserModule

_KNOWN_MODULES: frozenset[str] = frozenset(module.value for module in AppModule)


class ModuleError(RuntimeError):
    """Raised on an unknown module or an illegal toggle (e.g. deactivating the base)."""


class ModuleService:
    """Reads and writes per-user module activation."""

    def is_active(self, db: Session, user_id: int, module: str) -> bool:
        """Whether a module is active for a user (base modules are always on).

        Args:
            db: Database session.
            user_id: The user to check.
            module: Module value to check.

        Returns:
            ``True`` when the module is active.

        Raises:
            ModuleError: When the module is unknown.
        """
        self._validate(module)
        if module in BASE_MODULES:
            return True
        record = self._get(db, user_id, module)
        return record is not None and record.is_active

    def active_modules(self, db: Session, user_id: int) -> list[str]:
        """Return the sorted list of a user's active modules (base modules included).

        Args:
            db: Database session.
            user_id: The user whose modules to list.

        Returns:
            Sorted active module values.
        """
        active = set(BASE_MODULES)
        rows = db.query(UserModule).filter(UserModule.user_id == user_id, UserModule.is_active.is_(True)).all()
        active.update(row.module for row in rows)
        return sorted(active)

    def set_active(self, db: Session, user_id: int, module: str, active: bool) -> UserModule:
        """Activate or deactivate a module for a user.

        Args:
            db: Database session.
            user_id: The user to toggle.
            module: Module value to toggle.
            active: Target state.

        Returns:
            The persisted activation row.

        Raises:
            ModuleError: On an unknown module or an attempt to disable a base module.
        """
        self._validate(module)
        if module in BASE_MODULES and not active:
            raise ModuleError(f"Module {module!r} is always active and cannot be deactivated.")
        record = self._get(db, user_id, module)
        if record is None:
            record = UserModule(user_id=user_id, module=module)
            db.add(record)
        record.is_active = active
        if active:
            record.activated_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
        db.refresh(record)
        return record

    def activate(self, db: Session, user_id: int, module: str) -> UserModule:
        """Activate a module for a user."""
        return self.set_active(db, user_id, module, True)

    def deactivate(self, db: Session, user_id: int, module: str) -> UserModule:
        """Deactivate a module for a user."""
        return self.set_active(db, user_id, module, False)

    @staticmethod
    def _get(db: Session, user_id: int, module: str) -> UserModule | None:
        """Return the user's row for a module, or ``None``."""
        return db.query(UserModule).filter(UserModule.user_id == user_id, UserModule.module == module).first()

    @staticmethod
    def _validate(module: str) -> None:
        """Raise when a module value is not a known module."""
        if module not in _KNOWN_MODULES:
            raise ModuleError(f"Unknown module {module!r}.")


module_service = ModuleService()
