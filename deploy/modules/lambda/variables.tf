variable "project_name" {
  type = string
}

variable "zip_path" {
  type = string
}

variable "google_client_id" {
  description = "Google OAuth client ID passed to the Lambda as an environment variable"
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
