import subprocess
import sys

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text

from tests.conftest import ROOT

PASSWORD = "clave-segura-123"


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    """Aplica las migraciones Alembic sobre la BD de pruebas (las ejercita de paso)."""
    env = None
    for cmd in (["downgrade", "base"], ["upgrade", "head"]):
        res = subprocess.run(
            [sys.executable, "-m", "alembic", *cmd], cwd=ROOT, capture_output=True, text=True, env=env
        )
        assert res.returncode == 0, res.stderr


@pytest_asyncio.fixture(autouse=True)
async def clean_db(migrated_db):
    from app.api.deps import get_rate_limiter
    from app.infrastructure.db.session import get_engine
    from app.infrastructure.db.models import Base

    get_rate_limiter().clear()
    async with get_engine().begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in Base.metadata.sorted_tables:
            await conn.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    yield


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def make_user(email: str = "ana@example.com", password: str = PASSWORD):
    from app.application.auth import AuthConfig, AuthService
    from app.infrastructure.db.session import get_sessionmaker
    from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
    from app.infrastructure.security.passwords import Argon2PasswordHasher
    from app.infrastructure.security.tokens import JwtTokenService

    async with SqlAlchemyUnitOfWork(get_sessionmaker()) as uow:
        svc = AuthService(uow, Argon2PasswordHasher(), JwtTokenService("x"), AuthConfig())
        return await svc.create_user(email, password, "Ana")


async def login(client: httpx.AsyncClient, email: str, password: str = PASSWORD) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def user(clean_db):
    return await make_user()


@pytest_asyncio.fixture
async def api(client, user):
    """Cliente autenticado como el usuario por defecto."""
    token = await login(client, user.email)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def cats(api):
    """Categorías sembradas por nombre."""
    r = await api.get("/api/v1/categories")
    return {c["name"]: c for c in r.json()}
