variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "autocode"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.1.0.0/16"
}

variable "azs" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "domain_name" {
  description = "Root domain name for the application"
  type        = string
}

variable "create_hosted_zone" {
  description = "Whether to create a new Route53 hosted zone"
  type        = bool
  default     = false
}

variable "key_pair_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
}

variable "ami_id" {
  description = "AMI ID for EC2 instance. Leave empty to use latest Amazon Linux 2."
  type        = string
  default     = ""
}

variable "admin_arn" {
  description = "ARN of the IAM user/role for KMS key administration"
  type        = string
}

variable "bastion_cidr" {
  description = "CIDR block for bastion/SSH access"
  type        = string
  default     = null
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
}

variable "waf_rate_limit" {
  description = "WAF rate limit (requests per 5-minute period per IP)"
  type        = number
  default     = 2000
}

variable "cors_allowed_origins" {
  description = "Allowed CORS origins for the exports bucket"
  type        = list(string)
  default     = []
}
