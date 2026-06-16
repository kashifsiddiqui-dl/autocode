################################################################################
# Production Environment – Auto Code Infrastructure (HIPAA-Compliant)
################################################################################

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "autocode-terraform-state"
    key            = "environments/production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "autocode-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Compliance  = "HIPAA"
    }
  }
}

# ==============================================================================
# Data Sources
# ==============================================================================
data "aws_caller_identity" "current" {}

# Latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ==============================================================================
# KMS
# ==============================================================================
module "kms" {
  source = "../../modules/kms"

  environment = var.environment
  admin_arn   = var.admin_arn
}

# ==============================================================================
# VPC
# ==============================================================================
module "vpc" {
  source = "../../modules/vpc"

  vpc_cidr             = var.vpc_cidr
  environment          = var.environment
  project_name         = var.project_name
  azs                  = var.azs
  enable_ha_nat        = true # HA NAT Gateway for production
  flow_log_kms_key_arn = module.kms.key_arn
}

# ==============================================================================
# S3 Buckets
# ==============================================================================
module "s3" {
  source = "../../modules/s3"

  environment          = var.environment
  project_name         = var.project_name
  kms_key_id           = module.kms.key_id
  cors_allowed_origins = var.cors_allowed_origins
}

# ==============================================================================
# Route53
# ==============================================================================
module "route53" {
  source = "../../modules/route53"

  domain_name     = var.domain_name
  alb_dns_name    = module.alb.alb_dns_name
  alb_zone_id     = module.alb.alb_zone_id
  create_zone     = var.create_hosted_zone
  subdomain       = null # Root domain for production
  enable_wildcard = true # Wildcard for tenant subdomains
  environment     = var.environment
}

# ==============================================================================
# ACM Certificate
# ==============================================================================
module "acm" {
  source = "../../modules/acm"

  domain_name       = var.domain_name
  zone_id           = module.route53.zone_id
  include_wildcard  = true # Wildcard cert for tenant subdomains
  environment       = var.environment
}

# ==============================================================================
# ALB (created before EC2 to provide security_group_id)
# ==============================================================================
module "alb" {
  source = "../../modules/alb"

  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  certificate_arn    = module.acm.certificate_arn
  access_logs_bucket = module.s3.logs_bucket_name
  environment        = var.environment
  # target_instance_id is set after EC2 is created (see below)
}

# ==============================================================================
# EC2
# ==============================================================================
module "ec2" {
  source = "../../modules/ec2"

  instance_type      = "t3.xlarge" # Production size
  ami_id             = var.ami_id != "" ? var.ami_id : data.aws_ami.amazon_linux.id
  subnet_id          = module.vpc.private_subnet_ids[0]
  vpc_id             = module.vpc.vpc_id
  alb_sg_id          = module.alb.security_group_id
  kms_key_arn        = module.kms.key_arn
  key_pair_name      = var.key_pair_name
  environment        = var.environment
  bastion_cidr       = var.bastion_cidr
  qdrant_volume_size = 100 # Larger for production
  availability_zone  = var.azs[0]
  aws_region         = var.aws_region
}

# Register EC2 instance with ALB target group (breaks circular dependency)
resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = module.alb.target_group_arn
  target_id        = module.ec2.instance_id
  port             = 80
}

# ==============================================================================
# RDS
# ==============================================================================
module "rds" {
  source = "../../modules/rds"

  instance_class    = "db.r6g.large" # Production-grade
  engine_version    = "17.2"
  db_name           = "autocode"
  db_username       = "autocode_admin"
  allocated_storage = 100
  multi_az          = true # Multi-AZ for production
  backup_retention  = 35  # 35-day retention for production
  kms_key_arn       = module.kms.key_arn
  subnet_ids        = module.vpc.private_subnet_ids
  vpc_id            = module.vpc.vpc_id
  app_sg_id         = module.ec2.security_group_id
  environment       = var.environment
}

# ==============================================================================
# CloudWatch Monitoring
# ==============================================================================
module "cloudwatch" {
  source = "../../modules/cloudwatch"

  environment = var.environment
  instance_id = module.ec2.instance_id
  alb_arn     = module.alb.alb_arn
  alarm_email = var.alarm_email
  kms_key_arn = module.kms.key_arn
}

# ==============================================================================
# WAF (always enabled for production)
# ==============================================================================
module "waf" {
  source = "../../modules/waf"

  alb_arn     = module.alb.alb_arn
  environment = var.environment
  rate_limit  = var.waf_rate_limit
}
