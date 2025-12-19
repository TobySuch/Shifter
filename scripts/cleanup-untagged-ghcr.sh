#!/usr/bin/env bash
# Deletes untagged GHCR image versions for a package; run with
# GH_TOKEN=... OWNER=... [PACKAGE=shifter] [DRY_RUN=1] scripts/cleanup-untagged-ghcr.sh
set -euo pipefail

export GH_PAGER=cat

PACKAGE="shifter"

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "GH_TOKEN is required (token needs packages:read, packages:delete)." >&2
  exit 1
fi

if [[ -z "${OWNER:-}" || -z "${PACKAGE:-}" ]]; then
  echo "OWNER and PACKAGE are required (e.g., OWNER=tobysuch PACKAGE=shifter)." >&2
  exit 1
fi

owner_type=$(gh api -H "Accept: application/vnd.github+json" \
  /users/$OWNER --jq '.type')
if [[ "$owner_type" == "Organization" ]]; then
  base_path="/orgs/$OWNER"
else
  base_path="/users/$OWNER"
fi

versions=$(gh api -H "Accept: application/vnd.github+json" \
  "$base_path/packages/container/$PACKAGE/versions" --paginate \
  --jq '.[] | select(.metadata.container.tags | length == 0) | .id')

if [[ -z "$versions" ]]; then
  echo "No untagged versions found for $OWNER/$PACKAGE."
  exit 0
fi

if [[ "${DRY_RUN:-}" == "1" ]]; then
  echo "Untagged version IDs for $OWNER/$PACKAGE:"
  echo "$versions"
  exit 0
fi

version_ids=()
while IFS= read -r id; do
  [[ -n "$id" ]] || continue
  version_ids+=("$id")
done <<< "$versions"
total="${#version_ids[@]}"
echo "Found $total untagged version(s) to delete for $OWNER/$PACKAGE."

deleted=0
for id in "${version_ids[@]}"; do
  gh api -X DELETE -H "Accept: application/vnd.github+json" \
    "$base_path/packages/container/$PACKAGE/versions/$id"
  deleted=$((deleted + 1))
  echo "$deleted. Deleted version $id."

done

echo "Deleted $deleted untagged version(s) for $OWNER/$PACKAGE."
