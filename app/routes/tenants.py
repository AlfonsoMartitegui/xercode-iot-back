from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.encryption import encrypt_secret
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain
from app.services.beaver_client import (
    BeaverAuthError,
    BeaverClient,
    BeaverConfigError,
    BeaverConnectionError,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantDomainOut(BaseModel):
    id: int
    domain: str
    is_primary: bool

    class Config:
        orm_mode = True


class TenantOut(BaseModel):
    id: int
    name: str
    code: str
    address: str | None = None
    redirect_url: str | None = None
    beaver_base_url: str | None = None
    beaver_mqtt_host: str | None = None
    beaver_mqtt_port: str | None = None
    beaver_admin_username: str | None = None
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
    beaver_mqtt_host: str | None = None
    beaver_mqtt_port: str | None = None
    beaver_admin_username: str | None = None
    beaver_admin_password: str | None = None
    is_active: bool = True


class TenantUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    redirect_url: str | None = None
    beaver_base_url: str | None = None
    beaver_mqtt_host: str | None = None
    beaver_mqtt_port: str | None = None
    beaver_admin_username: str | None = None
    beaver_admin_password: str | None = None
    is_active: bool | None = None


class TenantDomainCreate(BaseModel):
    domain: str
    is_primary: bool = False


class TenantDomainUpdate(BaseModel):
    domain: str | None = None
    is_primary: bool | None = None


class BeaverAuthTestOut(BaseModel):
    ok: bool
    tenant_id: int
    beaver_base_url: str
    authenticated_as: str
    token_type: str | None = None
    expires_in: int | None = None
    token_received: bool


class BeaverRoleOut(BaseModel):
    role_id: str
    name: str


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
        beaver_mqtt_host=tenant.beaver_mqtt_host,
        beaver_mqtt_port=tenant.beaver_mqtt_port,
        beaver_admin_username=tenant.beaver_admin_username,
        is_active=tenant.is_active,
        domains=[
            TenantDomainOut(id=d.id, domain=d.domain, is_primary=d.is_primary)
            for d in domains
        ],
    )


def get_tenant_or_404(db: Session, tenant_id: int) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return tenant


