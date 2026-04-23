from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_tenant import UserTenant
from app.services.beaver_client import (
    BeaverAuthError,
    BeaverClient,
    BeaverConfigError,
    BeaverConnectionError,
)

router = APIRouter(prefix="/users", tags=["user-tenants"])


class UserTenantOut(BaseModel):
    user_id: int
    tenant_id: int
    role: str
    beaver_role_id: str | None = None
    is_active: bool

    class Config:
        orm_mode = True


class UserTenantCreate(BaseModel):
    tenant_id: int
    role: str
    beaver_role_id: str | None = None
    is_active: bool = True


class UserTenantUpdate(BaseModel):
    role: str | None = None
    beaver_role_id: str | None = None
    is_active: bool | None = None


class BeaverProvisionRequest(BaseModel):
    password: str


class BeaverProvisionOut(BaseModel):
    ok: bool
    tenant_id: int
    user_id: int
    email: str
    nickname: str
    beaver_user_id: str
    created_user: bool
    found_existing_user: bool
    role_associated: bool
    role_id: str


class BeaverUpdateOut(BaseModel):
    ok: bool
    tenant_id: int
    user_id: int
    email: str
    nickname: str
    beaver_user_id: str
    updated: bool


def superadmin_required(current_user=Depends(get_current_user)):
    if not current_user.get("is_superadmin", False):
        raise HTTPException(status_code=403, detail="No autorizado")
    return current_user


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def get_tenant_or_404(db: Session, tenant_id: int) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return tenant


def get_user_tenant_or_404(db: Session, user_id: int, tenant_id: int) -> UserTenant:
    user_tenant = (
        db.query(UserTenant)
        .filter(UserTenant.user_id == user_id, UserTenant.tenant_id == tenant_id)
        .first()
    )
    if not user_tenant:
        raise HTTPException(status_code=404, detail="Asignacion no encontrada")
    return user_tenant


def build_user_tenant_out(user_tenant: UserTenant) -> UserTenantOut:
    return UserTenantOut(
        user_id=user_tenant.user_id,
        tenant_id=user_tenant.tenant_id,
        role=user_tenant.role,
        beaver_role_id=user_tenant.beaver_role_id,
        is_active=user_tenant.is_active,
    )


@router.get("/{user_id}/tenants", response_model=List[UserTenantOut])
def list_user_tenants(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    get_user_or_404(db, user_id)
    memberships = db.query(UserTenant).filter(UserTenant.user_id == user_id).all()
    return [build_user_tenant_out(membership) for membership in memberships]


@router.post(
    "/{user_id}/tenants",
    response_model=UserTenantOut,
    status_code=status.HTTP_201_CREATED,
)
def create_user_tenant(
    user_id: int,
    payload: UserTenantCreate,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    get_user_or_404(db, user_id)
    get_tenant_or_404(db, payload.tenant_id)
    existing = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == payload.tenant_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="La asignacion ya existe")

    membership = UserTenant(
        user_id=user_id,
        tenant_id=payload.tenant_id,
        role=payload.role,
        beaver_role_id=payload.beaver_role_id,
        is_active=payload.is_active,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return build_user_tenant_out(membership)


@router.put("/{user_id}/tenants/{tenant_id}", response_model=UserTenantOut)
def update_user_tenant(
    user_id: int,
    tenant_id: int,
    payload: UserTenantUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    membership = get_user_tenant_or_404(db, user_id, tenant_id)

    if payload.role is not None:
        membership.role = payload.role
    if payload.beaver_role_id is not None:
        membership.beaver_role_id = payload.beaver_role_id
    if payload.is_active is not None:
        membership.is_active = payload.is_active

    db.commit()
    db.refresh(membership)
    return build_user_tenant_out(membership)


@router.post(
    "/{user_id}/tenants/{tenant_id}/beaver/provision",
    response_model=BeaverProvisionOut,
)
def provision_user_tenant_in_beaver(
    user_id: int,
    tenant_id: int,
    payload: BeaverProvisionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    user = get_user_or_404(db, user_id)
    membership = get_user_tenant_or_404(db, user_id, tenant_id)
    tenant = get_tenant_or_404(db, tenant_id)

    if not user.email:
        raise HTTPException(status_code=400, detail="User email is required for Beaver provisioning")
    if not membership.is_active:
        raise HTTPException(status_code=400, detail="User-tenant assignment is inactive")
    if not membership.beaver_role_id:
        raise HTTPException(status_code=400, detail="User-tenant Beaver role is not configured")

    client = BeaverClient(tenant)
    try:
        result = client.provision_user(
            email=user.email,
            nickname=user.username,
            password=payload.password,
            role_id=membership.beaver_role_id,
        )
    except BeaverConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BeaverAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except BeaverConnectionError as exc:
        raise HTTPException(status_code=504, detail=str(exc))

    return BeaverProvisionOut(
        ok=True,
        tenant_id=tenant_id,
        user_id=user_id,
        email=user.email,
        nickname=user.username,
        beaver_user_id=str(result["beaver_user_id"]),
        created_user=result["created_user"],
        found_existing_user=result["found_existing_user"],
        role_associated=result["role_associated"],
        role_id=str(result["role_id"]),
    )


@router.put(
    "/{user_id}/tenants/{tenant_id}/beaver/update",
    response_model=BeaverUpdateOut,
)
def update_user_tenant_in_beaver(
    user_id: int,
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    user = get_user_or_404(db, user_id)
    membership = get_user_tenant_or_404(db, user_id, tenant_id)
    tenant = get_tenant_or_404(db, tenant_id)

    if not user.email:
        raise HTTPException(status_code=400, detail="User email is required for Beaver update")
    if not membership.is_active:
        raise HTTPException(status_code=400, detail="User-tenant assignment is inactive")

    client = BeaverClient(tenant)
    try:
        result = client.update_user(
            email=user.email,
            nickname=user.username,
        )
    except BeaverConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BeaverAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except BeaverConnectionError as exc:
        raise HTTPException(status_code=504, detail=str(exc))

    return BeaverUpdateOut(
        ok=True,
        tenant_id=tenant_id,
        user_id=user_id,
        email=user.email,
        nickname=user.username,
        beaver_user_id=str(result["beaver_user_id"]),
        updated=result["updated"],
    )


@router.delete("/{user_id}/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_tenant(
    user_id: int,
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    membership = get_user_tenant_or_404(db, user_id, tenant_id)
    db.delete(membership)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
