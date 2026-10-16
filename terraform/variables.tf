variable "zone_id" {
  description = "Cloudflare zone ID for your domain (Dashboard > your domain > Overview, right sidebar)."
  type        = string
}

variable "domain" {
  description = "Your apex domain, e.g. example.com"
  type        = string
}

variable "origin_hostname" {
  description = "Where your site really lives, e.g. yourname.github.io (GitHub Pages) or an origin server hostname."
  type        = string
}

variable "static_edge_ttl" {
  description = "Seconds the CDN edge keeps /static/* in cache."
  type        = number
  default     = 86400
}

variable "static_browser_ttl" {
  description = "Seconds browsers keep /static/* in cache."
  type        = number
  default     = 3600
}
