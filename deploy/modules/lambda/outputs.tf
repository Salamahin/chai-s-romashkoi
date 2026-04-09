output "function_url" {
  value = aws_lambda_function_url.this.function_url
}

output "function_arn" {
  value = aws_lambda_function.this.arn
}
