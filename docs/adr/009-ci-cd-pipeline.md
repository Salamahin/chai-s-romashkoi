# CI/CD Pipeline

Date: 2026-04-14
Status: Proposed

## Context

The project has no automated pipeline. All deployments are performed manually: a developer runs Terraform locally, builds Lambda zips by hand, and uploads frontend assets. This creates two problems:

1. There is no safety net — broken Python code or failing Playwright tests can be merged and deployed.
2. There is no reproducible deployment record — state drift between developer machines is possible.

The requirement is three GitHub Actions workflows:

- **ci** — runs on every push/PR; executes linters, type checks, and unit tests.
- **e2e** — runs on every push/PR; starts the dev backend + frontend and runs Playwright tests.
- **cd** — runs on push to `main`; packages Lambdas, runs `terraform apply`, builds the frontend, and invalidates the CloudFront cache.

An additional one-time bootstrap step provisions the S3 bucket and DynamoDB table that store Terraform remote state. This is a separate Terraform root module (`deploy/bootstrap/`) run once by a human, not by the pipeline.

Constraints:
- Near-zero AWS cost must be preserved.
- No existing IAM user or role — setup instructions must be written for a human to follow.
- Google OAuth secrets for CD are real values; CI and e2e use the dev server which bypasses OAuth.

## Architecture

### Components

| Component | Responsibility |
|---|---|
| `.github/workflows/ci.yml` | Install Python deps, run ruff + mypy + pytest on every push/PR |
| `.github/workflows/e2e.yml` | Start dev backend + frontend, run Playwright suite on every push/PR |
| `.github/workflows/cd.yml` | Package Lambdas, `terraform apply`, `npm run build`, sync S3, invalidate CloudFront |
| `deploy/bootstrap/` | One-time Terraform root module: S3 state bucket + DynamoDB lock table |
| `scripts/build_lambdas.sh` | Reproducible Lambda packaging: `uv export` → `pip install -t` → `zip` |
| `deploy/main.tf` (modified) | Add S3 remote backend block pointing at the bootstrap-provisioned bucket |
| `deploy/outputs.tf` (modified) | Add `cloudfront_distribution_id` output needed by the CD invalidation step |
| `README.md` (new section) | Step-by-step IAM user setup + GitHub Actions secrets configuration |

### Interfaces

The workflows are shell-level; there are no typed domain interfaces. The build script interface is:

```
scripts/build_lambdas.sh
  Inputs:  none (reads REPO_ROOT from its own location)
  Outputs: dist/layer.zip
           dist/auth.zip
           dist/app.zip
           dist/profile.zip
           dist/relations.zip
           dist/log.zip
  Side effects: writes files under backend/dist/
```

The bootstrap module exposes two outputs consumed only by the human during initial setup:

```
deploy/bootstrap/outputs.tf
  output "state_bucket_name": string   # value to paste into deploy/main.tf backend block
  output "lock_table_name":   string   # value to paste into deploy/main.tf backend block
```

### Data flow

#### ci workflow

```
push / PR
  └─> checkout
        └─> uv sync (with dev deps)
              ├─> ruff check backend/
              ├─> mypy backend/
              └─> pytest backend/tests/
```

#### e2e workflow

```
push / PR
  └─> checkout
        ├─> uv sync (with dev deps)
        ├─> npm ci (frontend/)
        ├─> uv run python -m dev.server &   (port 8000)
        └─> npx playwright test
              └─> vite dev server launched by playwright.config.ts (port 5173)
```

#### cd workflow

