# Adding a New Lambda

Follow this checklist whenever a new domain requires its own Lambda.

## 1. Backend: handler module

Create `backend/src/<domain>/handler.py` with this structure:

```python
import json
import os
from datetime import UTC, datetime
from typing import cast

from session_guard import CORS_HEADERS, require_session
from auth import VerificationError

# Read env + build clients at module level (warm reuse)
_SECRET = os.environ["SESSION_SECRET"]
# ... other env vars and boto3 clients

def handler(event: dict[str, object], context: object) -> dict[str, object]:
    now_utc = int(datetime.now(UTC).timestamp())
    raw_headers = cast(dict[str, str], event.get("headers") or {})
    method = str(event.get("requestContext", {}).get("http", {}).get("method", ""))  # type: ignore[union-attr]
    raw_path = str(event.get("rawPath", ""))
    try:
        claims = require_session(raw_headers, _SECRET, now_utc)
    except VerificationError as e:
        return {"statusCode": 401, "headers": CORS_HEADERS, "body": json.dumps({"error": str(e)})}
    # route on (method, raw_path) ...
    return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
```

Rules:
- No imports from other handler modules
- `session_guard` and `auth` come from the Lambda Layer — import them as top-level modules
- 404 catch-all at the bottom of the handler

## 2. Backend: dev server routes

Add matching FastAPI routes to `backend/src/dev/server.py`:

```python
@app.get("/<domain>/...")
async def my_route(request: Request) -> JSONResponse:
    ...
```

The dev server uses an in-memory store or a real local DynamoDB where needed.

## 3. Terraform: new Lambda + Function URL

In `deploy/modules/lambda/main.tf`, add:

```hcl
resource "aws_lambda_function" "<domain>_handler" {
  function_name    = "${var.project_name}-<domain>-handler"
  role             = aws_iam_role.this.arn
  handler          = "<domain>.handler.handler"   # or auth_handler.handler for flat modules
  runtime          = "python3.12"
  filename         = var.<domain>_zip_path
  source_code_hash = filebase64sha256(var.<domain>_zip_path)
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      SESSION_SECRET = var.session_secret
      # domain-specific vars ...
    }
  }
}

resource "aws_lambda_function_url" "<domain>_handler" {
  function_name      = aws_lambda_function.<domain>_handler.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE"]
    allow_headers     = ["content-type", "authorization"]
    max_age           = 86400
  }
}
```

## 4. Terraform: Lambda Layer

The shared layer is defined once and referenced by all Lambdas:

```hcl
resource "aws_lambda_layer_version" "shared" {
  layer_name          = "${var.project_name}-shared"
  filename            = var.layer_zip_path
  source_code_hash    = filebase64sha256(var.layer_zip_path)
  compatible_runtimes = ["python3.12"]
}
```

## 5. Terraform: CloudFront behavior

Add an ordered cache behavior for the new domain's path prefix **before** the default behavior:

```hcl
ordered_cache_behavior {
  path_pattern     = "/<domain>*"
  target_origin_id = "<domain>-handler"
  # ... viewer_protocol_policy, cache settings, allowed_methods
}
```

And add the corresponding origin:

```hcl
origin {
  domain_name = replace(aws_lambda_function_url.<domain>_handler.function_url, "https://", "")
  origin_id   = "<domain>-handler"
  custom_origin_config { ... }
}
```

## 6. Update CLAUDE.md

Add the new handler to the File Map under Backend.
