# FORM — upper-body muscle vision MVP

A single-photo baseline pipeline for approximate upper-back muscle annotations:

```text
photo upload -> Pillow preprocessing -> MediaPipe Pose -> landmark polygons
             -> one Meta vision request -> saved JSON -> SVG photo overlay
```

The current back-view regions are trapezius, left/right rhomboids, left/right
latissimus dorsi, and left/right posterior deltoids. The polygons are geometric
approximations derived from pose landmarks, not muscle segmentation.

## Safety and cost controls

- `META_API_ENABLED=false` by default. No model request can be sent until this is
  explicitly changed.
- One uploaded image produces one request containing the image and every muscle.
- The adapter uses an HTTP transport with zero retries.
- `META_API_TOTAL_LIMIT=1` is a persistent, server-wide testing allowance stored
  in `backend/storage/api_usage.json`.
- The allowance is reserved before the request. A failed request consumes it and
  is not retried.
- Results and the raw provider response are saved. Opening a result again only
  reads `result.json` and never invokes the model.

The local preflight verifies that inference is enabled, a server-side key is
present, the endpoint is HTTPS, and the configured model name is image-capable
Llama. Credential validity and provider access can only be proven by the single
inference request itself; a separate network validation call would violate the
one-request cap.

## Saved artifacts

Each successful analysis is stored under:

```text
backend/storage/analyses/<analysis_id>/
  original.jpg
  preprocessed.jpg
  annotations.json
  model_response.json
  result.json
```

## Local setup

Use Python 3.11+ and Node.js 20+.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
cd web
npm install
```

Copy `.env.example` values into your server environment. Keep `META_API_ENABLED`
set to `false` until the paid request is authorized. The integration uses Meta's
Responses API at `https://api.meta.ai/v1/responses` through the OpenAI Python SDK.

Start the backend from the repository root:

```powershell
python -m uvicorn app:app --app-dir backend --reload --port 8000
```

Start the frontend in another terminal:

```powershell
cd web
$env:NEXT_PUBLIC_API_BASE = "http://localhost:8000"
npm run dev
```

## Tests

```powershell
python -m pytest backend/tests -q
cd web
npm test
npm run build
```

Tests inject a fake model adapter. They do not contact Meta.

## Two-photo comparison

Open `http://localhost:3000/compare` to select a baseline and current back photo.
Both photos are processed locally with MediaPipe, then included in one ordered
Muse Spark Responses request. Saved comparison artifacts live under:

```text
backend/storage/comparisons/<comparison_id>/
```

The API allowance is cumulative. If the existing single-photo test already used
request 1 of 1, a manually authorized comparison requires increasing
`META_API_TOTAL_LIMIT` to `2` and restarting the backend. Do this only when you
intend to authorize that additional paid request. Automated tests use isolated
temporary storage and mocked model responses.

## Enabling the first authorized baseline request

Only after explicit authorization, configure the backend process:

```powershell
$env:META_API_ENABLED = "true"
$env:MODEL_API_KEY = "..."
$env:MODEL_API_BASE_URL = "https://api.meta.ai/v1"
$env:MODEL_API_MODEL = "muse-spark-1.3"
$env:META_API_TOTAL_LIMIT = "1"
```

Then upload exactly one clear, straight-on upper-body back photo through the UI.
Do not delete `api_usage.json` to bypass the configured testing allowance.

