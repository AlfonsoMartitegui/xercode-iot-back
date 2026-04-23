import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)

class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_NAME: str = os.getenv("DB_NAME", "iotdb")
    DB_USER: str = os.getenv("DB_USER", "iotuser")
    DB_PASS: str = os.getenv("DB_PASS", "iotpass")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-cambia-esto")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    BEAVER_CREDENTIALS_ENCRYPTION_KEY: str = os.getenv(
        "BEAVER_CREDENTIALS_ENCRYPTION_KEY",
        "",
    )
    BEAVER_CLIENT_ID: str = os.getenv("BEAVER_CLIENT_ID", "")
    BEAVER_CLIENT_SECRET: str = os.getenv("BEAVER_CLIENT_SECRET", "")
    BEAVER_HTTP_TIMEOUT_SECONDS: int = int(
        os.getenv("BEAVER_HTTP_TIMEOUT_SECONDS", "10")
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24))
    )

    SQLALCHEMY_DATABASE_URI: str = (
        f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

settings = Settings()
