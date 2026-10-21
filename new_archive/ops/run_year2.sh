#!/bin/bash
# usage: run_year2.sh YEAR - fetches every month folder of the year that has links_all.txt and no results.csv yet; commits and pushes each; stops at once on a block
cd /home/user/recourse-sci-pool
S=/tmp/claude-0/-home-user-recourse-sci-pool/4a13d2e5-1eb7-514e-ba65-a54131f7576c/scratchpad
Y=$1
for d in $(ls -d new_archive/$Y-* 2>/dev/null | sort); do
  [ -f $d/links_all.txt ] && [ ! -f $d/results.csv ] || continue
  [ -s $d/links_all.txt ] || continue
  out=$(python3 -I -W ignore new_archive/first_pass.py $d/links_all.txt $S/pdfs_all $d/results.csv $S/refresh_20261005.csv.gz 2>&1 | tail -4)
  echo "$out"; echo "month $d done $(date +%T)"
  if echo "$out" | grep -q "STOP:"; then echo "BLOCKED - stopping, as the runbook requires"; exit 1; fi
  for i in 1 2 3; do
    git add $d && git commit -q -m "Fetch results for $d (court newer archive)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BKA5VmevDP2GsevzgKkDnc" && git pull -q --rebase origin claude/elegant-lovelace-xb15i2 && git push -q origin claude/elegant-lovelace-xb15i2 && break; sleep 5
  done
done
echo ALL DONE
