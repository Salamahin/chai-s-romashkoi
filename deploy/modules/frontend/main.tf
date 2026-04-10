# Frontend module
#
# Creates:
#   - An S3 bucket (private) for static frontend assets
#   - A CloudFront Origin Access Control so CloudFront can read the bucket
#   - An S3 bucket policy granting read access to CloudFront only
#   - S3 objects for every file under var.dist_path
#   - A CloudFront distribution with five origins:
#       1. S3 bucket — static assets (default behaviour, caching enabled)
#       2. auth Lambda Function URL  — routed for /auth/*
#       3. app Lambda Function URL   — routed for /app/* (catch-all app routes)
#       4. profile Lambda Function URL — routed for /profile and /profile/*
#       5. relations Lambda Function URL — routed for /relations and /relations/*
#   Cache behaviours are evaluated in declaration order; the default falls
#   through to S3 for everything not matched by an ordered behaviour.
#   - A local_file writing frontend/.env.production.local with VITE_RELATIONS_API_URL
#     so vite build picks it up without committing secrets to the repo.
#
# Cost: CloudFront free tier covers 10M requests/month. S3 storage and
# request costs are negligible for a small SPA. No hourly charges.

locals {
  mime_types = {
    ".html"  = "text/html"
    ".js"    = "application/javascript"
    ".css"   = "text/css"
    ".json"  = "application/json"
    ".svg"   = "image/svg+xml"
    ".ico"   = "image/x-icon"
    ".png"   = "image/png"
    ".woff2" = "font/woff2"
  }

  # Strip "https://" prefix and trailing "/" to extract the bare hostname
  # required by CloudFront custom_origin_config domain_name.
  auth_origin_domain      = replace(replace(var.auth_function_url, "https://", ""), "/", "")
  app_origin_domain       = replace(replace(var.app_function_url, "https://", ""), "/", "")
  profile_origin_domain   = replace(replace(var.profile_function_url, "https://", ""), "/", "")
  relations_origin_domain = replace(replace(var.relations_api_url, "https://", ""), "/", "")
}

# ---------------------------------------------------------------------------
# S3 bucket for static assets
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "this" {
  bucket = "${var.project_name}-frontend"
}

# Block all public access — objects are served exclusively through CloudFront.
resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "this" {
  name                              = "${var.project_name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_iam_policy_document" "s3_policy" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.this.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.this.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.s3_policy.json
}

resource "aws_s3_object" "assets" {
  for_each     = fileset(var.dist_path, "**/*")
  bucket       = aws_s3_bucket.this.id
  key          = each.value
  source       = "${var.dist_path}/${each.value}"
  content_type = lookup(local.mime_types, regex("\\.[^.]+$", each.value), "application/octet-stream")
  etag         = filemd5("${var.dist_path}/${each.value}")
}

# ---------------------------------------------------------------------------
# Build-time environment variable injection
# ---------------------------------------------------------------------------

# Write .env.production.local so `vite build` picks up VITE_RELATIONS_API_URL
# without committing the value to the repository. The file is gitignored by
# convention (.env*.local). It is regenerated on every `terraform apply`.
resource "local_file" "frontend_env" {
  filename        = "${path.module}/../../../frontend/.env.production.local"
  content         = "VITE_RELATIONS_API_URL=${var.relations_api_url}\n"
  file_permission = "0644"
}

# ---------------------------------------------------------------------------
# CloudFront distribution
# ---------------------------------------------------------------------------

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  default_root_object = "index.html"
  # PriceClass_100 restricts edge locations to North America + Europe,
  # keeping costs minimal while covering the expected audience.
  price_class = "PriceClass_100"

  # Origin 1: S3 static assets
  origin {
    domain_name              = aws_s3_bucket.this.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.this.id
  }

  # Origin 2: auth Lambda Function URL
  origin {
    domain_name = local.auth_origin_domain
    origin_id   = "auth-handler"

    # Lambda Function URLs are HTTPS-only; no OAC — Lambda authorizes via NONE.
    custom_origin_config {
      https_port             = 443
      http_port              = 80
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Origin 3: app Lambda Function URL
  origin {
    domain_name = local.app_origin_domain
    origin_id   = "app-handler"

    custom_origin_config {
      https_port             = 443
      http_port              = 80
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Origin 4: profile Lambda Function URL
  origin {
    domain_name = local.profile_origin_domain
    origin_id   = "profile-handler"

    custom_origin_config {
      https_port             = 443
      http_port              = 80
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Origin 5: relations Lambda Function URL
  origin {
    domain_name = local.relations_origin_domain
    origin_id   = "relations-handler"

    custom_origin_config {
      https_port             = 443
      http_port              = 80
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # ---------------------------------------------------------------------------
  # Ordered cache behaviours (evaluated before the default behaviour)
  # ---------------------------------------------------------------------------

  # /auth/* → auth handler — caching disabled so every request reaches Lambda
  ordered_cache_behavior {
    path_pattern     = "/auth/*"
    target_origin_id = "auth-handler"

    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]

    # TTL 0 effectively disables caching — required for auth endpoints.
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      headers      = ["*"] # forward all headers so auth tokens reach Lambda
      cookies {
        forward = "all"
      }
    }
  }

  # /profile (exact) → profile handler
  ordered_cache_behavior {
    path_pattern     = "/profile"
    target_origin_id = "profile-handler"

    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }
  }

  # /profile/* → profile handler
  ordered_cache_behavior {
    path_pattern     = "/profile/*"
    target_origin_id = "profile-handler"

    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }
  }

  # /relations (exact) → relations handler
  ordered_cache_behavior {
    path_pattern     = "/relations"
    target_origin_id = "relations-handler"

    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }
  }

  # /relations/* → relations handler
  ordered_cache_behavior {
    path_pattern     = "/relations/*"
    target_origin_id = "relations-handler"

    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }
  }

  # ---------------------------------------------------------------------------
  # Default behaviour — S3 static assets with caching enabled
  # ---------------------------------------------------------------------------

  default_cache_behavior {
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  # Return index.html for unknown paths so the SPA router handles them.
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
