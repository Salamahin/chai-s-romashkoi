variable "project_name" {
  description = "Project name used as a prefix for all resource names"
  type        = string
}

variable "dist_path" {
  description = "Local path to the built frontend static assets directory"
  type        = string
}

variable "auth_function_url" {
  description = "Lambda Function URL for the auth handler (https://...)"
  type        = string
}

variable "app_function_url" {
  description = "Lambda Function URL for the app handler (https://...)"
  type        = string
}

variable "profile_function_url" {
  description = "Lambda Function URL for the profile handler (https://...)"
  type        = string
}
