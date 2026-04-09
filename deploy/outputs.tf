output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${module.frontend.cloudfront_domain}"
}

output "lambda_function_url" {
  description = "Lambda Function URL"
  value       = module.lambda.function_url
}
