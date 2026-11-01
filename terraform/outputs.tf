###############################################################################
# College Management System – Terraform Outputs
###############################################################################

output "ec2_public_ip" {
  description = "Elastic (static) public IP address of the application server"
  value       = aws_eip.app_eip.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID of the application server"
  value       = aws_instance.app_server.id
}

output "rds_endpoint" {
  description = "RDS MySQL endpoint (host:port) – keep this secret"
  value       = aws_db_instance.college_rds.endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS MySQL port (default 3306)"
  value       = aws_db_instance.college_rds.port
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket used for college media and documents"
  value       = aws_s3_bucket.college_bucket.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.college_bucket.arn
}

output "vpc_id" {
  description = "ID of the College Management VPC"
  value       = aws_vpc.college_vpc.id
}

output "ec2_security_group_id" {
  description = "ID of the EC2 security group"
  value       = aws_security_group.ec2_sg.id
}

output "ssh_connection_command" {
  description = "SSH command to connect to the application server"
  value       = "ssh -i <your-key.pem> ubuntu@${aws_eip.app_eip.public_ip}"
}

output "application_url" {
  description = "URL to access the application"
  value       = var.app_domain != "" ? "http://${var.app_domain}" : "http://${aws_eip.app_eip.public_ip}"
}
