###############################################################################
# College Management System – Terraform Main Configuration
# Target: AWS ap-south-1 (Mumbai)  |  Architecture: Two-Tier (EC2 + RDS/S3)
###############################################################################

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

###############################################################################
# 1. VPC
###############################################################################

resource "aws_vpc" "college_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

###############################################################################
# 2. Subnets
###############################################################################

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.college_vpc.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet"
    Tier = "Public"
  }
}

resource "aws_subnet" "private_subnet_az1" {
  vpc_id            = aws_vpc.college_vpc.id
  cidr_block        = var.private_subnet_az1_cidr
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "${var.project_name}-private-subnet-az1"
    Tier = "Private"
  }
}

resource "aws_subnet" "private_subnet_az2" {
  vpc_id            = aws_vpc.college_vpc.id
  cidr_block        = var.private_subnet_az2_cidr
  availability_zone = "${var.aws_region}b"

  tags = {
    Name = "${var.project_name}-private-subnet-az2"
    Tier = "Private"
  }
}

###############################################################################
# 3. Internet Gateway
###############################################################################

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.college_vpc.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

###############################################################################
# 4. Route Tables
###############################################################################

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.college_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public_subnet_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

###############################################################################
# 5. Security Groups
###############################################################################

resource "aws_security_group" "ec2_sg" {
  name        = "${var.project_name}-ec2-sg"
  description = "Security group for College Management EC2 instance"
  vpc_id      = aws_vpc.college_vpc.id

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # HTTP
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Gunicorn (internal only – self-referencing)
  ingress {
    description = "Gunicorn internal"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    self        = true
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for College Management RDS instance"
  vpc_id      = aws_vpc.college_vpc.id

  # MySQL – only from EC2 security group
  ingress {
    description     = "MySQL from EC2"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

###############################################################################
# 6. IAM Role, Policy, and Instance Profile
###############################################################################

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_role" {
  name               = "${var.project_name}-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    Name = "${var.project_name}-ec2-role"
  }
}

data "aws_iam_policy_document" "s3_policy_doc" {
  statement {
    sid    = "S3ObjectAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.college_bucket.arn}/*"]
  }

  statement {
    sid    = "S3BucketAccess"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [aws_s3_bucket.college_bucket.arn]
  }
}

resource "aws_iam_policy" "s3_policy" {
  name        = "${var.project_name}-s3-policy"
  description = "Allow EC2 to access the College Management S3 bucket"
  policy      = data.aws_iam_policy_document.s3_policy_doc.json

  tags = {
    Name = "${var.project_name}-s3-policy"
  }
}

resource "aws_iam_role_policy_attachment" "ec2_s3_attachment" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.s3_policy.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name

  tags = {
    Name = "${var.project_name}-ec2-profile"
  }
}

###############################################################################
# 7. S3 Bucket
###############################################################################

resource "aws_s3_bucket" "college_bucket" {
  bucket        = var.s3_bucket_name
  force_destroy = false

  tags = {
    Name = var.s3_bucket_name
  }
}

resource "aws_s3_bucket_versioning" "college_bucket_versioning" {
  bucket = aws_s3_bucket.college_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "college_bucket_sse" {
  bucket = aws_s3_bucket.college_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "college_bucket_pab" {
  bucket = aws_s3_bucket.college_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "college_bucket_cors" {
  bucket = aws_s3_bucket.college_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

###############################################################################
# 8. RDS Subnet Group
###############################################################################

resource "aws_db_subnet_group" "college_db_subnet_group" {
  name        = "${var.project_name}-db-subnet-group"
  description = "Private subnet group for College Management RDS"
  subnet_ids  = [
    aws_subnet.private_subnet_az1.id,
    aws_subnet.private_subnet_az2.id,
  ]

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

###############################################################################
# 9. RDS Instance
###############################################################################

resource "aws_db_instance" "college_rds" {
  identifier = "${var.project_name}-rds"

  engine         = "mysql"
  instance_class = var.rds_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "college_management"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.college_db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  publicly_accessible    = false
  multi_az               = false
  deletion_protection    = true

  backup_retention_period   = 1
  backup_window             = "02:00-03:00"
  maintenance_window        = "sun:03:30-sun:04:30"
  auto_minor_version_upgrade = true

  skip_final_snapshot       = false
  final_snapshot_identifier = "college-final-snapshot"

  performance_insights_enabled = false

  tags = {
    Name = "${var.project_name}-rds"
  }
}

###############################################################################
# 10. EC2 Instance
###############################################################################

resource "aws_instance" "app_server" {
  ami           = var.ubuntu_ami
  instance_type = var.ec2_instance_type

  subnet_id                   = aws_subnet.public_subnet.id
  vpc_security_group_ids      = [aws_security_group.ec2_sg.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  key_name                    = var.key_pair_name
  associate_public_ip_address = true

  user_data = file("${path.module}/user_data.sh")

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true

    tags = {
      Name = "${var.project_name}-root-volume"
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"   # IMDSv2 enforced
    http_put_response_hop_limit = 1
  }

  tags = {
    Name = "${var.project_name}-app-server"
  }

  lifecycle {
    ignore_changes = [user_data]
  }
}

###############################################################################
# 11. Elastic IP
###############################################################################

resource "aws_eip" "app_eip" {
  instance = aws_instance.app_server.id
  domain   = "vpc"

  depends_on = [aws_internet_gateway.igw]

  tags = {
    Name = "${var.project_name}-eip"
  }
}