```
push to main
  └─> checkout
        ├─> scripts/build_lambdas.sh
        │     ├─> uv export --no-dev → requirements.txt
        │     ├─> pip install -t dist/layer/python/ -r requirements.txt
        │     ├─> zip dist/layer.zip dist/layer/python/
        │     ├─> for each handler group (auth, app, profile, relations, log):
        │     │     zip dist/<name>.zip src/<handler files>
        │     └─> emit paths: dist/layer.zip, dist/auth.zip, ...
        │
        ├─> terraform -chdir=deploy init   (S3 backend, DynamoDB lock)
        ├─> terraform -chdir=deploy apply  (updates Lambdas, emits Function URLs)
        │     env: TF_VAR_google_client_id, TF_VAR_session_secret,
        │          TF_VAR_layer_zip_path=../backend/dist/layer.zip, ...
        │
        ├─> terraform -chdir=deploy output -raw cloudfront_distribution_id → CF_DIST_ID
        ├─> terraform -chdir=deploy output -raw cloudfront_url             → APP_URL
        │
        ├─> npm ci && npm run build   (frontend/, picks up .env.production.local
        │                              written by terraform apply via local_file resource)
        │
        ├─> aws s3 sync frontend/dist/ s3://<frontend-bucket>/ --delete
        └─> aws cloudfront create-invalidation --distribution-id $CF_DIST_ID --paths "/*"
```

### Boundary map

| Side effect | Where it happens |
|---|---|
| GitHub Actions secret injection | Runner environment — values never written to disk |
| AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) | Injected as env vars into the `cd` runner only |
| `pip install` into a temp directory | `scripts/build_lambdas.sh` — boundary before pure zip assembly |
| `terraform apply` (mutates AWS state) | `cd.yml` step, after Lambda zips are built |
| `.env.production.local` file creation | Terraform `local_file` resource inside `deploy/modules/frontend/main.tf` — already exists |
| `npm run build` (reads `.env.production.local`) | `cd.yml` step, after `terraform apply` |
| `aws s3 sync` (uploads assets) | `cd.yml` step, after `npm run build` |
| CloudFront invalidation | `cd.yml` final step |

## Implementation plan

### `infrastructure_engineer`

This agent has all implementation work. No changes are needed from `python_developer` or `frontend_developer`.

#### 1. `deploy/bootstrap/` — one-time state backend provisioner

Create a new Terraform root module at `deploy/bootstrap/` with three files.

`deploy/bootstrap/main.tf`:
- `terraform` block: `required_version >= 1.5`, `required_providers { aws ~> 5.0 }`. No backend block — state is stored locally (this is a one-time run).
- `provider "aws"`: reads `var.aws_region`.
- `resource "aws_s3_bucket" "tf_state"`: bucket name `"${var.project_name}-tf-state"`. Enable versioning (`aws_s3_bucket_versioning`) so previous states can be recovered. Block all public access (`aws_s3_bucket_public_access_block`).
- `resource "aws_s3_bucket_server_side_encryption_configuration" "tf_state"`: AES256.
- `resource "aws_dynamodb_table" "tf_lock"`: name `"${var.project_name}-tf-lock"`, `billing_mode = "PAY_PER_REQUEST"`, `hash_key = "LockID"` (type `S`). Near-zero cost: DynamoDB on-demand with no traffic is free.

`deploy/bootstrap/variables.tf`:
- `variable "aws_region"`: default `"eu-central-1"`.
- `variable "project_name"`: default `"chai-s-romashkoi"`.

`deploy/bootstrap/outputs.tf`:
- `output "state_bucket_name"`: value = `aws_s3_bucket.tf_state.bucket`.
- `output "lock_table_name"`: value = `aws_dynamodb_table.tf_lock.name`.

#### 2. `deploy/main.tf` — add S3 remote backend

Add a `backend "s3"` block inside the existing `terraform {}` block:

```hcl
backend "s3" {
  bucket         = "chai-s-romashkoi-tf-state"
  key            = "prod/terraform.tfstate"
  region         = "eu-central-1"
  dynamodb_table = "chai-s-romashkoi-tf-lock"
  encrypt        = true
}
```

The bucket and table names are hardcoded (not variables) because the backend block does not support variable interpolation in Terraform.

#### 3. `deploy/outputs.tf` — add CloudFront distribution ID

The CD workflow needs the distribution ID (not just the domain name) to call `aws cloudfront create-invalidation`. Add:

