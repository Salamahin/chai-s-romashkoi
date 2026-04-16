output "state_bucket_name" {
  description = "S3 bucket name for Terraform remote state — paste into deploy/main.tf backend block"
  value       = aws_s3_bucket.tf_state.bucket
}

output "lock_table_name" {
  description = "DynamoDB table name for state locking — paste into deploy/main.tf backend block"
  value       = aws_dynamodb_table.tf_lock.name
}

output "deploy_role_arn" {
  description = "ARN of the IAM role assumed by the GitHub Actions CD workflow via OIDC"
  value       = aws_iam_role.deploy.arn
}
