variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "autocode"
}

variable "azs" {
  description = "List of availability zones (minimum 2)"
  type        = list(string)
}

variable "enable_ha_nat" {
  description = "Enable HA NAT Gateway (one per AZ). Set to false for single NAT to save costs."
  type        = bool
  default     = false
}

variable "flow_log_kms_key_arn" {
  description = "KMS key ARN for encrypting VPC flow log CloudWatch log group. Pass null to use default encryption."
  type        = string
  default     = null
}