```hcl
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID used for cache invalidation"
  value       = module.frontend.cloudfront_distribution_id
}
```

This requires a matching output in `deploy/modules/frontend/outputs.tf`:

```hcl
output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.this.id
}
```

#### 4. `scripts/build_lambdas.sh` — Lambda packaging

Create `scripts/build_lambdas.sh` as an executable bash script. Logic:

```
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"
DIST="$BACKEND/dist"

rm -rf "$DIST" && mkdir -p "$DIST"

# --- Shared layer ---
# Export only production deps (no dev group) to a requirements file.
# uv export writes a pip-compatible requirements.txt.
cd "$BACKEND"
uv export --no-dev --no-emit-project -o "$DIST/requirements.txt"

LAYER_DIR="$DIST/layer/python"
mkdir -p "$LAYER_DIR"
pip install --quiet -t "$LAYER_DIR" -r "$DIST/requirements.txt"

cd "$DIST/layer"
zip -qr "$DIST/layer.zip" python/
cd "$REPO_ROOT"

# --- auth handler ---
# auth_handler.py lives at src/auth_handler.py and imports from the layer.
cd "$BACKEND/src"
zip -qj "$DIST/auth.zip" auth_handler.py
cd "$REPO_ROOT"

# --- app handler ---
# app/ package: handler.py + dispatcher.py
cd "$BACKEND/src"
zip -qr "$DIST/app.zip" app/
cd "$REPO_ROOT"

# --- profile handler ---
cd "$BACKEND/src"
zip -qr "$DIST/profile.zip" profile/
cd "$REPO_ROOT"

# --- relations handler ---
cd "$BACKEND/src"
zip -qr "$DIST/relations.zip" relations/
cd "$REPO_ROOT"

# --- log handler ---
cd "$BACKEND/src"
zip -qr "$DIST/log.zip" log/
cd "$REPO_ROOT"

echo "Lambda zips written to $DIST"
```

Notes:
- `uv export --no-dev --no-emit-project` produces a requirements.txt containing only the two production dependencies (`cachetools`, `pyjwt[cryptography]`). The project package itself is excluded (`--no-emit-project`) because handler source goes into separate handler zips, not the layer.
- `auth.py` and `session_guard.py` are in the layer (they are Lambda Layer utilities imported by handlers). They are NOT in the handler zips. The `auth_handler.py` zip only needs the entry-point file; it imports `auth` and `session_guard` from the layer at runtime.
- The layer zip structure must be `python/<packages>/` so Lambda's runtime path resolution finds them under `/opt/python/`.
- `pip` (not `uv`) is used for the `pip install -t` step because `uv` does not support `--target` installation for layer assembly.

The `deploy/variables.tf` already has `*_zip_path` variables for all six zips. The CD workflow will pass them as `-var` flags pointing at `backend/dist/*.zip`.

#### 5. `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync --dev

      - name: Lint
        run: uv run ruff check .

      - name: Type check
        run: uv run mypy .

      - name: Unit tests
        run: uv run pytest
```

No AWS credentials needed — moto mocks all DynamoDB calls.

#### 6. `.github/workflows/e2e.yml`

```yaml
name: E2E

on:
  push:
  pull_request:

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Install backend dependencies
        working-directory: backend
        run: uv sync --dev

      - name: Start dev backend
        working-directory: backend
        run: uv run python -m dev.server &

      - name: Install Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci

      - name: Install Playwright browsers
        working-directory: integration_tests
        run: npx playwright install --with-deps chromium

      - name: Install integration test dependencies
        working-directory: integration_tests
        run: npm ci

      - name: Run Playwright tests
        working-directory: integration_tests
        run: npx playwright test
