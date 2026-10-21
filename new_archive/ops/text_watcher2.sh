#!/bin/bash
# every 5 minutes: store the text of any finished month (a results.csv not yet stored) on the data branch; stops after the fetch queue is done and everything is stored
S=/tmp/claude-0/-home-user-recourse-sci-pool/4a13d2e5-1eb7-514e-ba65-a54131f7576c/scratchpad
D=/home/user/recourse-sci-court-newer
while true; do
  cd /home/user/recourse-sci-pool
  todo=$(python3 - <<P
import json,glob,csv,os
d=json.load(open("$D/state/processed.json")) if os.path.exists("$D/state/processed.json") else {}
print(" ".join(f for f in sorted(glob.glob("new_archive/*/results.csv")) if d.get(f)!=sum(1 for _ in csv.DictReader(open(f)))))
P
)
  if [ -n "$todo" ]; then
    python3 -I -W ignore new_archive/store_text.py $S/pdfs_all $D $todo 2>&1 | tail -2
    cd $D && git add -A && git commit -q -m "Text of newly fetched judgments ($(echo $todo | wc -w) result files)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BKA5VmevDP2GsevzgKkDnc" && git push -q origin claude/sci-court-newer && echo "stored+pushed $(date +%T): $todo"
  fi
  if grep -q -E "QUEUE2 DONE|BLOCKED" /tmp/claude-0/run_queue2.log /tmp/claude-0/run_queue.log && [ -z "$todo" ]; then echo WATCHER DONE; exit 0; fi
  sleep 300
done
