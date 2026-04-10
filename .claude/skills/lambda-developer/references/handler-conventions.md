# Handler Conventions

## CORS headers

Always use `CORS_HEADERS` from `session_guard` (imported from the Lambda Layer).
Every response — including errors — must include these headers.

```python
from session_guard import CORS_HEADERS, require_session

return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "bad request"})}
```

Never define `CORS_HEADERS` locally inside a handler module.

## Session guard

`require_session` raises `VerificationError` if the token is missing, malformed, or expired.
Catch it at the top of `handler()` and return 401 immediately:

```python
try:
    claims = require_session(raw_headers, _SECRET, now_utc)
except VerificationError as e:
    return {"statusCode": 401, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
```

For endpoints that don't require auth (e.g. `POST /auth/session`), skip this.

## Response shape

Always return a dict with `statusCode`, `headers`, and `body` (JSON string):

```python
{"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"key": "value"})}
```

## Routing inside a handler

Route on `(method, raw_path)`:

```python
method = str(event.get("requestContext", {}).get("http", {}).get("method", ""))  # type: ignore[union-attr]
raw_path = str(event.get("rawPath", ""))

if method == "GET" and raw_path == "/profile":
    ...
elif method == "PUT" and raw_path == "/profile":
    ...
else:
    return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
```

CloudFront only routes matching prefixes to this Lambda, so the 404 branch is only hit for unexpected sub-paths.

## Module-level warm initialisation

Env vars and boto3 clients are read once at module load and reused across invocations:

```python
_SECRET = os.environ["SESSION_SECRET"]
_TABLE = boto3.resource("dynamodb").Table(os.environ["PROFILES_TABLE_NAME"])
```

## Lambda Layer imports

The layer is mounted at `/opt/python/`. Import shared modules as top-level:

```python
from auth import SessionClaims, VerificationError, verify_session_token
from session_guard import CORS_HEADERS, require_session
```

Do **not** use relative imports or package prefixes for layer modules.

## Packaging

Each Lambda is zipped separately. The zip contains the handler module tree only.
The shared layer (`auth.py`, `session_guard.py`) is **not** included in the Lambda zips — it is provided by the layer.

Build layout (example for profile):
```
profile_handler.zip
└── profile/
    ├── __init__.py
    ├── domain.py
    ├── handler.py
    ├── repository.py
    └── tags.py
```
