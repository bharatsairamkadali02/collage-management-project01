###############################################################################
# College Management System – Terraform Variables
###############################################################################

variable "aws_region" {
  description = "AWS region to deploy the infrastructure"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name of the project – used as a prefix for all resource names"
  type        = string
  default     = "college-management"
}

variable "environment" {
  description = "Deployment environment (e.g. production, staging, development)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "environment must be one of: production, staging, development."
  }
}

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet (ap-south-1a)"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_subnet_az1_cidr" {
  description = "CIDR block for the private subnet in ap-south-1a (RDS primary)"
  type        = string
  default     = "10.0.2.0/24"
}

variable "private_subnet_az2_cidr" {
  description = "CIDR block for the private subnet in ap-south-1b (RDS standby)"
  type        = string
  default     = "10.0.3.0/24"
}

# ---------------------------------------------------------------------------
# EC2
# ---------------------------------------------------------------------------

variable "ec2_instance_type" {
  description = "EC2 instance type for the application server"
  type        = string
  default     = "t3.small"
}

variable "ubuntu_ami" {
  description = "AMI ID for Ubuntu 24.04 LTS in ap-south-1 (ami-0f5ee92e2d63afc18)"
  type        = string
  default     = "ami-0f5ee92e2d63afc18"
}

variable "key_pair_name" {
  description = "Name of the existing EC2 Key Pair for SSH access (required)"
  type        = string
  default     = "laptopkeymumhp02"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the EC2 instance. Restrict to your IP in production (e.g. 203.0.113.0/32)."
  type        = string
  default     = "0.0.0.0/0"
}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

variable "db_username" {
  description = "Master username for the RDS MySQL instance (sensitive)"
  type        = string
  sensitive   = true
  default     = "admin"
}

variable "db_password" {
  description = "Master password for the RDS MySQL instance (sensitive, min 8 chars)"
  type        = string
  sensitive   = true
  default     = "password123"

  validation {
    condition     = length(var.db_password) >= 8
    error_message = "db_password must be at least 8 characters long."
  }
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

variable "s3_bucket_name" {
  description = "Globally unique S3 bucket name for college media and documents"
  type        = string
  default     = "college-media-docs-bucket"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9\\-]{1,61}[a-z0-9]$", var.s3_bucket_name))
    error_message = "s3_bucket_name must be 3-63 characters, lowercase letters, numbers, and hyphens only."
  }
}

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

variable "app_domain" {
  description = "Custom domain name for the application (e.g. college.yourdomain.com). Leave empty to use EC2 public IP."
  type        = string
  default     = ""
}
