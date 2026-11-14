#!/usr/bin/env bash
# One-time Google Cloud setup so GitHub Actions can deploy the API to Cloud Run (.github/workflows/deploy-api.yml).
#
# Run it in Cloud Shell (the >_ button at the top of console.cloud.google.com), in a project that has
# billing enabled:
#   bash setup-gcp.sh <project-id>
#
# It is safe to run again: everything it creates is skipped if it already exists. It creates
#   - an Artifact Registry repository for the API image, keeping only the five newest images
#   - a deployer service account that GitHub signs in as, through Workload Identity Federation (no keys),
#     trusted only for this repository's main branch
#   - a runtime service account the API runs as, with no permissions (it only reads its own files)
# and prints the GitHub repository variables the workflow needs.
set -euo pipefail

PROJECT_ID="${1:?usage: bash setup-gcp.sh <project-id>}"
REGION="${REGION:-us-east1}"                       # a free-tier region, near Vercel's default (Washington, D.C.)
GITHUB_REPO="${GITHUB_REPO:-tsetan13821/NBAAnalyticsProject}"
REPOSITORY=nba-analytics
POOL=github
PROVIDER=github
DEPLOY_SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
RUNTIME_SA="nba-api-runtime@${PROJECT_ID}.iam.gserviceaccount.com"

step() { printf '\n== %s\n' "$*"; }

gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

step "Enabling the APIs"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com iam.googleapis.com \
  iamcredentials.googleapis.com sts.googleapis.com

step "Artifact Registry repository $REPOSITORY ($REGION)"
if ! gcloud artifacts repositories describe "$REPOSITORY" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" --repository-format=docker --location="$REGION" \
    --description="NBA Analytics API images"
fi
# Each deploy pushes a new image; keep the newest five so storage stays inside the free 0.5 GB.
policy=$(mktemp)
cat > "$policy" <<'JSON'
[
  {"name": "keep-newest", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 5}},
  {"name": "delete-older", "action": {"type": "Delete"}, "condition": {"tagState": "any", "olderThan": "1d"}}
]
JSON
gcloud artifacts repositories set-cleanup-policies "$REPOSITORY" --location="$REGION" \
  --policy="$policy" --no-dry-run >/dev/null
rm -f "$policy"

step "Service accounts"
created=
for sa in github-deployer nba-api-runtime; do
  if ! gcloud iam service-accounts describe "${sa}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$sa" --display-name="$sa"
    created=1
  fi
done
[ -n "$created" ] && sleep 20  # new accounts take a moment before they can be granted roles

step "Deployer permissions"
# Deploy Cloud Run services and make them public (run.admin), push images to this one repository,
# and run the service as the runtime account.
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$DEPLOY_SA" \
  --role=roles/run.admin --condition=None >/dev/null
gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY" --location="$REGION" \
  --member="serviceAccount:$DEPLOY_SA" --role=roles/artifactregistry.writer >/dev/null
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" --member="serviceAccount:$DEPLOY_SA" \
  --role=roles/iam.serviceAccountUser >/dev/null

step "Workload Identity Federation for $GITHUB_REPO"
if ! gcloud iam workload-identity-pools describe "$POOL" --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL" --location=global --display-name="GitHub Actions"
fi
if ! gcloud iam workload-identity-pools providers describe "$PROVIDER" --location=global \
    --workload-identity-pool="$POOL" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --location=global \
    --workload-identity-pool="$POOL" --display-name="GitHub" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository == '${GITHUB_REPO}' && assertion.ref == 'refs/heads/main'"
fi
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${GITHUB_REPO}" \
  >/dev/null

step "Done. Set these GitHub repository variables (Settings > Secrets and variables > Actions > Variables):"
cat <<EOF
GCP_PROJECT_ID=$PROJECT_ID
GCP_REGION=$REGION
GCP_WIF_PROVIDER=projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/providers/${PROVIDER}
GCP_DEPLOY_SA=$DEPLOY_SA
GCP_RUNTIME_SA=$RUNTIME_SA
EOF
