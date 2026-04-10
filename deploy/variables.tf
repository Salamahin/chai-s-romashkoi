variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "chai-s-romashkoi"
}

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  sensitive   = true
}

variable "session_secret" {
  description = "Secret key used to sign session tokens"
  type        = string
  sensitive   = true
}

variable "layer_zip_path" {
  description = "Path to shared Lambda layer zip containing common Python utilities"
  type        = string
}

variable "auth_zip_path" {
  description = "Path to auth handler Lambda zip"
  type        = string
}

variable "app_zip_path" {
  description = "Path to app handler Lambda zip"
  type        = string
}

variable "profile_zip_path" {
  description = "Path to profile handler Lambda zip"
  type        = string
}
