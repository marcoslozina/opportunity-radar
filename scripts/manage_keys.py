"""CLI script for managing API keys.

Usage:
    python scripts/manage_keys.py create --client propflow --scopes read:opportunities
    python scripts/manage_keys.py revoke --key-id <uuid>
    python scripts/manage_keys.py list
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path so domain/infra modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from domain.entities.api_key import ApiKey
from infrastructure.db.repositories import SqlApiKeyRepository


async def _get_session_factory() -> async_sessionmaker:  # type: ignore[type-arg]
    from config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


async def cmd_create(client: str, scopes: list[str], expires: str | None) -> None:
    expires_at: datetime | None = None
    if expires:
        expires_at = datetime.fromisoformat(expires)

    entity, raw_key = ApiKey.generate(client_name=client, scopes=scopes, expires_at=expires_at)

    factory = await _get_session_factory()
    async with factory() as session:
        repo = SqlApiKeyRepository(session)
        await repo.save(entity)

    print()
    print("API Key created successfully.")
    print("=" * 60)
    print("SAVE THIS KEY — it will NOT be shown again.")
    print()
    print(f"  Key ID      : {entity.id}")
    print(f"  Client name : {entity.client_name}")
    print(f"  Scopes      : {', '.join(entity.scopes)}")
    print(f"  Expires at  : {entity.expires_at or 'never'}")
    print()
    print(f"  API Key: {raw_key}")
    print("=" * 60)
    print()


async def cmd_revoke(key_id: str) -> None:
    factory = await _get_session_factory()
    async with factory() as session:
        repo = SqlApiKeyRepository(session)
        await repo.revoke(key_id)
    print(f"Key {key_id!r} has been revoked.")


async def cmd_list() -> None:
    factory = await _get_session_factory()
    async with factory() as session:
        repo = SqlApiKeyRepository(session)
        keys = await repo.list_all()

    if not keys:
        print("No API keys found.")
        return

    print(f"\n{'ID':<36}  {'Client':<20}  {'Active':<6}  {'Scopes':<30}  Expires")
    print("-" * 100)
    for k in keys:
        scopes_str = ", ".join(k.scopes) if k.scopes else "(none)"
        expires_str = k.expires_at.isoformat() if k.expires_at else "never"
        print(f"{k.id:<36}  {k.client_name:<20}  {str(k.active):<6}  {scopes_str:<30}  {expires_str}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Opportunity Radar API keys")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("--client", required=True, help="Client name (e.g. propflow)")
    create_parser.add_argument(
        "--scopes",
        required=True,
        help="Comma-separated scopes (e.g. read:opportunities)",
    )
    create_parser.add_argument(
        "--expires",
        default=None,
        help="Optional expiry date in ISO format (e.g. 2027-01-01)",
    )

    # revoke
    revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key by ID")
    revoke_parser.add_argument("--key-id", required=True, help="UUID of the key to revoke")

    # list
    subparsers.add_parser("list", help="List all API keys")

    args = parser.parse_args()

    if args.command == "create":
        scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
        asyncio.run(cmd_create(client=args.client, scopes=scopes, expires=args.expires))
    elif args.command == "revoke":
        asyncio.run(cmd_revoke(key_id=args.key_id))
    elif args.command == "list":
        asyncio.run(cmd_list())


if __name__ == "__main__":
    main()
