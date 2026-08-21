"""独立的知识导入脚本。

用法（在 backend 目录下，激活 venv 后）：
    python -m scripts.sync_knowledge
"""

from __future__ import annotations

import logging
import sys

from app.core.config import load_settings
from app.core.database import create_db_engine, init_db
from app.core.logging import setup_logging
from app.services.embedding import SiliconFlowEmbedder
from app.services.importer import sync_knowledge
from app.services.milvus_store import MilvusVectorStore

logger = logging.getLogger(__name__)


def main() -> int:
    settings = load_settings()
    setup_logging(settings.debug)

    engine = create_db_engine(settings)
    init_db(engine)

    embedder = SiliconFlowEmbedder(
        api_key=settings.sf_api_key,
        model=settings.embedding_model,
        base_url=settings.sf_base_url,
        batch_size=settings.embedding_batch_size,
        batch_sleep=settings.batch_sleep,
        timeout=settings.sf_timeout,
    )
    settings.milvus_db_path.parent.mkdir(parents=True, exist_ok=True)
    vector_store = MilvusVectorStore(
        db_path=str(settings.milvus_db_path),
        collection_name=settings.collection_name,
        dim=settings.embedding_dim,
    )

    try:
        sync_knowledge(settings, engine, vector_store, embedder)
    finally:
        vector_store.close()
        embedder.close()
        engine.dispose()
    logger.info("导入完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
