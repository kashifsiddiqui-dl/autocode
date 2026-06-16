output "zone_id" {
  description = "Route53 hosted zone ID"
  value       = local.zone_id
}

output "fqdn" {
  description = "Fully qualified domain name of the application"
  value       = aws_route53_record.app.fqdn
}

output "name_servers" {
  description = "Name servers for the hosted zone (only if zone was created)"
  value       = var.create_zone ? aws_route53_zone.main[0].name_servers : []
}
