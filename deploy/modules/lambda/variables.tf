variable "project_name" {
  description = "Project name used as a prefix for all resource names"
  type        = string
}

variable "layer_zip_path" {
  description = "Path to shared layer zip containing common Python dependencies and auth utilities"
  type        = string
}

variable "auth_zip_path" {
  description = "Path to auth handler Lambda zip (handles POST /auth/session)"
  type        = string
}

variable "app_zip_path" {
  description = "Path to app handler Lambda zip (handles general app routes)"
  type        = string
}

variable "profile_zip_path" {
  description = "Path to profile handler Lambda zip (handles /profile routes)"
  type        = string
}

variable "google_client_id" {
  description = "Google OAuth client ID passed to the auth Lambda as an environment variable"
  type        = string
  sensitive   = true
}

variable "session_secret" {
  description = "Secret key used to sign session tokens"
  type        = string
  sensitive   = true
}

variable "jwks_url" {
  description = "URL of Google's public JWKS endpoint for token verification"
  type        = string
  default     = "https://www.googleapis.com/oauth2/v3/certs"
}

variable "session_ttl_seconds" {
  description = "Session lifetime in seconds"
  type        = number
  default     = 900
}
