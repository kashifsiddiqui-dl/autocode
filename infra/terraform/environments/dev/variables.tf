variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "autocode"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
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
  description = "ARN of the IAM user/role for KMS key administration. Leave empty to use current caller."
  type        = string
  default     = ""
}

variable "bastion_cidr" {
  description = "CIDR block for bastion/SSH access"
  type        = string
  default     = null
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = null
}

variable "enable_waf" {
  description = "Enable WAF for dev environment"
  type        = bool
  default     = false
}
