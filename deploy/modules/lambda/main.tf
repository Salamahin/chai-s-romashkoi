# Lambda module
#
# Creates:
#   - A shared Lambda Layer containing common Python utilities (auth, etc.)
#   - Three Lambda functions: auth_handler, app_handler, profile_handler
#   - Three Lambda Function URLs (one per function), each with CORS configured
#   - A DynamoDB table for user profiles
#   - A single IAM execution role shared by all three Lambdas
#   - An inline IAM policy granting DynamoDB access to the profile handler

# ---------------------------------------------------------------------------
# IAM
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.project_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

# Grants permission to write logs to CloudWatch — required for every Lambda.
resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Inline policy scoped to the profiles table only — least privilege.
data "aws_iam_policy_document" "dynamodb_profiles" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
    ]
    resources = [aws_dynamodb_table.profiles.arn]
  }
}

resource "aws_iam_role_policy" "dynamodb_profiles" {
  name   = "${var.project_name}-dynamodb-profiles"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.dynamodb_profiles.json
}

# ---------------------------------------------------------------------------
# DynamoDB
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "profiles" {
  name         = "${var.project_name}-profiles"
  billing_mode = "PAY_PER_REQUEST" # no hourly charges — pay per read/write unit
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  lifecycle {
    prevent_destroy = true # protect against accidental data loss
  }
}

# ---------------------------------------------------------------------------
# Shared Lambda Layer
# ---------------------------------------------------------------------------

resource "aws_lambda_layer_version" "shared" {
  layer_name          = "${var.project_name}-shared"
  filename            = var.layer_zip_path
  source_code_hash    = filebase64sha256(var.layer_zip_path)
  compatible_runtimes = ["python3.12"]
}

# ---------------------------------------------------------------------------
# Lambda Functions
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "auth_handler" {
  function_name    = "${var.project_name}-auth"
  role             = aws_iam_role.this.arn
  handler          = "auth_handler.handler"
  runtime          = "python3.12"
  filename         = var.auth_zip_path
  source_code_hash = filebase64sha256(var.auth_zip_path)
  memory_size      = 128 # minimum — increase only with measured justification

  layers = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      SESSION_SECRET      = var.session_secret
      JWKS_URL            = var.jwks_url
      GOOGLE_CLIENT_ID    = var.google_client_id
      SESSION_TTL_SECONDS = tostring(var.session_ttl_seconds)
    }
  }
}

resource "aws_lambda_function" "app_handler" {
  function_name    = "${var.project_name}-app"
  role             = aws_iam_role.this.arn
  handler          = "app.handler.handler"
  runtime          = "python3.12"
  filename         = var.app_zip_path
  source_code_hash = filebase64sha256(var.app_zip_path)
  memory_size      = 128

  layers = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      SESSION_SECRET = var.session_secret
    }
  }
}

resource "aws_lambda_function" "profile_handler" {
  function_name    = "${var.project_name}-profile"
  role             = aws_iam_role.this.arn
  handler          = "profile.handler.handler"
  runtime          = "python3.12"
  filename         = var.profile_zip_path
  source_code_hash = filebase64sha256(var.profile_zip_path)
  memory_size      = 128

  layers = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      SESSION_SECRET      = var.session_secret
      PROFILES_TABLE_NAME = aws_dynamodb_table.profiles.name
    }
  }
}

# ---------------------------------------------------------------------------
# Lambda Function URLs
# ---------------------------------------------------------------------------

resource "aws_lambda_function_url" "auth_handler" {
  function_name      = aws_lambda_function.auth_handler.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST", "PUT"]
    allow_headers     = ["content-type", "authorization"]
    max_age           = 86400
  }
}

resource "aws_lambda_function_url" "app_handler" {
  function_name      = aws_lambda_function.app_handler.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST", "PUT"]
    allow_headers     = ["content-type", "authorization"]
    max_age           = 86400
  }
}

resource "aws_lambda_function_url" "profile_handler" {
  function_name      = aws_lambda_function.profile_handler.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST", "PUT"]
    allow_headers     = ["content-type", "authorization"]
    max_age           = 86400
  }
}
