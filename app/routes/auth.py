from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain
from app.models.user_tenant import UserTenant
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.deps import get_current_user

from typing import List

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    # 1) resolver tenant por dominio
    host = request.headers.get("host")
    if not host:
        raise HTTPException(status_code=400, detail="Host header required")

    domain = db.query(TenantDomain).filter(TenantDomain.domain == host).first()

    # de momento NO levantamos error si no hay domain,
    # porque puede que el usuario sea superadmin
    if domain:
        tenant = db.query(Tenant).filter(Tenant.id == domain.tenant_id).first()
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=400, detail="Tenant inactive or not found")
        tenant_id_from_domain = tenant.id
    else:
        tenant = None
        tenant_id_from_domain = None

    # 2) buscar usuario
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 3) validar password
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 4) determinar rol y tenant_id final
    if user.is_superadmin:
        # superadmin puede entrar incluso si NO hay domain
        # en ese caso trabajara con tenant_id = 0 (modo global)
        final_tenant_id = tenant_id_from_domain if tenant_id_from_domain else 0
        final_role = "superadmin"
    else:
        # usuario normal: aqui SI es obligatorio que haya tenant
        if not tenant_id_from_domain:
            raise HTTPException(status_code=400, detail="Domain not registered")

        ut = (
            db.query(UserTenant)
            .filter(
                UserTenant.user_id == user.id,
                UserTenant.tenant_id == tenant_id_from_domain,
                UserTenant.is_active == True,
            )
            .first()
        )
        if not ut:
            raise HTTPException(
                status_code=403,
                detail="User not allowed for this tenant",
            )

        final_tenant_id = tenant_id_from_domain
        final_role = ut.role

    # 5) crear token
    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "tenant_id": final_tenant_id,
            "role": final_role,
            "is_superadmin": user.is_superadmin,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return current_user

# --- NUEVOS ENDPOINTS SOLO SUPERADMIN ---
class TenantOut(BaseModel):
    id: int
    name: str
    class Config:
        orm_mode = True

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str
    is_superadmin: bool
    tenants: List[TenantOut]
    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    is_active: bool = True
    is_superadmin: bool = False
    tenant_ids: List[int] = []

class UserUpdate(BaseModel):
    username: str = None
    email: str = None
    password: str = None
    is_active: bool = None
    is_superadmin: bool = None

def superadmin_required(current_user = Depends(get_current_user)):
    # current_user es un dict, no un modelo User
    if not current_user.get("is_superadmin", False):
        raise HTTPException(status_code=403, detail="No autorizado")
    return current_user

@router.get("/users", response_model=List[UserOut], tags=["users"])
def list_users(db: Session = Depends(get_db), current_user = Depends(superadmin_required)):
    users = db.query(User).all()
    result = []
    for user in users:
        user_tenants = db.query(UserTenant).filter(UserTenant.user_id == user.id).all()
        tenants = [db.query(Tenant).get(ut.tenant_id) for ut in user_tenants]
        result.append(UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=str(user.created_at) if hasattr(user, "created_at") else "",
            is_superadmin=getattr(user, "is_superadmin", False),
            tenants=[TenantOut(id=t.id, name=t.name) for t in tenants if t]
        ))
    return result


# Nuevo endpoint para crear usuario
@router.post("/user", response_model=UserOut, tags=["users"])
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current_user = Depends(superadmin_required)):
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="El email ya existe")
    user = User(
        username=user_in.username,
        email=user_in.email,
        is_active=user_in.is_active,
        is_superadmin=user_in.is_superadmin
    )
    user.password_hash = get_password_hash(user_in.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    # Compatibilidad legacy: el flujo Beaver debe crear membresias explicitas via POST /users/{user_id}/tenants.
    tenants = []
    for tenant_id in user_in.tenant_ids:
        tenant = db.query(Tenant).get(tenant_id)
        if tenant:
            ut = UserTenant(user_id=user.id, tenant_id=tenant.id, is_active=True, role="user")
            db.add(ut)
            tenants.append(tenant)
    db.commit()
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=str(user.created_at) if hasattr(user, "created_at") else "",
        is_superadmin=getattr(user, "is_superadmin", False),
        tenants=[TenantOut(id=t.id, name=t.name) for t in tenants]
    )

# Endpoint para obtener usuario por id
@router.get("/user/{user_id}", response_model=UserOut, tags=["users"])
def get_user(user_id: int, db: Session = Depends(get_db), current_user = Depends(superadmin_required)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user_tenants = db.query(UserTenant).filter(UserTenant.user_id == user.id).all()
    tenants = [db.query(Tenant).get(ut.tenant_id) for ut in user_tenants]
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=str(user.created_at) if hasattr(user, "created_at") else "",
        is_superadmin=getattr(user, "is_superadmin", False),
        tenants=[TenantOut(id=t.id, name=t.name) for t in tenants if t]
    )

# Endpoint para editar usuario por id
@router.post("/user/{user_id}", response_model=UserOut, tags=["users"])
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db), current_user = Depends(superadmin_required)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user_in.username is not None:
        user.username = user_in.username
    if user_in.email is not None:
        user.email = user_in.email
    if user_in.password is not None:
        user.password_hash = get_password_hash(user_in.password)
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.is_superadmin is not None:
        user.is_superadmin = user_in.is_superadmin
    db.commit()
    db.refresh(user)
    user_tenants = db.query(UserTenant).filter(UserTenant.user_id == user.id).all()
    tenants = [db.query(Tenant).get(ut.tenant_id) for ut in user_tenants]
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=str(user.created_at) if hasattr(user, "created_at") else "",
        is_superadmin=getattr(user, "is_superadmin", False),
        tenants=[TenantOut(id=t.id, name=t.name) for t in tenants if t]
    )
