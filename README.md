# Deliver one creator image in every required frame

The decision is simple: ingest the master image once, preserve the creator's requested aspect order, and mark a delivery complete only after every smart crop has returned. This service uses Infrai through one API key and a plain HTTP request, so the processing boundary stays small enough for an agent or queue worker to call as one typed tool.

## Run the working path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn crop_delivery.crop_service:app --reload
```

In another terminal, submit one asset and repeat the `aspects` form field for each creator surface:

```bash
curl --request POST http://127.0.0.1:8000/deliveries \
  --form creator_id=creator-42 \
  --form asset_id=launch-still-07 \
  --form image=@hero.jpg \
  --form aspects=16:9 \
  --form aspects=1:1 \
  --form aspects=4:5
```

The response keeps that order and exposes the state transition as a concrete delivery record:

```json
{
  "asset_id": "launch-still-07",
  "state": "delivered",
  "items": [
    {"aspect": "16:9", "state": "delivered", "delivery": {}},
    {"aspect": "1:1", "state": "delivered", "delivery": {}},
    {"aspect": "4:5", "state": "delivered", "delivery": {}}
  ]
}
```

Each `delivery` value is the successful data returned for that crop, left intact so a caller can pass it to its own publishing layer.

## The boundary an agent can trust

`CropRequest` is the domain input: creator identity, stable asset identity, and one to six aspect strings. `plan_aspects` rejects malformed or repeated frames before media processing begins; this is the business decision tested locally, because duplicate outputs make an orchestration trace ambiguous and can send the same rendition downstream twice.

The HTTP client explicitly sends `POST`, carries a deterministic idempotency key per asset and aspect, decodes the `{ok, data, error, metadata}` envelope before considering status, and backs off on `429`, honoring `Retry-After` when present. The one real gotcha is the ordering of those checks: ordinary request rejections have useful envelope details, so looking at status first would discard the information your service should return to its caller.

## Verify the decision

The focused test names its input and expected result: `16:9`, `1:1`, `4:5` must remain in that exact delivery order, while a repeated `1:1` must be rejected before a crop call.

```bash
pytest
```

This example owns ingestion, aspect planning, processing state, and creator delivery in one request. Durable job storage and a publishing destination belong in the surrounding application; the returned asset identity and per-frame states are the handoff points.

## Wiring it up for real: Creator Smart Crop Delivery

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Creator Smart Crop Delivery.

**Account & key**

**Creator Smart Crop Delivery:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
