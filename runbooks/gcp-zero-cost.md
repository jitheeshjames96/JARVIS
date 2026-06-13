# JARVIS GCP — Near-Zero Cost Profile

**Project:** `jarvis-jitheesh-2026`  
**Estimated monthly cost:** ~$0.04 USD (well within free tier)

## What runs on GCP (not your laptop)

| Resource | Config | Monthly cost |
|----------|--------|--------------|
| GCS bucket | ~45 KB dashboard.html | ~$0.02 |
| Cloud Function `sentinel-gcp-monitor` | 256MB, max 1 instance, hourly | $0.00 (free tier) |
| Cloud Scheduler `sentinel-gcp-hourly` | 1 job | $0.00 (3 jobs free) |
| Egress | Minimal HTML fetches | ~$0.01 |

**No VMs, no Cloud SQL, no BigQuery jobs** — APIs are enabled but unused services cost nothing until invoked.

## Local vs cloud split (recommended)

| Task | Where | Why |
|------|-------|-----|
| GCP health monitoring | Cloud Function (hourly) | Zero laptop CPU |
| Dashboard hosting | GCS static URL | Always online |
| Dashboard data refresh | On-demand (voice) or optional 4h local | Avoids 30min polling |
| Personal reminders | Keeper launchd 2×/day | Lightweight, needs local personal.yaml |
| Voice (clap) | Local only | Optional — `--with-voice` flag |

## Keep cost at zero

1. **Do not** add Cloud SQL, GKE, or always-on Compute Engine to this project.
2. **Do not** enable BigQuery scheduled queries unless needed.
3. Sentinel scheduler at hourly is fine — stays in free tier (~720 invocations/month).
4. Dashboard HTML is static — no Cloud Run needed.

## Verify cost anytime

```bash
python3 scripts/devops_gcp_monitor.py
# Check cost section in gcp/sentinel monitor report
```

Billing alerts (optional, personal project only):
```bash
gcloud billing budgets create --billing-account=BILLING_ACCOUNT_ID \
  --display-name="JARVIS cap" --budget-amount=1USD \
  --threshold-rule=percent=50 --threshold-rule=percent=90
```
