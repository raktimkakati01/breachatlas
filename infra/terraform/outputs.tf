output "alb_dns_name" {
  description = "Public DNS name of the load balancer. Point your domain's CNAME here."
  value       = aws_lb.main.dns_name
}

output "ecr_repository_urls" {
  description = "ECR repository URLs to push images to."
  value       = { for k, r in aws_ecr_repository.repo : k => r.repository_url }
}

output "rds_endpoint" {
  description = "RDS endpoint (host:port). Reachable only from inside the VPC."
  value       = aws_db_instance.main.endpoint
}

output "db_secret_arn" {
  description = "Secrets Manager ARN holding the DB credentials and connection URL."
  value       = aws_secretsmanager_secret.db.arn
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.main.name
}

output "vpc_id" {
  description = "VPC ID."
  value       = aws_vpc.main.id
}
