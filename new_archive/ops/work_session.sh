#!/bin/bash
# One working session for the Supreme Court newer-archive fetch, run in the FOREGROUND of a turn (the container only runs while the session is active).
# usage: work_session.sh SECONDS   (default 3300). Fetches pending months, newest year first, until the time budget is used up or nothing is pending.
cd /home/user/recourse-sci-pool
END=$(( $(date +%s) + ${1:-3300} ))
while [ $(date +%s) -lt $END ]; do
  for i in 1 2 3; do git pull -q --rebase origin claude/elegant-lovelace-xb15i2 && break; sleep 10; done
  python3 new_archive/ops/intake_months.py
  pend=$(for d in $(ls -d new_archive/20[0-9][0-9]-[0-9][0-9] 2>/dev/null); do [ -f $d/links_all.txt ] && [ ! -f $d/results.csv ] && [ -s $d/links_all.txt ] && echo $d; done | sort -r)
  if [ -z "$pend" ]; then echo "NOTHING PENDING"; break; fi
  Y=$(echo "$pend" | head -1 | sed -E 's#new_archive/([0-9]{4})-.*#\1#')
  echo "=== year $Y $(date +%T), $(echo "$pend" | wc -l) months pending"
  timeout $(( END - $(date +%s) )) /tmp/claude-0/run_year2.sh $Y
  if grep -q "BLOCKED" /dev/null; then :; fi
done
echo "SESSION END $(date +%T)"
