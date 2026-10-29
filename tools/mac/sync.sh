#!/bin/bash
# Copies new or changed Zwift workouts from GitHub into Zwift's custom workouts folder.
# Installed by install.sh as a launchd job (every 30 min and at login). Safe to run by hand.
set -u
REPO="amizuno92/ironman-cairns-2027"
ZWIFT_ID="8422202"
DEST="$HOME/Documents/Zwift/Workouts/$ZWIFT_ID"
HERE="$HOME/Documents/Zwift/Workouts/.ironman-sync"
STATE="$HERE/state"
LOG="$HERE/sync.log"
mkdir -p "$STATE"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

if [ ! -d "$DEST" ]; then log "Zwift folder not found: $DEST"; exit 1; fi
if ! curl -fsS --max-time 30 -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$REPO/contents/workouts/zwo" -o "$TMP/list.json"; then
  log "Couldn't reach GitHub (offline?). Will retry next run."; exit 0
fi

# name, sha, download_url appear in that order for each file
grep -oE '"(name|sha|download_url)": *"[^"]*"' "$TMP/list.json" \
  | sed -E 's/"([a-z_]+)": *"([^"]*)"/\1 \2/' \
  | awk '$1=="name"{n=$2} $1=="sha"{s=$2} $1=="download_url"{print n, s, $2}' > "$TMP/files.txt"

new=0; upd=0; fail=0
while read -r name sha url; do
  case "$name" in *.zwo) ;; *) continue ;; esac
  if [ -f "$DEST/$name" ] && [ "$(cat "$STATE/$name.sha" 2>/dev/null)" = "$sha" ]; then continue; fi
  if ! curl -fsS --max-time 30 "$url" -o "$TMP/$name"; then fail=$((fail+1)); continue; fi
  if [ -f "$DEST/$name" ]; then
    if ! cmp -s "$TMP/$name" "$DEST/$name"; then cp "$TMP/$name" "$DEST/$name" && upd=$((upd+1)); fi
  else
    cp "$TMP/$name" "$DEST/$name" && new=$((new+1))
  fi
  echo "$sha" > "$STATE/$name.sha"
done < "$TMP/files.txt"

total=$(wc -l < "$TMP/files.txt" | tr -d ' ')
if [ $((new+upd+fail)) -gt 0 ]; then log "checked $total: added $new, updated $upd, failed $fail"; fi
[ -f "$LOG" ] && tail -n 300 "$LOG" > "$TMP/log" && cp "$TMP/log" "$LOG"
exit 0
