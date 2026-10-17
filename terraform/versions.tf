terraform {
  required_version = ">= 1.6"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }

  # Remote state (needed once you run Terraform from CI/CD).
  # Start with local state while learning; then uncomment this block and
  # follow "Remote state" in the README to store state in Cloudflare R2.
  #
  backend "s3" {
    bucket                      = "tf-state"
    key                         = "cdn-practice/terraform.tfstate"
    region                      = "auto"
    skip_credentials_validation = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true
    use_path_style              = true
    # endpoints.s3 is passed at init time: -backend-config="endpoints={s3=\"https://<ACCOUNT_ID>.r2.cloudflarestorage.com\"}"
  }
}

# Auth comes from the CLOUDFLARE_API_TOKEN environment variable,
# so no secret is ever written into code (same idea as Akamai's .edgerc).
provider "cloudflare" {}
