"""配置加载模块。

所有配置集中在 backend/config.ini，本文件负责解析并提供带默认值的
Settings 对象。相对路径统一以 backend/ 目录为基准解析。
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

# backend/ 目录（app/core/config.py -> app/core -> app -> backend）
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = BACKEND_ROOT / "config.ini"


@dataclass(frozen=True)
class Settings:
    # [app]
    title: str = "个人博客"
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    cors_origins: tuple[str, ...] = ()

    # [database] / [milvus]
    sqlite_path: Path = BACKEND_ROOT / "data" / "blog.db"
    milvus_db_path: Path = BACKEND_ROOT / "data" / "milvus.db"
    collection_name: str = "blog_chunks"
    embedding_dim: int = 1024

    # [content]
    posts_dir: Path = BACKEND_ROOT.parent / "content" / "posts"
    documents_dir: Path = BACKEND_ROOT.parent / "content" / "documents"
    about_file: Path = BACKEND_ROOT.parent / "content" / "about.md"

    # [import]
    chunk_size: int = 600
    similarity_drop: float = 0.15
    embedding_batch_size: int = 16
    batch_sleep: float = 0.5

    # [retrieval]
    top_k: int = 10
    rerank_top_n: int = 4

    # [siliconflow]
    sf_api_key: str = ""
    sf_base_url: str = "https://api.siliconflow.cn"
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    sf_timeout: float = 60.0

    # [openai]
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.3


def _resolve_path(raw: str) -> Path:
    path = Path(raw.strip())
    return path if path.is_absolute() else (BACKEND_ROOT / path)


def _split_origins(raw: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def load_settings(config_path: Path | None = None) -> Settings:
    path = config_path or DEFAULT_CONFIG_PATH
    parser = configparser.ConfigParser()
    if not parser.read(path, encoding="utf-8"):
        raise FileNotFoundError(
            f"未找到配置文件 {path}。请复制 config.example.ini 为 config.ini 并填写配置。"
        )

    def get(section: str, option: str, fallback: str = "") -> str:
        return parser.get(section, option, fallback=fallback).strip()

    return Settings(
        title=get("app", "title", "个人博客"),
        host=get("app", "host", "127.0.0.1"),
        port=parser.getint("app", "port", fallback=8000),
        debug=parser.getboolean("app", "debug", fallback=False),
        cors_origins=_split_origins(get("app", "cors_origins")),
        sqlite_path=_resolve_path(get("database", "sqlite_path", "data/blog.db")),
        milvus_db_path=_resolve_path(get("milvus", "db_path", "data/milvus.db")),
        collection_name=get("milvus", "collection", "blog_chunks"),
        embedding_dim=parser.getint("milvus", "embedding_dim", fallback=1024),
        posts_dir=_resolve_path(get("content", "posts_dir", "../content/posts")),
        documents_dir=_resolve_path(get("content", "documents_dir", "../content/documents")),
        about_file=_resolve_path(get("content", "about_file", "../content/about.md")),
        chunk_size=parser.getint("import", "chunk_size", fallback=600),
        similarity_drop=parser.getfloat("import", "similarity_drop", fallback=0.15),
        embedding_batch_size=parser.getint("import", "embedding_batch_size", fallback=16),
        batch_sleep=parser.getfloat("import", "batch_sleep", fallback=0.5),
        top_k=parser.getint("retrieval", "top_k", fallback=10),
        rerank_top_n=parser.getint("retrieval", "rerank_top_n", fallback=4),
        sf_api_key=get("siliconflow", "api_key"),
        sf_base_url=get("siliconflow", "base_url", "https://api.siliconflow.cn"),
        embedding_model=get("siliconflow", "embedding_model", "BAAI/bge-m3"),
        reranker_model=get("siliconflow", "reranker_model", "BAAI/bge-reranker-v2-m3"),
        sf_timeout=parser.getfloat("siliconflow", "timeout", fallback=60.0),
        openai_api_key=get("openai", "api_key"),
        openai_base_url=get("openai", "base_url", "https://api.openai.com/v1"),
        llm_model=get("openai", "model", "gpt-4o-mini"),
        llm_temperature=parser.getfloat("openai", "temperature", fallback=0.3),
    )
