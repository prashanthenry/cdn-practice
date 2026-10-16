# ---------------------------------------------------------------------------
# DNS  (Akamai equivalent: Edge DNS zone + records)
# ---------------------------------------------------------------------------

# www -> origin, proxied through the CDN.
# proxied = true is like pointing www at an Akamai edge hostname:
# traffic now flows user -> CDN edge -> origin.
resource "cloudflare_dns_record" "www" {
  zone_id = var.zone_id
  name    = "www.${var.domain}"
  type    = "CNAME"
  content = var.origin_hostname
  proxied = true
  ttl     = 1 # 1 = "automatic"; required for proxied records
  comment = "Managed by Terraform - www behind the CDN"
}

# Apex (example.com) -> origin.
# A plain CNAME isn't allowed at the zone apex by the DNS standard.
# Cloudflare solves it with "CNAME flattening"; Akamai solves it with the
# AKAMAICDN record type. Good interview talking point.
resource "cloudflare_dns_record" "apex" {
  zone_id = var.zone_id
  name    = var.domain
  type    = "CNAME"
  content = var.origin_hostname
  proxied = true
  ttl     = 1
  comment = "Managed by Terraform - apex, redirected to www by a rule"
}

# A DNS-only (not proxied) record, so you can compare behavior:
# dig shows the real target, and responses have no cf-cache-status header.
resource "cloudflare_dns_record" "origin_direct" {
  zone_id = var.zone_id
  name    = "origin.${var.domain}"
  type    = "CNAME"
  content = var.origin_hostname
  proxied = false
  ttl     = 300
  comment = "Managed by Terraform - bypasses CDN, for troubleshooting"
}

# CAA: only these CAs may issue certificates for the domain.
resource "cloudflare_dns_record" "caa_letsencrypt" {
  zone_id = var.zone_id
  name    = var.domain
  type    = "CAA"
  ttl     = 3600
  data = {
    flags = 0
    tag   = "issue"
    value = "letsencrypt.org"
  }
}

resource "cloudflare_dns_record" "caa_google" {
  zone_id = var.zone_id
  name    = var.domain
  type    = "CAA"
  ttl     = 3600
  data = {
    flags = 0
    tag   = "issue"
    value = "pki.goog"
  }
}
