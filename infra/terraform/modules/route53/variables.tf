variable "domain_name" {
  description = "Root domain name (e.g., autocode.example.com)"
  type        = string
}

variable "alb_dns_name" {
  description = "DNS name of the ALB"
  type        = string
}

variable "alb_zone_id" {
  description = "Route53 zone ID of the ALB"
  type        = string
}

variable "create_zone" {
  description = "Whether to create a new hosted zone or use an existing one"
  type        = bool
  default     = false
}

variable "subdomain" {
  description = "Optional subdomain prefix (e.g., 'app' creates app.domain.com)"
  type        = string
  default     = null
}

variable "enable_wildcard" {
  description = "Create wildcard DNS record for tenant subdomains"
  type        = bool
  default     = false
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "autocode"
}
