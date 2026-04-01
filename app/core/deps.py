from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.security import SECRET_KEY, ALGORITHM
from app.db.session import get_db
from app.models.user import User
from app.models.user_tenant import UserTenant
from app.models.tenant import Tenant

# Mecanismo de autenticación por cabecera Authorization: Bearer <token>
bearer_scheme = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Valida el JWT, recupera el usuario y verifica permisos."""

    token = creds.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decodificar el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: int = payload.get("tenant_id")
        is_superadmin: bool = payload.get("is_superadmin", False)

        if user_id is None or tenant_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Buscar el usuario en la base de datos
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise credentials_exception

    # Si no es superadmin, comprobar que pertenece al tenant
    if not is_superadmin:
        ut = (
            db.query(UserTenant)
            .filter(
                UserTenant.user_id == user.id,
                UserTenant.tenant_id == tenant_id,
                UserTenant.is_active == True,
            )
            .first()
        )
        if not ut:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not allowed for this tenant",
            )
        role = ut.role
    else:
        # Si es superadmin, le damos rol especial y acceso total
        role = "superadmin"

    # Recuperar información del tenant (si existe)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    # Devolver usuario “actual” con toda la info útil
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "tenant_id": tenant_id,
        "tenant_code": tenant.code if tenant else None,
        "role": role,
        "is_superadmin": is_superadmin,
    }
