import asyncio

import httpx

import config


HEADERS = {"Authorization": f"Api-Key {config.BOT_API_KEY}"}
_client: httpx.AsyncClient | None = None


class RetryingAsyncClient(httpx.AsyncClient):
    async def request(self, method, url, *args, **kwargs):
        method = method.upper()
        attempts = 3 if method == "GET" else 1
        for attempt in range(attempts):
            try:
                response = await super().request(method, url, *args, **kwargs)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt + 1 >= attempts:
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            if response.status_code not in {502, 503, 504} or attempt + 1 >= attempts:
                return response
            await asyncio.sleep(0.5 * (attempt + 1))
        raise RuntimeError("HTTP request retry loop exited unexpectedly.")


def _get_client() -> RetryingAsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = RetryingAsyncClient(base_url=config.BACKEND_URL, timeout=30)
    return _client


class _ClientContext:
    async def __aenter__(self):
        return _get_client()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


def client_context():
    return _ClientContext()


async def close():
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
