"""SQLite / SQLModel 数据库初始化。"""

from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Settings


def create_db_engine(settings: Settings):
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{settings.sqlite_path.as_posix()}",
        echo=False,
        connect_args={"check_same_thread": False},
    )


def init_db(engine) -> None:
    # 确保所有表模型已注册到 SQLModel.metadata
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def new_session(engine) -> Session:
    return Session(engine)
