from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.tenant_domain import TenantDomain

from app.routes import auth
from app.routes import tenants
from app.routes import user_tenants

app = FastAPI()
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # luego tu dominio real o el del nginx
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(user_tenants.router)

@app.get("/ping")
def ping():
    return {"msg": "pong"}

@app.get("/tenants")
def list_tenants(db: Session = Depends(get_db)):
    tenants = db.query(Tenant).all()
    return tenants


@app.get("/whoami")
def whoami(request: Request, db: Session = Depends(get_db)):
    host = request.headers.get("host")
    if not host:
      return {"error": "no host header"}

    domain = db.query(TenantDomain).filter(TenantDomain.domain == host).first()
    if not domain:
        return {"tenant": None, "domain": host}

    tenant = db.query(Tenant).filter(Tenant.id == domain.tenant_id).first()
    return {
        "host": host,
        "tenant_id": tenant.id if tenant else None,
        "tenant_code": tenant.code if tenant else None,
        "tenant_name": tenant.name if tenant else None,
        "redirect_url": tenant.redirect_url if tenant else None,
        "beaver_base_url": tenant.beaver_base_url if tenant else None,
    }
