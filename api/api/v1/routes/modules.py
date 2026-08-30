"""Module activation endpoints — a user turns tool modules on and off.

Feeds the dashboard nav (which module areas to show) and gates module-specific routes.
The websites module is the base tenant and is always active.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from enums.app_module import AppModule
from models.user import User
from services.auth_service import get_current_active_user
from services.module_service import ModuleError, module_service

router = APIRouter(prefix="/modules", tags=["modules"])


class ModuleState(BaseModel):
    """A module and whether it is active for the user."""

    module: str
    active: bool


class ModulesResponse(BaseModel):
    """The user's activation state for every module."""

    modules: list[ModuleState]


@router.get("", response_model=ModulesResponse)
async def list_modules(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ModulesResponse:
    """List every module with the caller's activation state."""
    active = set(module_service.active_modules(db, current_user.id))
    return ModulesResponse(
        modules=[ModuleState(module=module.value, active=module.value in active) for module in AppModule]
    )


@router.post("/{module}/activate", response_model=ModuleState)
async def activate_module(
    module: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ModuleState:
    """Activate a module for the caller."""
    try:
        record = module_service.activate(db, current_user.id, module)
    except ModuleError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return ModuleState(module=record.module, active=record.is_active)


@router.post("/{module}/deactivate", response_model=ModuleState)
async def deactivate_module(
    module: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ModuleState:
    """Deactivate a module for the caller."""
    try:
        record = module_service.deactivate(db, current_user.id, module)
    except ModuleError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return ModuleState(module=record.module, active=record.is_active)
