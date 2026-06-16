variable "domain_name" {
  description = "Primary domain name for the certificate"
  type        = string
}

variable "zone_id" {
  description = "Route53 hosted zone ID for DNS validation"
  type        = string
}

variable "subject_alternative_names" {
  description = "Additional subject alternative names for the certificate"
  type        = list(string)
  default     = []
}

variable "include_wildcard" {
  description = "Include a wildcard SAN (*.domain_name)"
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
