output "cloudfront_domain" {
  value = aws_cloudfront_distribution.this.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID used for cache invalidation"
  value       = aws_cloudfront_distribution.this.id
}
