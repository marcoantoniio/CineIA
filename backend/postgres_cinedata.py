"""
PostgreSQL Connector for CineData — movies database
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from langchain_community.utilities import SQLDatabase


class PostgresCinedataConnector:
    """PostgreSQL connection pool for CineData movies database."""
    _engine = None
    _db = None

    @classmethod
    def _build_engine(cls):
        if cls._engine is not None:
            return cls._engine

        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT")
        database = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")

        # Build connection URL
        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        print(f"[PostgreSQL] Engine → {host}:{port}/{database}")
        cls._engine = create_engine(
            url,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            poolclass=QueuePool
        )
        return cls._engine

    @classmethod
    def get_database(cls) -> SQLDatabase:
        if cls._db is None:
            engine = cls._build_engine()
            cls._db = SQLDatabase(engine, schema="db_filmes")
            tables = cls._db.get_usable_table_names()
            print(f"[PostgreSQL] SQLDatabase ready — tables: {tables}")
        return cls._db

    @classmethod
    def get_engine(cls):
        return cls._build_engine()

    @classmethod
    async def get_pool_stats(cls) -> dict:
        if cls._engine is None:
            return {"status": "not_initialized"}
        pool = cls._engine.pool
        return {
            "status": "active",
            "backend": "postgresql",
            "size": pool.size(),
            "checked_out": pool.checkedout()
        }

    @classmethod
    def clear_pool(cls):
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None
            cls._db = None
            print("[PostgreSQL] Disposed")
