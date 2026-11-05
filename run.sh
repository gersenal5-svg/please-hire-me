#!/usr/bin/env bash
# please-hire-me (approval fork). The original run.sh found AND submitted in one go. This fork splits
# that in two so nothing is sent without your yes:
#   ./find.sh     find and vet listings (never submits)
#   ./review.sh   approve or reject each one
#   ./apply.sh    submit only what you approved
# run.sh is kept as an alias for ./find.sh so old habits and old schedules can never auto-submit.
cd "$(dirname "$0")"
echo "run.sh now only FINDS listings. Approve them with ./review.sh, then submit with ./apply.sh."
exec ./find.sh "$@"
