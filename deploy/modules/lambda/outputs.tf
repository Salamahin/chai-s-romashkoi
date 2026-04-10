output "auth_function_url" {
  description = "Function URL for the auth handler Lambda"
  value       = aws_lambda_function_url.auth_handler.function_url
}

output "app_function_url" {
  description = "Function URL for the app handler Lambda"
  value       = aws_lambda_function_url.app_handler.function_url
}

output "profile_function_url" {
  description = "Function URL for the profile handler Lambda"
  value       = aws_lambda_function_url.profile_handler.function_url
}

output "relations_function_url" {
  description = "Function URL for the relations handler Lambda"
  value       = aws_lambda_function_url.relations_handler.function_url
}