```

The dev backend listens on port 8000 and always authenticates as `dev@local.dev` — no OAuth secrets needed. `playwright.config.ts` auto-starts the Vite dev server on port 5173.

#### 7. `.github/workflows/cd.yml`

```yaml
name: CD

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Install backend dependencies
        working-directory: backend
        run: uv sync

      - name: Build Lambda zips
        run: scripts/build_lambdas.sh

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-central-1

      - name: Terraform init
        working-directory: deploy
        run: terraform init

      - name: Terraform apply
        working-directory: deploy
        env:
          TF_VAR_google_client_id: ${{ secrets.GOOGLE_CLIENT_ID }}
          TF_VAR_session_secret: ${{ secrets.SESSION_SECRET }}
          TF_VAR_layer_zip_path: ../backend/dist/layer.zip
          TF_VAR_auth_zip_path: ../backend/dist/auth.zip
          TF_VAR_app_zip_path: ../backend/dist/app.zip
          TF_VAR_profile_zip_path: ../backend/dist/profile.zip
          TF_VAR_relations_zip_path: ../backend/dist/relations.zip
          TF_VAR_log_zip_path: ../backend/dist/log.zip
        run: terraform apply -auto-approve

      - name: Read Terraform outputs
        id: tf
        working-directory: deploy
        run: |
          echo "cf_dist_id=$(terraform output -raw cloudfront_distribution_id)" >> "$GITHUB_OUTPUT"
          echo "cf_url=$(terraform output -raw cloudfront_url)"                 >> "$GITHUB_OUTPUT"

      - name: Install Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Build frontend
        working-directory: frontend
        run: |
          npm ci
          npm run build

      - name: Sync frontend assets to S3
        run: |
          BUCKET=$(aws s3 ls | awk '/chai-s-romashkoi-frontend/ {print $3}')
          aws s3 sync frontend/dist/ "s3://$BUCKET/" --delete

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ steps.tf.outputs.cf_dist_id }} \
            --paths "/*"
```

Key design decisions:
- `terraform apply` runs before `npm run build` because `apply` writes `.env.production.local` via the existing `local_file` resource in `deploy/modules/frontend/main.tf`. Vite reads that file during `npm run build`.
- The S3 bucket name for the frontend is discovered at runtime via `aws s3 ls` filtered by project prefix, rather than hardcoding it, to avoid duplication with the Terraform-managed name.
- `environment: production` gates secrets; the `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` are not available to `ci` or `e2e` workflows.

#### 8. `README.md` — IAM setup section

Add a section titled "Deployment setup (one-time)" with the following sub-sections.

**Bootstrap Terraform state**

```
cd deploy/bootstrap
terraform init
terraform apply
# Note the outputs: state_bucket_name and lock_table_name
```

**Create a deployment IAM user**

1. Open the AWS console → IAM → Users → Create user.
2. Name: `chai-s-romashkoi-deployer`. Select "Programmatic access".
3. Attach the following inline policy (replace `ACCOUNT_ID`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
        "s3:ListBucket", "s3:GetBucketLocation",
        "s3:GetBucketVersioning"
      ],
      "Resource": [
        "arn:aws:s3:::chai-s-romashkoi-tf-state",
        "arn:aws:s3:::chai-s-romashkoi-tf-state/*",
        "arn:aws:s3:::chai-s-romashkoi-frontend",
        "arn:aws:s3:::chai-s-romashkoi-frontend/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem", "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:eu-central-1:ACCOUNT_ID:table/chai-s-romashkoi-tf-lock"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction", "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration", "lambda:GetFunction",
        "lambda:GetFunctionConfiguration", "lambda:PublishLayerVersion",
        "lambda:GetLayerVersion", "lambda:AddPermission",
        "lambda:RemovePermission", "lambda:CreateFunctionUrlConfig",
        "lambda:UpdateFunctionUrlConfig", "lambda:GetFunctionUrlConfig",
        "lambda:DeleteFunction"
      ],
      "Resource": "arn:aws:lambda:eu-central-1:ACCOUNT_ID:function:chai-s-romashkoi-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetRole", "iam:CreateRole", "iam:AttachRolePolicy",
        "iam:DetachRolePolicy", "iam:PutRolePolicy", "iam:GetRolePolicy",
        "iam:DeleteRolePolicy", "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::ACCOUNT_ID:role/chai-s-romashkoi-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable", "dynamodb:DescribeTable",
        "dynamodb:UpdateTable", "dynamodb:DeleteTable",
        "dynamodb:ListTables", "dynamodb:DescribeContinuousBackups",
        "dynamodb:DescribeTimeToLive"
      ],
      "Resource": "arn:aws:dynamodb:eu-central-1:ACCOUNT_ID:table/chai-s-romashkoi-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:GetDistribution", "cloudfront:CreateDistribution",
        "cloudfront:UpdateDistribution", "cloudfront:DeleteDistribution",
        "cloudfront:GetDistributionConfig",
        "cloudfront:CreateInvalidation", "cloudfront:GetInvalidation",
        "cloudfront:ListDistributions",
        "cloudfront:CreateOriginAccessControl",
        "cloudfront:GetOriginAccessControl",
        "cloudfront:DeleteOriginAccessControl"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetPolicy", "iam:CreatePolicy", "iam:DeletePolicy"
      ],
      "Resource": "arn:aws:iam::ACCOUNT_ID:policy/chai-s-romashkoi-*"
    }
  ]
}
```

