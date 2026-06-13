#!/bin/bash
# Deploy Sentinel GCP prod monitor to jarvis-jitheesh-2026
# Account: jitheeshjames27@gmail.com | Profile: jarvis-personal
set -euo pipefail

PROJECT="jarvis-jitheesh-2026"
REGION="asia-south1"
FUNCTION="sentinel-gcp-monitor"
SCHEDULER_JOB="sentinel-gcp-hourly"
ACCOUNT="jitheeshjames27@gmail.com"
BUCKET="jarvis-jitheesh-2026"

cd "$(dirname "$0")/.."

echo "=== Sentinel GCP Deploy (prod) ==="
echo "Project: $PROJECT | Account: $ACCOUNT"

gcloud config configurations activate jarvis-personal
gcloud config set account "$ACCOUNT"
gcloud config set project "$PROJECT"

echo "Enabling APIs..."
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT"

echo "Deploying Cloud Function (Gen2)..."
gcloud functions deploy "$FUNCTION" \
  --gen2 \
  --runtime=python311 \
  --region="$REGION" \
  --source=gcp/sentinel \
  --entry-point=run_monitor \
  --trigger-http \
  --allow-unauthenticated \
  --memory=256Mi \
  --timeout=60s \
  --max-instances=1 \
  --project="$PROJECT"

FUNCTION_URL=$(gcloud functions describe "$FUNCTION" \
  --gen2 --region="$REGION" --project="$PROJECT" \
  --format='value(serviceConfig.uri)')

echo "Function URL: $FUNCTION_URL"

echo "Creating/updating Cloud Scheduler (hourly)..."
if gcloud scheduler jobs describe "$SCHEDULER_JOB" --location="$REGION" --project="$PROJECT" &>/dev/null; then
  gcloud scheduler jobs update http "$SCHEDULER_JOB" \
    --location="$REGION" \
    --schedule="0 * * * *" \
    --uri="$FUNCTION_URL" \
    --http-method=GET \
    --project="$PROJECT"
else
  gcloud scheduler jobs create http "$SCHEDULER_JOB" \
    --location="$REGION" \
    --schedule="0 * * * *" \
    --uri="$FUNCTION_URL" \
    --http-method=GET \
    --time-zone="Asia/Kolkata" \
    --project="$PROJECT"
fi

echo "Granting function SA storage access..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gsutil iam ch "serviceAccount:${SA}:objectAdmin" "gs://${BUCKET}" 2>/dev/null || true

echo "Running initial monitor invocation..."
curl -sf "$FUNCTION_URL" | python3 -m json.tool | head -30

echo ""
echo "=== Sentinel deployed ==="
echo "Scheduler: hourly (Asia/Kolkata)"
echo "Report: gs://${BUCKET}/ops/sentinel-report.json"
echo "Dashboard: https://storage.googleapis.com/${BUCKET}/dashboard.html"
