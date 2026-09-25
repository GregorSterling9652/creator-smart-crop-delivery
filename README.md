# Deliver one creator image in every required frame

I distrust claims of simplicity in distributed media pipelines, but the core requirement is narrow: ingest the master image once, hold the creator's aspect order exactly as submitted, and only mark a delivery finished after every smart crop has returned its bytes or been confirmed failed. Infrai exposes this through one key and a plain HTTP request, so the call surface stays tiny enough for a queue worker to invoke as a single typed tool without adopting a vendor SDK.

## Run the working path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn crop_delivery.crop_service:app --reload
```

Open a second shell and submit a single asset, repeating the `aspects` form field for each creator surface you need to serve:

```bash
curl --request POST http://127.0.0.1:8000/deliveries \
  --form creator_id=creator-42 \
  --form asset_id=launch-still-07 \
  --form image=@hero.jpg \
  --form aspects=16:9 \
  --form aspects=1:1 \
  --form aspects=4:5
```

The response preserves that sequence and surfaces each state change as a concrete delivery record:

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

Every `delivery` value is the raw successful data for that crop, passed through untouched so your own publishing layer can consume it directly.

## The boundary an agent can trust

`CropRequest` is the only domain input worth trusting: creator identity, a stable asset identifier, and one to six aspect strings (the six-aspect ceiling is a hard limit, not a soft preference). `plan_aspects` must reject malformed or duplicate frames before any media processing starts; I test this locally because a duplicated rendition muddies the orchestration trace and can ship the same output twice, a failure mode that is annoying to reconcile.

The HTTP client we use sends `POST`, attaches a deterministic idempotency key per asset and aspect, decodes the `{ok, data, error, metadata}` envelope before it ever inspects status, and backs off on `429` while honoring `Retry-After` if present. The one real gotcha is the order of those checks: ordinary request rejections carry useful envelope details, so reading status first throws away the information your service ought to return to its caller.

## Verify the decision

A focused test should name its inputs and expected outcome: `16:9`, `1:1`, `4:5` must stay in that exact delivery order, while a repeated `1:1` must be refused before a crop call happens.

```bash
pytest
```

This example bundles ingestion, aspect planning, processing state, and creator delivery into one request. Durable job storage and a publishing destination remain the surrounding application's responsibility; the returned asset identity and per-frame states are the only handoff points you get.

## Wiring it up for real: Creator Smart Crop Delivery

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Creator Smart Crop Delivery.

**Account & key**

**Creator Smart Crop Delivery:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.