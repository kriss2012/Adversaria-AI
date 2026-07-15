"""
adversaria/services/pubsub.py — Unified Pub/Sub and Caching interface.

Provides fallback to in-memory queues and dictionaries when Redis is not available or configured.
Essential for running in resource-constrained or free-tier environments like Render.
"""
from __future__ import annotations

import asyncio
import json
import redis.asyncio as aioredis
from typing import Any, AsyncGenerator

from adversaria.config import get_settings

_settings = get_settings()

class InMemPubSub:
    """In-memory pub/sub manager for single-process environments."""
    def __init__(self) -> None:
        self._listeners: dict[str, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str) -> asyncio.Queue:
        async with self._lock:
            queue = asyncio.Queue()
            if channel not in self._listeners:
                self._listeners[channel] = set()
            self._listeners[channel].add(queue)
            return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            if channel in self._listeners:
                self._listeners[channel].discard(queue)
                if not self._listeners[channel]:
                    del self._listeners[channel]

    async def publish(self, channel: str, message: str) -> None:
        async with self._lock:
            if channel in self._listeners:
                for queue in list(self._listeners[channel]):
                    await queue.put(message)

_in_mem_pubsub = InMemPubSub()
_in_mem_cache: dict[str, str] = {}


async def publish_message(channel: str, data: dict[str, Any]) -> None:
    """Publish a JSON payload to a channel (Redis or In-memory)."""
    message = json.dumps(data)
    if _settings.redis_url:
        try:
            redis_client = aioredis.from_url(_settings.redis_url)
            await redis_client.publish(channel, message)
            await redis_client.aclose()
            return
        except Exception:
            # Fallback to in-memory if Redis fails
            pass
    await _in_mem_pubsub.publish(channel, message)


async def subscribe_channel(channel: str) -> AsyncGenerator[str, None]:
    """Subscribe to a channel and yield messages (Redis or In-memory)."""
    if _settings.redis_url:
        try:
            redis_client = aioredis.from_url(_settings.redis_url)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        yield message["data"].decode()
            finally:
                await pubsub.unsubscribe(channel)
                await redis_client.aclose()
            return
        except Exception:
            # Fallback to in-memory if Redis fails
            pass

    queue = await _in_mem_pubsub.subscribe(channel)
    try:
        while True:
            msg = await queue.get()
            yield msg
    finally:
        await _in_mem_pubsub.unsubscribe(channel, queue)


async def set_cache(key: str, value: Any, expire: int = 3600) -> None:
    """Set cache key with expiration (Redis or In-memory)."""
    payload = json.dumps(value)
    if _settings.redis_url:
        try:
            redis_client = aioredis.from_url(_settings.redis_url)
            await redis_client.setex(key, expire, payload)
            await redis_client.aclose()
            return
        except Exception:
            pass
    _in_mem_cache[key] = payload


async def get_cache(key: str) -> Any | None:
    """Retrieve cache key (Redis or In-memory)."""
    if _settings.redis_url:
        try:
            redis_client = aioredis.from_url(_settings.redis_url)
            val = await redis_client.get(key)
            await redis_client.aclose()
            if val:
                return json.loads(val)
        except Exception:
            pass
    val = _in_mem_cache.get(key)
    if val:
        return json.loads(val)
    return None
