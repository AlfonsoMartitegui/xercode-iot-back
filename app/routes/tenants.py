from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantDomainOut(BaseModel):
    id: int
    domain: str

    class Config:
        orm_mode = True


class TenantOut(BaseModel):
    id: int
    name: str
    code: str
    address: str | None = None
    redirect_url: str | None = None
    beaver_base_url: str | None = None
    is_active: bool
    domains: List[TenantDomainOut] = []

    class Config:
        orm_mode = True


class TenantCreate(BaseModel):
    name: str
    code: str
    address: str | None = None
    redirect_url: str | None = None
    beaver_base_url: str | None = None
    is_active: bool = True


class TenantUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    redirect_url: str | None = None
    beaver_base_url: str | None = None
    is_active: bool | None = None


def superadmin_required(current_user=Depends(get_current_user)):
    if not current_user.get("is_superadmin", False):
        raise HTTPException(status_code=403, detail="No autorizado")
    return current_user


def build_tenant_out(db: Session, tenant: Tenant) -> TenantOut:
    domains = db.query(TenantDomain).filter(TenantDomain.tenant_id == tenant.id).all()
    return TenantOut(
        id=tenant.id,
        name=tenant.name,
        code=tenant.code,
        address=tenant.address,
        redirect_url=tenant.redirect_url,
        beaver_base_url=tenant.beaver_base_url,
        is_active=tenant.is_active,
        domains=[TenantDomainOut(id=d.id, domain=d.domain) for d in domains],
    )


@router.get("/", response_model=List[TenantOut])
def get_tenants(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
    return [build_tenant_out(db, tenant) for tenant in tenants]


@router.post("/", response_model=TenantOut)
def create_tenant(
    tenant_in: TenantCreate,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    existing = (
        db.query(Tenant)
        .filter((Tenant.name == tenant_in.name) | (Tenant.code == tenant_in.code))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="El tenant ya existe")

    tenant = Tenant(
        name=tenant_in.name,
        code=tenant_in.code,
        address=tenant_in.address,
        redirect_url=tenant_in.redirect_url,
        beaver_base_url=tenant_in.beaver_base_url,
        is_active=tenant_in.is_active,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return build_tenant_out(db, tenant)


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return build_tenant_out(db, tenant)


@router.put("/{tenant_id}", response_model=TenantOut)
def update_tenant(
    tenant_id: int,
    tenant_in: TenantUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    if tenant_in.name is not None and tenant_in.name != tenant.name:
        existing_by_name = db.query(Tenant).filter(
            Tenant.name == tenant_in.name,
            Tenant.id != tenant_id,
        ).first()
        if existing_by_name:
            raise HTTPException(status_code=400, detail="Ya existe un tenant con ese nombre")
        tenant.name = tenant_in.name

    if tenant_in.code is not None and tenant_in.code != tenant.code:
        existing_by_code = db.query(Tenant).filter(
            Tenant.code == tenant_in.code,
            Tenant.id != tenant_id,
        ).first()
        if existing_by_code:
            raise HTTPException(status_code=400, detail="Ya existe un tenant con ese code")
        tenant.code = tenant_in.code

    if tenant_in.address is not None:
        tenant.address = tenant_in.address
    if tenant_in.redirect_url is not None:
        tenant.redirect_url = tenant_in.redirect_url
    if tenant_in.beaver_base_url is not None:
        tenant.beaver_base_url = tenant_in.beaver_base_url
    if tenant_in.is_active is not None:
        tenant.is_active = tenant_in.is_active

    db.commit()
    db.refresh(tenant)
    return build_tenant_out(db, tenant)


@router.delete("/{tenant_id}")
def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    tenant.is_active = False
    db.commit()
    return {"ok": True, "tenant_id": tenant.id, "is_active": tenant.is_active}
