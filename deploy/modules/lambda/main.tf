# Lambda module
#
# Creates:
#   - A shared Lambda Layer containing common Python utilities (auth, etc.)
#   - Five Lambda functions: auth_handler, app_handler, profile_handler, relations_handler, log_handler
#   - Five Lambda Function URLs (one per function), each with CORS configured
#   - A DynamoDB table for user profiles with GSIs for pending relations and log entry lookup
#   - A single IAM execution role shared by all five Lambdas
#   - An inline IAM policy granting DynamoDB access (table + GSIs) to the handlers

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

# Inline policy scoped to the profiles table and its GSI — least privilege.
data "aws_iam_policy_document" "dynamodb_profiles" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:TransactWriteItems",
    ]
    resources = [
      aws_dynamodb_table.profiles.arn,
      # GSI ARN required for Query calls targeting PendingReceivedIndex.
      "${aws_dynamodb_table.profiles.arn}/index/PendingReceivedIndex",
      # GSI ARN required for Query calls targeting LogEntryByIdIndex.
      "${aws_dynamodb_table.profiles.arn}/index/LogEntryByIdIndex",
    ]
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

  # GSI attributes — DynamoDB requires every attribute used in an index to be
  # declared here even if they are not part of the base table key schema.
  attribute {
    name = "owner_email"
    type = "S"
  }

  attribute {
    name = "status_direction"
    type = "S"
  }

  attribute {
    name = "entry_id"
    type = "S"
  }

  # GSI used by the relations handler to look up pending received requests for
  # a given owner without scanning the entire table.
  global_secondary_index {
    name            = "PendingReceivedIndex"
    hash_key        = "owner_email"
    range_key       = "status_direction"
    projection_type = "KEYS_ONLY" # minimise read cost — callers re-fetch as needed
  }

  # GSI used by the log handler to query log entries by owner and entry ID.
  global_secondary_index {
    name            = "LogEntryByIdIndex"
    hash_key        = "owner_email"
    range_key       = "entry_id"
    projection_type = "ALL"
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
      SESSION_SECRET      = var.session_secret
      # Required to call count_pending_received on the profiles table.
      PROFILES_TABLE_NAME = aws_dynamodb_table.profiles.name
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

resource "aws_lambda_function" "relations_handler" {
  function_name    = "${var.project_name}-relations"
  role             = aws_iam_role.this.arn
  handler          = "relations.handler.handler"
  runtime          = "python3.12"
  filename         = var.relations_zip_path
  source_code_hash = filebase64sha256(var.relations_zip_path)
  memory_size      = 128 # minimum — increase only with measured justification

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

resource "aws_lambda_function_url" "relations_handler" {
  function_name      = aws_lambda_function.relations_handler.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST", "DELETE"]
    allow_headers     = ["content-type", "authorization"]
    max_age           = 86400
  }
}

resource "aws_lambda_function" "log_handler" {
  function_name    = "${var.project_name}-log"
  role             = aws_iam_role.this.arn
  handler          = "log.handler.handler"
  runtime          = "python3.12"
  filename         = var.log_zip_path
  source_code_hash = filebase64sha256(var.log_zip_path)
  memory_size      = 128 # minimum — increase only with measured justification

  layers = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      SESSION_SECRET      = var.session_secret
      PROFILES_TABLE_NAME = aws_dynamodb_table.profiles.name
    }
  }
}

resource "aws_lambda_function_url" "log_handler" {
  function_name      = aws_lambda_function.log_handler.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE"]
    allow_headers     = ["content-type", "authorization"]
    max_age           = 86400
  }
}

# ---------------------------------------------------------------------------
# Lambda permissions — allow Function URL invoker (anonymous HTTP) to call
# each function. Required when authorization_type = "NONE".
# ---------------------------------------------------------------------------

resource "aws_lambda_permission" "relations_handler_url_invoker" {
  statement_id           = "FunctionURLAllowPublicAccess3"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.relations_handler.function_name
  principal              = "*"
  function_url_auth_type = "NONE"

  lifecycle {
    replace_triggered_by = [
      aws_lambda_function.relations_handler,
      aws_lambda_function_url.relations_handler,
    ]
  }
}

resource "aws_lambda_permission" "log_handler_url_invoker" {
  statement_id           = "FunctionURLAllowPublicAccess3"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.log_handler.function_name
  principal              = "*"
  function_url_auth_type = "NONE"

  lifecycle {
    replace_triggered_by = [
      aws_lambda_function.log_handler,
      aws_lambda_function_url.log_handler,
    ]
  }
}

resource "aws_lambda_permission" "auth_handler_url_invoker" {
  statement_id           = "FunctionURLAllowPublicAccess3"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.auth_handler.function_name
  principal              = "*"
  function_url_auth_type = "NONE"

  lifecycle {
    replace_triggered_by = [
      aws_lambda_function.auth_handler,
      aws_lambda_function_url.auth_handler,
    ]
  }
}

resource "aws_lambda_permission" "app_handler_url_invoker" {
  statement_id           = "FunctionURLAllowPublicAccess3"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.app_handler.function_name
  principal              = "*"
  function_url_auth_type = "NONE"

  lifecycle {
    replace_triggered_by = [
      aws_lambda_function.app_handler,
      aws_lambda_function_url.app_handler,
    ]
  }
}

resource "aws_lambda_permission" "profile_handler_url_invoker" {
  statement_id           = "FunctionURLAllowPublicAccess3"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.profile_handler.function_name
  principal              = "*"
  function_url_auth_type = "NONE"

  lifecycle {
    replace_triggered_by = [
      aws_lambda_function.profile_handler,
      aws_lambda_function_url.profile_handler,
    ]
  }
}
