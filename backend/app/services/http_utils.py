"""硅基流动 HTTP 调用的公共工具：鉴权客户端与带重试的请求。"""

from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 4


def build_client(api_key: str, base_url: str, timeout: float = 60.0) -> httpx.Client:
    if not api_key:
        raise ValueError("缺少硅基流动 API Key，请在 config.ini [siliconflow] api_key 中配置")
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=timeout,
    )


def post_with_retry(
    client: httpx.Client,
    path: str,
    payload: dict,
    max_retries: int = MAX_RETRIES,
) -> dict:
    """POST JSON，对 429 限流与网络错误做退避重试（免费档有速率限制）。"""
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.post(path, json=payload)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = float(min(2 ** attempt, 15))
                logger.warning("硅基流动接口限流（429），%.1f 秒后重试 %s", wait, path)
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            last_error = exc
            logger.warning("硅基流动 %s 第 %d 次请求失败：%s", path, attempt, exc)
            time.sleep(min(2 ** attempt, 15))
    raise RuntimeError(f"硅基流动 {path} 调用失败：{last_error}")
