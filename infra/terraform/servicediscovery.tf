# Private DNS namespace so services can find each other by name inside the VPC,
# the same way they do by service name in docker-compose. The worker resolves
# the fetcher at fetcher.breachatlas.local:8001 — and only the worker's security
# group is allowed to connect there.
resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "breachatlas.local"
  description = "Internal service discovery for ${local.name}"
  vpc         = aws_vpc.main.id
}

resource "aws_service_discovery_service" "fetcher" {
  name = "fetcher"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}
