# CDN Automation Practice Lab (Cloudflare → Akamai concepts)

A small, real project that practices everything in the Akamai platform-engineer job description:
edge properties and routing, DNS, security controls, Terraform + Python automation, API usage,
and CI/CD with automated validation.

```
User ──► DNS (Cloudflare) ──► CDN edge: redirects, WAF, cache, headers ──► Origin (GitHub Pages)
                                         ▲
             GitHub Actions: test ► terraform plan ► approval ► apply ► validate.py
```

## What's in here

| Path | What it does | Akamai equivalent |
|---|---|---|
| `terraform/dns.tf` | www + apex records (proxied), a DNS-only origin record, CAA records | Edge DNS zone and records; `AKAMAICDN` apex record |
| `terraform/rules.tf` | TLS settings, apex→www redirect, cache rules, security headers, WAF rules | Property Manager rule tree, CPS, App & API Protector |
| `scripts/validate.py` | Live checks: status, redirects, cache HIT, headers. Non-zero exit fails the pipeline | Validation with Pragma debug headers against staging |
| `scripts/checks.json` | The test cases, as data | Same idea |
| `scripts/purge.py` | Purge by URL or everything via API | Fast Purge (CCU v3) API with EdgeGrid |
| `scripts/dns_check.py` | Shows CNAME/A/AAAA answers and TTLs | Checking the `.edgekey.net` CNAME chain |
| `tests/test_validate.py` | Unit tests for the validation logic | — |
| `.github/workflows/cdn-deploy.yml` | Test → plan → gated apply → validate | Staging activation → tests → production activation |
| `docs/` | The tiny website (origin) | Your origin server |

---

## Step 1 — Accounts and domain (one time)

1. Create a free account at **cloudflare.com** (Free plan).
2. Buy a cheap domain (Cloudflare Registrar, Porkbun, Namecheap…).
3. In Cloudflare: **Add a domain** → choose Free → change the nameservers at your registrar to the two Cloudflare gives you. Wait until the zone shows **Active**.
4. Copy the **Zone ID** and **Account ID** from the domain's Overview page (right sidebar).

## Step 2 — Origin website (GitHub Pages)

1. Push this repo to GitHub.
2. Edit `docs/CNAME` so it contains `www.yourdomain.com` (create it if needed).
3. Repo **Settings → Pages** → Source: *Deploy from a branch* → `main` / `/docs`.
4. Your origin hostname is `<your-github-username>.github.io`.

## Step 3 — API token

Cloudflare dashboard → **My Profile → API Tokens → Create Token → Custom token** with:
- Zone → DNS → Edit
- Zone → Zone Settings → Edit
- Zone → Zone WAF → Edit
- Zone → Cache Rules → Edit
- Zone → Dynamic Redirect → Edit
- Zone → Transform Rules → Edit
- Zone → Cache Purge → Purge

Limit it to your one zone. (Principle of least privilege — say this in the interview.)

## Step 4 — Run Terraform locally

```bash
export CLOUDFLARE_API_TOKEN=...          # never put it in a file you commit
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in zone_id, domain, origin_hostname
terraform init
terraform plan        # read it! what will change?
terraform apply
```

> If your zone already has DNS records with the same names (Cloudflare imports existing records when you add a domain), delete them in the dashboard first, or bring them under Terraform with `terraform import` — good practice for the "we have UI-created config, how do we move it to IaC?" interview question.

## Step 5 — Validate

```bash
pip install -r requirements.txt
pytest -q                                            # unit tests
python scripts/validate.py --domain yourdomain.com   # live checks
python scripts/dns_check.py yourdomain.com www.yourdomain.com origin.yourdomain.com
python scripts/purge.py --zone-id <ZONE_ID> --url https://www.yourdomain.com/static/style.css
```

Handy curl commands:

```bash
curl -sI https://www.yourdomain.com/static/style.css | grep -iE "cf-cache-status|cache-control|age"
curl -sI https://yourdomain.com/about               # 301 to www
curl -sI https://www.yourdomain.com/wp-login.php    # 403 from WAF
curl -sI https://origin.yourdomain.com/             # bypasses the CDN: compare headers
dig www.yourdomain.com +short                       # Cloudflare IPs, not GitHub's
```

## Step 6 — CI/CD

### Remote state
A pipeline can't use state on your laptop. Store it in Cloudflare **R2** (S3-compatible, free tier):
1. Dashboard → R2 → create bucket `tf-state`; create an R2 API token (gives an access key + secret).
2. Uncomment the `backend "s3"` block in `terraform/versions.tf`.
3. Locally: `terraform init -migrate-state -backend-config='endpoints={s3="https://<ACCOUNT_ID>.r2.cloudflarestorage.com"}'` (with the R2 keys exported as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`).

### GitHub settings
- **Secrets:** `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
- **Variables:** `DOMAIN`, `ORIGIN_HOSTNAME`
- **Environment** `production` with yourself as a required reviewer → manual approval gate.

Now: open a PR → tests + plan run. Merge → approve → apply → live validation.

---

## Practice exercises (do these, then talk about them)

1. **Break it on purpose.** Change the cache rule path to `/assets/`, push, and watch `validate.py` fail the pipeline. Fix with `git revert`. → *"How do you roll back?"*
2. **Cache key.** Request `/static/style.css?v=1` and `?v=2` — two cache entries. Exclude the query string from the cache key and compare. → *"What is a cache key?"*
3. **Origin outage.** Point `origin_hostname` at something that doesn't exist, apply, observe the 5xx, then troubleshoot edge vs origin using the `origin.` record. → *"Users see 503s — what do you do?"*
4. **Import drift.** Add a rule in the dashboard by hand, run `terraform plan`, and decide: import it or remove it. → *"How do you handle config drift?"*
5. **WAF tuning.** Change a block rule to `log` first, review Security Events, then switch to `block`. → *"How do you roll out a WAF rule safely?"*
6. **Cutover.** Lower a record's TTL to 60, change its target, then raise it again. → *"How do you migrate DNS with minimal risk?"*

## How to describe this in the interview

> "To get hands-on with CDN automation I built a small pipeline: DNS, redirects, caching, security headers and WAF rules are all Terraform; a Python validator checks redirects, cache hits and headers against the live edge and fails the pipeline if anything regresses; and GitHub Actions runs test, plan, an approval gate, apply and validation. I used Cloudflare's free tier, but each piece maps directly to Akamai — rules to Property Manager behaviors, the apply-then-validate flow to staging and production activations, and the purge script to Fast Purge."

## Notes
- Written for the Cloudflare Terraform provider **v5** (`cloudflare_dns_record`, list-style `rules = [...]`). Older blog posts use v4 names like `cloudflare_record` and block syntax — they won't work here.
- Free plan limits apply (number of custom WAF rules, rate-limiting options). Rate limiting is left out so `apply` works on Free.