4. Click "Create user". On the confirmation screen, download or copy the Access key ID and Secret access key — they are shown only once.

**Set GitHub Actions secrets**

Navigate to the repository on GitHub → Settings → Secrets and variables → Actions → New repository secret. Create these secrets:

| Secret name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key ID from the IAM user created above |
| `AWS_SECRET_ACCESS_KEY` | Secret access key from the IAM user created above |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID from Google Cloud Console |
| `SESSION_SECRET` | A random string used to sign session JWTs (e.g. `openssl rand -hex 32`) |

All four secrets must be scoped to the `production` environment (Settings → Environments → production → Add secret) because `cd.yml` sets `environment: production`.

## Secrets table

| Secret | Used by | Purpose |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | `cd.yml` only | Authenticates Terraform and AWS CLI to the deployer IAM user |
| `AWS_SECRET_ACCESS_KEY` | `cd.yml` only | Paired with the above |
| `GOOGLE_CLIENT_ID` | `cd.yml` only | Passed as `TF_VAR_google_client_id`; injected into auth Lambda env |
| `SESSION_SECRET` | `cd.yml` only | Passed as `TF_VAR_session_secret`; injected into all Lambda envs |

`ci.yml` and `e2e.yml` require no secrets. The dev backend always authenticates as `dev@local.dev` and does not validate Google tokens.

## Open questions

1. The S3 sync step locates the frontend bucket by filtering `aws s3 ls` output with a name prefix. If another bucket with the prefix `chai-s-romashkoi-frontend` exists in the account, this step will break. The implementer may instead add a `frontend_bucket_name` output to `deploy/outputs.tf` and use it directly, at the cost of a second `terraform output` call.

2. The deployer IAM policy above grants `cloudfront:*` on `Resource: "*"` because CloudFront ARNs are global and Terraform's provider requires `ListDistributions`. The implementer should verify whether tighter scoping is possible by checking which Terraform resource operations trigger list calls.

3. `scripts/build_lambdas.sh` calls bare `pip` for the layer assembly. On the GitHub Actions runner (`ubuntu-latest`) the default `pip` installs Python 3.12 packages. If the runner's default Python version changes away from 3.12, the layer may contain binaries incompatible with the Lambda runtime. The implementer should pin the Python version with `actions/setup-python` before calling the build script, or replace `pip` with `uv pip install --python 3.12`.

4. `auth.py` and `session_guard.py` are shared layer modules. Their source paths must be included in the layer zip rather than any handler zip. The build script above does not explicitly zip these files; they are imported as a Python package from the layer at Lambda runtime. Verify the `[tool.hatch.build.targets.wheel]` `packages` entry includes them when checking correctness of the script zip contents.
