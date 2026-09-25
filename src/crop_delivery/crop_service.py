from __future__ import annotations

import hashlib
import os
from enum import StrEnum
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .smart_crop_client import InfraiError, InfraiTransportError, SmartCropClient


class JobState(StrEnum):
    PROCESSING = "processing"
    DELIVERED = "delivered"


class CropRequest(BaseModel):
    creator_id: str = Field(min_length=1, max_length=80)
    asset_id: str = Field(min_length=1, max_length=80)
    aspects: list[str] = Field(min_length=1, max_length=6)


class CropItem(BaseModel):
    aspect: str
    state: JobState
    delivery: Any | None = None


class CropDelivery(BaseModel):
    asset_id: str
    state: JobState
    items: list[CropItem]


def plan_aspects(aspects: list[str]) -> list[str]:
    planned: list[str] = []
    for raw_aspect in aspects:
        aspect = raw_aspect.strip()
        parts = aspect.split(":")
        if len(parts) != 2 or not all(part.isdigit() and int(part) > 0 for part in parts):
            raise ValueError(f"Invalid aspect: {raw_aspect}")
        if aspect in planned:
            raise ValueError(f"Duplicate aspect: {aspect}")
        planned.append(aspect)
    return planned


app = FastAPI(title="Creator smart-crop delivery")


@app.post("/deliveries", response_model=CropDelivery)
async def create_delivery(
    image: Annotated[UploadFile, File()],
    creator_id: Annotated[str, Form()],
    asset_id: Annotated[str, Form()],
    aspects: Annotated[list[str], Form()],
) -> CropDelivery:
    try:
        request = CropRequest(creator_id=creator_id, asset_id=asset_id, aspects=aspects)
        planned = plan_aspects(request.aspects)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")

    content = await image.read()
    if not content:
        raise HTTPException(status_code=422, detail="The image is empty")

    client = SmartCropClient(api_key)
    items = [CropItem(aspect=aspect, state=JobState.PROCESSING) for aspect in planned]
    try:
        for item in items:
            identity = f"{request.creator_id}:{request.asset_id}:{item.aspect}"
            request_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            item.delivery = await client.smart_crop(
                content,
                image.filename or "creator-image",
                item.aspect,
                request_key,
            )
            item.state = JobState.DELIVERED
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
    except InfraiTransportError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await client.close()

    return CropDelivery(asset_id=request.asset_id, state=JobState.DELIVERED, items=items)
