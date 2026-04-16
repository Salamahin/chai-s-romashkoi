# Provisions the custom domain chaisromashkoi.org for the CloudFront distribution.
# Resources created here:
#   - us-east-1 provider alias (ACM certificates for CloudFront must be in us-east-1)
#   - ACM certificate with DNS validation
#   - Route53 CNAME records that satisfy the ACM DNS challenge
#   - Route53 A alias record pointing the apex domain at CloudFront

# ACM certificates used by CloudFront must live in us-east-1 regardless of the
# primary deployment region.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# The hosted zone was pre-created when the domain was registered in Route53.
data "aws_route53_zone" "app" {
  name         = "chaisromashkoi.org."
  private_zone = false
}

resource "aws_acm_certificate" "app" {
  provider          = aws.us_east_1
  domain_name       = "chaisromashkoi.org"
  validation_method = "DNS"

  lifecycle {
    # Prevent accidental deletion of a certificate that CloudFront depends on.
    create_before_destroy = true
  }
}

# One CNAME record per domain validation option. ACM may return multiple options
# when a certificate covers several names; for_each handles that generically.
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.app.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = data.aws_route53_zone.app.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "app" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

# Apex A record aliased to the CloudFront distribution.
# CloudFront hosted zone ID is a fixed AWS constant (Z2FDTNDATAQYW2) but we
# retrieve it from the module output to avoid hardcoding.
resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.app.zone_id
  name    = "chaisromashkoi.org"
  type    = "A"

  alias {
    name                   = module.frontend.cloudfront_domain
    zone_id                = module.frontend.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}
