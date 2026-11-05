# FORM — upper-body muscle identification MVP

FORM accepts exactly two photos for one browser session: a front-facing and a
back-facing upper-body photo. It is an anatomy identification tool, not a
progress tracker.

```text
front + back photos
  -> Pillow validation and normalization
  -> local MediaPipe pose detection
  -> separate front/back candidate regions
  -> one Muse Spark 1.3 Responses request
  -> bounded grounding correction constrained by pose geometry
  -> interactive SVG anatomy map
```

## Privacy and storage

Uploaded photo bytes are processed in the request and are not written to disk,
a database, or server session storage. The browser holds temporary object URLs
while the result is visible. Refreshing or closing the page discards the UI
session. The only persisted backend state is `api_usage.json`, which contains a
request count and no photo or model content.

## Supported candidates

Front: bilateral pectoralis major, anterior and lateral deltoids, biceps
brachii, external oblique/serratus areas, and rectus abdominis.

Back: trapezius, bilateral rhomboids, latissimus dorsi, posterior deltoids,
triceps brachii, and an estimated erector-spinae location.

Muse classifies each candidate as visible surface anatomy, an estimated deeper
location, or not meaningfully locatable. The last category is omitted from the
map. Muse grounding points use Meta's normalized 0–1000 coordinate system.
They apply a bounded placement correction to MediaPipe-anchored templates but
never become muscle outlines. Deeper muscles render as compact dashed estimated
locations rather than surface polygons.

The diagnostic result preserves three independently toggleable layers:

- blue: the unmodified MediaPipe anatomical template;
- green: Muse's raw point, documented bounding box, and any experimental
  perimeter samples;
- orange: the final pose-constrained generated outline.

Bounding boxes and single points are documented Muse perception-grounding
modes. Ordered `boundary_points` are an experimental structured prompt and are
shown for evaluation only; they are not treated as segmentation ground truth.

Preprocessing EXIF-corrects each image and letterboxes it onto a square
inference canvas. The recorded transform maps MediaPipe and Muse coordinates
back to the source photo without stretching the body.

For local coordinate diagnostics only, set `ANNOTATION_DEBUG_DIR` to an
absolute directory. The backend writes JSON containing transforms, landmarks,
candidate regions, and structured model output. It never writes photo bytes.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
cd web
npm install
```

Create `backend/.env`:

```dotenv
MODEL_API_KEY=your_real_server_side_key
MODEL_API_BASE_URL=https://api.meta.ai/v1
MODEL_API_MODEL=muse-spark-1.3
META_API_ENABLED=false
META_API_TOTAL_LIMIT=1
CORS_ORIGINS=http://localhost:3000
```

Keep `META_API_ENABLED=false` until explicitly authorizing a paid request.

## One-request localization evaluation

After explicit authorization, use a fresh local counter directory so the test
is isolated, set `META_API_ENABLED=true`, and keep `META_API_TOTAL_LIMIT=1`:

```dotenv
META_API_ENABLED=true
META_API_TOTAL_LIMIT=1
STORAGE_DIR=C:/absolute/path/to/one-live-localization-test
```

Restart the backend, upload exactly one front/back pair once, and compare the
green layer against the blue template and orange result. Do not resubmit after
an error: automatic SDK retries remain disabled. Save opt-in debug JSON if
needed, then return `META_API_ENABLED=false`.

Start the services from separate terminals:

```powershell
python -m uvicorn app:app --app-dir backend --env-file backend/.env --reload --port 8000
```

```powershell
cd web
$env:NEXT_PUBLIC_API_BASE = "http://localhost:8000"
npm run dev
```

Open `http://localhost:3000`, select the two required views, and submit once.

## Tests

```powershell
python -m pytest backend/tests -q
cd web
npm test
npm run build
```

Tests use mocked Muse responses and isolated request counters. They do not make
paid API calls.

## Vercel deployment assessment

Vercel officially supports FastAPI through its Python Functions runtime, so the
current service can be evaluated without an immediate rewrite. However,
MediaPipe's native dependency size and cold-start behavior must be measured in a
preview deployment.

A Next.js Route Handler is a good future home for the small credential-protected
Muse proxy, request schema validation, and safety limit. It should not replace
the Python service until pose detection moves either to MediaPipe Tasks in the
browser or to a separately measured Python function. The current no-storage POST
contract already fits that migration: the server returns annotations and text in
the same response and retains no photos.

## Known limitations

- MediaPipe landmarks anchor broad anatomical approximations, not boundaries.
- Front/back validation uses the explicit upload slots plus Muse's semantic view
  confirmation. Shoulder handedness is used only to report likely mirroring;
  MediaPipe alone cannot reliably distinguish a back from a mirrored front.
- Clothing, crop, rotation, arm position, and lighting can hide candidates.
- Rhomboids and other covered anatomy can only be estimated, not observed as a
  surface outline.
- Muse grounding can correct placement only within conservative pose bounds;
  it cannot recover precise muscle boundaries from a single point.
- No SAM, segmentation model, training, fine-tuning, recommendations, accounts,
  database, or progress tracking is included.
