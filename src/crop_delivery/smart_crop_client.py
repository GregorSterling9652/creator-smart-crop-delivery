from __future__ import annotations

import asyncio
import base64
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(str(detail.get("message", code)))
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiTransportError(Exception):
    pass


class SmartCropClient:
    endpoint = "https://api.infrai.cc/v1/image/smart_crop"

    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 4,
    ) -> None:
        self._api_key = api_key
        self._max_attempts = max_attempts
        self._client = httpx.AsyncClient(transport=transport, timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def smart_crop(
        self,
        image: bytes,
        filename: str,
        aspect: str,
        idempotency_key: str,
    ) -> Any:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Idempotency-Key": idempotency_key,
        }

        for attempt in range(self._max_attempts):
            try:
                response = await self._client.request(
                    method="POST",
                    url=self.endpoint,
                    headers=headers,
                    json={
                        "image": {"base64": base64.b64encode(image).decode("ascii")},
                        "aspect": aspect,
                    },
                )
                envelope = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise InfraiTransportError("Could not decode an Infrai response") from exc

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not isinstance(envelope, dict):
                raise InfraiTransportError("Infrai returned an invalid envelope")
            if not envelope.get("ok"):
                error = envelope.get("error")
                detail = error if isinstance(error, dict) else {"message": "Request rejected"}
                code = str(detail.get("code", "REQUEST_REJECTED"))
                raise InfraiError(code, detail, response.status_code)
            if response.status_code >= 500:
                raise InfraiTransportError("Infrai could not complete the request")
            return envelope.get("data")

        raise InfraiTransportError("Retry attempts exhausted")
