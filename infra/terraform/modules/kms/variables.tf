variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "autocode"
}

variable "admin_arn" {
  description = "ARN of the IAM user/role that will administer the KMS key"
  type        = string
}
