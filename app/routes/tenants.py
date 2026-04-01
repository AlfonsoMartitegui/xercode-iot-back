from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain
from app.core.deps import get_current_user
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/tenants", tags=["tenants"])

class TenantDomainOut(BaseModel):
    id: int
    domain: str
    class Config:
        orm_mode = True

class TenantOut(BaseModel):
    id: int
    name: str
    code: str = None
    is_active: bool
    domains: List[TenantDomainOut] = []
    class Config:
        orm_mode = True

class TenantCreate(BaseModel):
    name: str
    code: str = None
    is_active: bool = True

@router.get("/", response_model=List[TenantOut])
def get_tenants(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
    result = []
    for tenant in tenants:
        domains = db.query(TenantDomain).filter(TenantDomain.tenant_id == tenant.id).all()
        result.append(TenantOut(
            id=tenant.id,
            name=tenant.name,
            code=tenant.code,
            is_active=tenant.is_active,
            domains=[TenantDomainOut(id=d.id, domain=d.domain) for d in domains]
        ))
    return result

# Endpoint para crear tenant
@router.post("/", response_model=TenantOut)
def create_tenant(tenant_in: TenantCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    existing = db.query(Tenant).filter(Tenant.name == tenant_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="El tenant ya existe")
    tenant = Tenant(name=tenant_in.name, code=tenant_in.code, is_active=tenant_in.is_active)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant
