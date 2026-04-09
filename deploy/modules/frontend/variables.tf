variable "project_name" {
  type = string
}

variable "dist_path" {
  type = string
}

variable "lambda_invoke_arn" {
  type        = string
  description = "Lambda function ARN (unused in frontend module, kept for dependency ordering)"
}
