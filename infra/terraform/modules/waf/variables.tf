variable "alb_arn" {
  description = "ARN of the ALB to associate with the WAF"
  type        = string
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

variable "rate_limit" {
  description = "Maximum number of requests per 5-minute period per IP"
  type        = number
  default     = 2000
}
