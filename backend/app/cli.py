"""CLI: python -m app.cli create-user --email X --password Y"""
import argparse
import asyncio
import sys

from app.application.auth import AuthConfig, AuthService
from app.core.config import get_settings
from app.domain.exceptions import DomainError
from app.infrastructure.db.session import dispose_engine, get_sessionmaker
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.security.passwords import Argon2PasswordHasher
from app.infrastructure.security.tokens import JwtTokenService


async def create_user(email: str, password: str, display_name: str | None) -> None:
    s = get_settings()
    try:
        async with SqlAlchemyUnitOfWork(get_sessionmaker()) as uow:
            svc = AuthService(
                uow,
                Argon2PasswordHasher(),
                JwtTokenService(s.jwt_secret, s.access_token_minutes),
                AuthConfig(s.refresh_token_days, s.default_currency, s.default_timezone),
            )
            user = await svc.create_user(email, password, display_name)
            print(f"Usuario creado: {user.email} ({user.id})")
    finally:
        await dispose_engine()


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    cu = sub.add_parser("create-user", help="Crea un usuario (siembra categorías por defecto)")
    cu.add_argument("--email", required=True)
    cu.add_argument("--password", required=True)
    cu.add_argument("--display-name")
    args = parser.parse_args()
    try:
        asyncio.run(create_user(args.email, args.password, args.display_name))
    except DomainError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
