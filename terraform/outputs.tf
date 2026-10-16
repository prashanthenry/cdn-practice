output "site_url" {
  value = "https://www.${var.domain}"
}

output "origin_direct_url" {
  description = "Bypasses the CDN - compare responses with site_url when troubleshooting"
  value       = "https://origin.${var.domain}"
}

output "ruleset_ids" {
  value = {
    redirects        = cloudflare_ruleset.redirects.id
    cache            = cloudflare_ruleset.cache.id
    security_headers = cloudflare_ruleset.security_headers.id
    waf_custom       = cloudflare_ruleset.waf_custom.id
  }
}
