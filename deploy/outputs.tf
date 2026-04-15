output "cloudfront_url" {
  description = "CloudFront distribution URL (entry point for both frontend and API)"
  value       = "https://${module.frontend.cloudfront_domain}"
}

output "auth_function_url" {
  description = "Direct Lambda Function URL for the auth handler"
  value       = module.lambda.auth_function_url
}

output "app_function_url" {
  description = "Direct Lambda Function URL for the app handler"
  value       = module.lambda.app_function_url
}

output "profile_function_url" {
  description = "Direct Lambda Function URL for the profile handler"
  value       = module.lambda.profile_function_url
}

output "relations_function_url" {
  description = "Direct Lambda Function URL for the relations handler"
  value       = module.lambda.relations_function_url
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID used for cache invalidation"
  value       = module.frontend.cloudfront_distribution_id
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend assets"
  value       = module.frontend.frontend_bucket_name
}
