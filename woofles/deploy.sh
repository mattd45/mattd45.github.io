#!/usr/bin/env bash
# Deploy the Woofles site to an S3 static website bucket.
#
#   ./deploy.sh my-bucket-name [aws-region]
#
# Needs the AWS CLI configured with credentials that can create and write to
# S3 buckets. Safe to re-run: it creates what is missing and syncs the rest.

set -euo pipefail

BUCKET="${1:-}"
REGION="${2:-eu-west-2}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "$BUCKET" ]]; then
  echo "usage: $0 <bucket-name> [region]   (default region: eu-west-2 / London)" >&2
  exit 1
fi

echo "==> Bucket: s3://$BUCKET   Region: $REGION"

# 1. Create the bucket if it isn't there already.
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "==> Bucket already exists, reusing it"
else
  echo "==> Creating bucket"
  if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=$REGION"
  fi
fi

# 2. Allow public reads. Static marketing site, no private data — but if you'd
#    rather keep the bucket private, delete this block and put CloudFront with
#    an Origin Access Control in front of it instead.
echo "==> Allowing public read access"
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

aws s3api put-bucket-policy --bucket "$BUCKET" --policy "$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::$BUCKET/*"
  }]
}
JSON
)"

# 3. Turn on static website hosting.
echo "==> Enabling static website hosting"
aws s3api put-bucket-website --bucket "$BUCKET" --website-configuration \
  '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"index.html"}}'

# 4. Upload. Images get a long cache, the HTML a short one so edits show up.
echo "==> Uploading images"
aws s3 sync "$HERE" "s3://$BUCKET" \
  --exclude "*" --include "*.jpg" --include "*.png" \
  --cache-control "public,max-age=604800"

echo "==> Uploading index.html"
aws s3 cp "$HERE/index.html" "s3://$BUCKET/index.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "public,max-age=300"

# 5. Tidy up anything left over from a previous deploy.
aws s3 rm "s3://$BUCKET/README.md" --quiet 2>/dev/null || true
aws s3 rm "s3://$BUCKET/deploy.sh" --quiet 2>/dev/null || true
aws s3 rm "s3://$BUCKET/woofles-stand.jpg" --quiet 2>/dev/null || true

echo
echo "==> Done. Your site is live at:"
echo "    http://$BUCKET.s3-website.$REGION.amazonaws.com"
echo
echo "    (S3 website endpoints are HTTP only. For HTTPS and a custom domain,"
echo "     put CloudFront in front of the bucket.)"
