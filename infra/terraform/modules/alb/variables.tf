variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for the ALB"
  type        = list(string)
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS listener"
  type        = string
}

variable "target_instance_id" {
  description = "EC2 instance ID to register with the target group. Set to null to skip attachment."
  type        = string
  default     = null
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

variable "access_logs_bucket" {
  description = "S3 bucket name for ALB access logs"
  type        = string
}