def get_tenant_domain_or_404(db: Session, tenant_id: int, domain_id: int) -> TenantDomain:
    domain = (
        db.query(TenantDomain)
        .filter(TenantDomain.id == domain_id, TenantDomain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Dominio no encontrado")
    return domain


def normalize_domain(raw_domain: str) -> str:
    domain = raw_domain.strip().lower()
    if "://" in domain:
        domain = domain.split("://", 1)[1]
    domain = domain.split("/", 1)[0]
    return domain.rstrip("/")


def build_tenant_domain_out(domain: TenantDomain) -> TenantDomainOut:
    return TenantDomainOut(
        id=domain.id,
        domain=domain.domain,
        is_primary=domain.is_primary,
    )


def ensure_single_primary_domain(db: Session, tenant_id: int, current_domain_id: int | None = None):
    query = db.query(TenantDomain).filter(TenantDomain.tenant_id == tenant_id)
    if current_domain_id is not None:
        query = query.filter(TenantDomain.id != current_domain_id)
    query.update({"is_primary": False}, synchronize_session=False)


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
        beaver_mqtt_host=tenant_in.beaver_mqtt_host,
        beaver_mqtt_port=tenant_in.beaver_mqtt_port,
        beaver_admin_username=tenant_in.beaver_admin_username,
        is_active=tenant_in.is_active,
    )
    if tenant_in.beaver_admin_password:
        try:
            tenant.beaver_admin_password_encrypted = encrypt_secret(
                tenant_in.beaver_admin_password
            )
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
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
    tenant = get_tenant_or_404(db, tenant_id)
    return build_tenant_out(db, tenant)


@router.put("/{tenant_id}", response_model=TenantOut)
def update_tenant(
    tenant_id: int,
    tenant_in: TenantUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    tenant = get_tenant_or_404(db, tenant_id)

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
    if tenant_in.beaver_mqtt_host is not None:
        tenant.beaver_mqtt_host = tenant_in.beaver_mqtt_host
    if tenant_in.beaver_mqtt_port is not None:
        tenant.beaver_mqtt_port = tenant_in.beaver_mqtt_port
    if tenant_in.beaver_admin_username is not None:
        tenant.beaver_admin_username = tenant_in.beaver_admin_username
    if tenant_in.beaver_admin_password:
        try:
            tenant.beaver_admin_password_encrypted = encrypt_secret(
                tenant_in.beaver_admin_password
            )
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
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
    tenant = get_tenant_or_404(db, tenant_id)

    tenant.is_active = False
    db.commit()
    return {"ok": True, "tenant_id": tenant.id, "is_active": tenant.is_active}


@router.post("/{tenant_id}/beaver/test-auth", response_model=BeaverAuthTestOut)
def test_tenant_beaver_auth(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    tenant = get_tenant_or_404(db, tenant_id)
    client = BeaverClient(tenant)

    try:
        result = client.test_auth()
    except BeaverConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BeaverAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except BeaverConnectionError as exc:
        raise HTTPException(status_code=504, detail=str(exc))

    return BeaverAuthTestOut(**result)


@router.get("/{tenant_id}/beaver/roles", response_model=List[BeaverRoleOut])
def list_tenant_beaver_roles(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    tenant = get_tenant_or_404(db, tenant_id)
    client = BeaverClient(tenant)

    try:
        roles = client.list_roles()
    except BeaverConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BeaverAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except BeaverConnectionError as exc:
        raise HTTPException(status_code=504, detail=str(exc))

    return [
        BeaverRoleOut(
            role_id=str(role.get("role_id")),
            name=str(role.get("name", "")),
        )
        for role in roles
        if role.get("role_id") and role.get("name")
    ]


@router.get("/{tenant_id}/domains", response_model=List[TenantDomainOut])
def get_tenant_domains(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    get_tenant_or_404(db, tenant_id)
    domains = db.query(TenantDomain).filter(TenantDomain.tenant_id == tenant_id).all()
    return [build_tenant_domain_out(domain) for domain in domains]


@router.post("/{tenant_id}/domains", response_model=TenantDomainOut)
def create_tenant_domain(
    tenant_id: int,
    domain_in: TenantDomainCreate,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    get_tenant_or_404(db, tenant_id)
    normalized_domain = normalize_domain(domain_in.domain)
    existing = db.query(TenantDomain).filter(TenantDomain.domain == normalized_domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="El dominio ya existe")

    if domain_in.is_primary:
        ensure_single_primary_domain(db, tenant_id)

    domain = TenantDomain(
        tenant_id=tenant_id,
        domain=normalized_domain,
        is_primary=domain_in.is_primary,
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return build_tenant_domain_out(domain)


@router.get("/{tenant_id}/domains/{domain_id}", response_model=TenantDomainOut)
def get_tenant_domain(
    tenant_id: int,
    domain_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    domain = get_tenant_domain_or_404(db, tenant_id, domain_id)
    return build_tenant_domain_out(domain)


@router.put("/{tenant_id}/domains/{domain_id}", response_model=TenantDomainOut)
def update_tenant_domain(
    tenant_id: int,
    domain_id: int,
    domain_in: TenantDomainUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    domain = get_tenant_domain_or_404(db, tenant_id, domain_id)

    if domain_in.domain is not None:
        normalized_domain = normalize_domain(domain_in.domain)
        existing = db.query(TenantDomain).filter(
            TenantDomain.domain == normalized_domain,
            TenantDomain.id != domain_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="El dominio ya existe")
        domain.domain = normalized_domain

    if domain_in.is_primary is not None:
        if domain_in.is_primary:
            ensure_single_primary_domain(db, tenant_id, current_domain_id=domain_id)
        domain.is_primary = domain_in.is_primary

    db.commit()
    db.refresh(domain)
    return build_tenant_domain_out(domain)


@router.delete("/{tenant_id}/domains/{domain_id}")
def delete_tenant_domain(
    tenant_id: int,
    domain_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(superadmin_required),
):
    domain = get_tenant_domain_or_404(db, tenant_id, domain_id)
    db.delete(domain)
    db.commit()
    return {"ok": True, "tenant_id": tenant_id, "domain_id": domain_id}
