# ---------------------------------------------------------------------------
# Edge rules  (Akamai equivalent: Property Manager rule tree)
#   expression        ~ criteria (match on path, host, extension...)
#   action/parameters ~ behaviors (redirect, caching, headers...)
# ---------------------------------------------------------------------------

# TLS settings (Akamai: certificate + "Redirect HTTP to HTTPS" behavior)
resource "cloudflare_zone_setting" "ssl_mode" {
  zone_id    = var.zone_id
  setting_id = "ssl"
  value      = "full" # encrypt CDN -> origin too; use "strict" once origin cert is valid
}

resource "cloudflare_zone_setting" "always_https" {
  zone_id    = var.zone_id
  setting_id = "always_use_https"
  value      = "on"
}

resource "cloudflare_zone_setting" "min_tls" {
  zone_id    = var.zone_id
  setting_id = "min_tls_version"
  value      = "1.2"
}

# Redirects (Akamai: Redirect behavior or Edge Redirector Cloudlet)
resource "cloudflare_ruleset" "redirects" {
  zone_id     = var.zone_id
  name        = "Redirect rules"
  description = "Canonical host redirects"
  kind        = "zone"
  phase       = "http_request_dynamic_redirect"

  rules = [
    {
      ref         = "apex_to_www"
      description = "301 example.com -> www.example.com, keep path and query"
      expression  = "(http.host eq \"${var.domain}\")"
      action      = "redirect"
      action_parameters = {
        from_value = {
          status_code           = 301
          preserve_query_string = true
          target_url = {
            expression = "concat(\"https://www.${var.domain}\", http.request.uri.path)"
          }
        }
      }
    }
  ]
}

# Caching (Akamai: Caching behavior, Downstream Cacheability, cache keys)
resource "cloudflare_ruleset" "cache" {
  zone_id     = var.zone_id
  name        = "Cache rules"
  description = "Edge and browser caching policy"
  kind        = "zone"
  phase       = "http_request_cache_settings"

  rules = [
    {
      ref         = "cache_static"
      description = "Cache /static/* at the edge and in browsers"
      expression  = "(starts_with(http.request.uri.path, \"/static/\"))"
      action      = "set_cache_settings"
      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = var.static_edge_ttl
        }
        browser_ttl = {
          mode    = "override_origin"
          default = var.static_browser_ttl
        }
        cache_key = {
          ignore_query_strings_order = true
        }
      }
    },
    {
      ref         = "bypass_api"
      description = "Never cache /api/* (personalized or dynamic data)"
      expression  = "(starts_with(http.request.uri.path, \"/api/\"))"
      action      = "set_cache_settings"
      action_parameters = {
        cache = false
      }
    }
  ]
}

# Response headers (Akamai: Modify Outgoing Response Header behavior)
resource "cloudflare_ruleset" "security_headers" {
  zone_id     = var.zone_id
  name        = "Response header rules"
  description = "Add security headers to every response"
  kind        = "zone"
  phase       = "http_response_headers_transform"

  rules = [
    {
      ref         = "security_headers"
      description = "Baseline security headers"
      expression  = "true"
      action      = "rewrite"
      action_parameters = {
        headers = {
          "Strict-Transport-Security" = { operation = "set", value = "max-age=31536000" }
          "X-Content-Type-Options"    = { operation = "set", value = "nosniff" }
          "X-Frame-Options"           = { operation = "set", value = "DENY" }
          "Referrer-Policy"           = { operation = "set", value = "strict-origin-when-cross-origin" }
        }
      }
    }
  ]
}

# WAF custom rules (Akamai: App & API Protector custom rules / IP-geo firewall)
resource "cloudflare_ruleset" "waf_custom" {
  zone_id     = var.zone_id
  name        = "WAF custom rules"
  description = "Simple custom firewall rules"
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  rules = [
    {
      ref         = "block_wp_probes"
      description = "Block common WordPress probing (we don't run WordPress)"
      expression  = "(starts_with(http.request.uri.path, \"/wp-admin\") or http.request.uri.path eq \"/wp-login.php\" or http.request.uri.path eq \"/xmlrpc.php\")"
      action      = "block"
    },
    {
      ref         = "challenge_admin"
      description = "Managed challenge on /admin from outside the US (practice geo rule)"
      expression  = "(starts_with(http.request.uri.path, \"/admin\") and ip.src.country ne \"US\")"
      action      = "managed_challenge"
    }
  ]
}
# Bot protection (Akamai equivalent: Bot Manager settings in the security policy)
# Bot Fight Mode is off because it challenges our CI validator from GitHub's
# datacenter IPs, and on the Free plan it can't be bypassed with WAF skip rules.
resource "cloudflare_bot_management" "bots" {
  zone_id    = var.zone_id
  fight_mode = false
}
