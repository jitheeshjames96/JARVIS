#!/bin/bash
# Deploy JARVIS voice API to GCP (browser mic + agent chat)
set -euo pipefail
PROJECT="jarvis-jitheesh-2026"
REGION="asia-south1"
FUNCTION="jarvis-voice-api"
ACCOUNT="jitheeshjames27@gmail.com"
cd "$(dirname "$0")/.."

gcloud config configurations activate jarvis-personal
gcloud config set account "$ACCOUNT"
gcloud config set project "$PROJECT"

gcloud functions deploy "$FUNCTION" \
  --gen2 \
  --runtime=python311 \
  --region="$REGION" \
  --source=gcp/voice_api \
  --entry-point=voice_api \
  --trigger-http \
  --allow-unauthenticated \
  --memory=256Mi \
  --timeout=30s \
  --max-instances=3 \
  --project="$PROJECT"

URL=$(gcloud functions describe "$FUNCTION" --gen2 --region="$REGION" --project="$PROJECT" \
  --format='value(serviceConfig.uri)')
echo "Voice API URL: $URL"
echo "Add to config/gcp.yaml: voice_api_url: $URL"
