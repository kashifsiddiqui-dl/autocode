variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.xlarge"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance (Amazon Linux 2)"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID to launch the instance in (private subnet)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "alb_sg_id" {
  description = "Security group ID of the ALB (for ingress rules)"
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN for EBS encryption"
  type        = string
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "autocode"
}

variable "bastion_cidr" {
  description = "CIDR block for bastion/SSH access. Set to null to disable SSH access."
  type        = string
  default     = null
}

variable "qdrant_volume_size" {
  description = "Size in GB for the Qdrant data EBS volume"
  type        = number
  default     = 50
}

variable "availability_zone" {
  description = "Availability zone for the EBS volume (must match the instance)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
