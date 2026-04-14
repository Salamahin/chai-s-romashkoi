# About

**chai c romashkoi** is aimed to help a group of close relatives to watch out
their lifestyle such as food habits and working out sessions.

## Local Development

### One-time setup

1. Create `backend/.env`:
   ```
   SESSION_SECRET=any-random-string
   ```

2. Create `frontend/.env`:
   ```
   VITE_API_URL=http://localhost:8000
   ```

In local mode the Google OAuth flow is bypassed — a hardcoded `dev@local.dev` user is used instead. `GOOGLE_CLIENT_ID` is only required for production deployment. `VITE_RELATIONS_API_URL` is not required locally; the relations service falls back to `http://localhost:8000` automatically.

### Running

```bash
bash scripts/local_run.sh   # start backend (:8000) and frontend (:5173)
bash scripts/local_kill.sh  # stop both
```

### E2E tests

```bash
bash scripts/e2e.sh
```

Starts the backend, installs integration test dependencies if needed, then runs Playwright (which starts Vite automatically). Tests validate the full local login flow: button click → token exchange → app page.

## Deployment setup (one-time)

### Bootstrap Terraform state

Run this once to create the S3 bucket and DynamoDB table that store Terraform remote state:

```bash
cd deploy/bootstrap
terraform init
terraform apply
# Note the outputs: state_bucket_name and lock_table_name
```

The bucket and lock table names are already wired into `deploy/main.tf`'s `backend "s3"` block. No manual editing is needed after the bootstrap apply succeeds.

### Create a deployment IAM user

1. Open the AWS console → IAM → Users → Create user.
2. Name: `chai-s-romashkoi-deployer`. Select "Programmatic access".
3. Attach the following inline policy (replace `ACCOUNT_ID` with your 12-digit AWS account ID):

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

### Set GitHub Actions secrets

Navigate to the repository on GitHub → Settings → Secrets and variables → Actions → New repository secret. All four secrets must be scoped to the `production` environment (Settings → Environments → production → Add secret) because `cd.yml` sets `environment: production`.

| Secret name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key ID from the IAM user created above |
| `AWS_SECRET_ACCESS_KEY` | Secret access key from the IAM user created above |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID from Google Cloud Console |
| `SESSION_SECRET` | A random string used to sign session JWTs (e.g. `openssl rand -hex 32`) |

`ci.yml` and `e2e.yml` require no secrets — the dev backend always authenticates as `dev@local.dev` and does not validate Google tokens.

## Development Dependencies

| Tool | Version | Purpose |
|------|---------|---------|
| [Python](https://www.python.org/) | >=3.12 | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager |
| [Node.js](https://nodejs.org/) | >=20 | Frontend runtime |
| [Terraform](https://www.terraform.io/) | latest | Infrastructure provisioning |
