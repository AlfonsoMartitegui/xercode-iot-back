from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func, ForeignKey
from app.db.session import Base

class TenantDomain(Base):
    __tablename__ = "tenant_domains"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    domain = Column(String(150), unique=True, nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
