################################################################################
# Route53 Module – Auto Code DNS
################################################################################

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  zone_id = var.create_zone ? aws_route53_zone.main[0].zone_id : data.aws_route53_zone.existing[0].zone_id
}

# ------------------------------------------------------------------------------
# Hosted Zone (create or use existing)
# ------------------------------------------------------------------------------
resource "aws_route53_zone" "main" {
  count = var.create_zone ? 1 : 0

  name    = var.domain_name
  comment = "Hosted zone for Auto Code ${var.environment}"

  tags = local.common_tags
}

data "aws_route53_zone" "existing" {
  count = var.create_zone ? 0 : 1

  name         = var.domain_name
  private_zone = false
}

# ------------------------------------------------------------------------------
# A Record – ALB Alias
# ------------------------------------------------------------------------------
resource "aws_route53_record" "app" {
  zone_id = local.zone_id
  name    = var.subdomain != null ? "${var.subdomain}.${var.domain_name}" : var.domain_name
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}

# ------------------------------------------------------------------------------
# Wildcard Record (optional – for tenant subdomains)
# ------------------------------------------------------------------------------
resource "aws_route53_record" "wildcard" {
  count = var.enable_wildcard ? 1 : 0

  zone_id = local.zone_id
  name    = var.subdomain != null ? "*.${var.subdomain}.${var.domain_name}" : "*.${var.domain_name}"
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}
