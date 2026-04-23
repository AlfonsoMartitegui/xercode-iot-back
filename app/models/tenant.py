from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func
from app.db.session import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    address = Column(String(255), nullable=True)
    redirect_url = Column(String(255), nullable=True)
    beaver_base_url = Column(String(255), nullable=True)
    beaver_admin_username = Column(String(150), nullable=True)
    beaver_admin_password_encrypted = Column(String(512), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
    )
