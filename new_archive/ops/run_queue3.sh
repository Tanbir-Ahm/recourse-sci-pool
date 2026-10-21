#!/bin/bash
# queue 3: after queue 1, repeatedly (a) pulls the owner's uploads from GitHub, (b) turns new link files into month folders, (c) fetches every pending month, newest year first,
# never two fetches at once. Finishes ("QUEUE2 DONE" in run_queue2.log) when 2017 to 2019 are all fetched and nothing is pending; stops at once on a block.
cd /home/user/recourse-sci-pool
while true; do
  for i in 1 2 3; do git pull -q --rebase origin claude/elegant-lovelace-xb15i2 && break; sleep 10; done
  python3 - <<'P'
import glob,re,os
for f in sorted(glob.glob('new_archive/SCI judgements/*/links_*.txt')):
    m=re.search(r'links_(\d\d)-(\d\d)-(\d{4})_to_(\d\d)-(\d\d)-(\d{4})',f)
    if not m: continue
    d=f'new_archive/{m.group(3)}-{m.group(2)}'
    if os.path.exists(d+'/links_all.txt'): continue
    txt=open(f,'rb').read().decode('utf-8-sig').replace('\r','')
    L=[l.strip() for l in txt.splitlines() if l.strip().startswith('https://')]
    os.makedirs(d,exist_ok=True); open(d+'/links_all.txt','w').write('\n'.join(L)+'\n'); print('new month folder',d,len(L))
P
  pend=$(for d in $(ls -d new_archive/20[0-9][0-9]-[0-9][0-9]* 2>/dev/null); do [ -f $d/links_all.txt ] && [ ! -f $d/results.csv ] && [ -s $d/links_all.txt ] && echo $d; done | sort -r)
  if [ -n "$pend" ]; then
    git add new_archive >/dev/null 2>&1; git commit -q -m "Link lists from the owner's upload normalised into month folders

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BKA5VmevDP2GsevzgKkDnc" 2>/dev/null; git push -q origin claude/elegant-lovelace-xb15i2 2>/dev/null
    Y=$(echo "$pend" | head -1 | sed -E 's#new_archive/([0-9]{4})-.*#\1#')
    echo "=== year $Y start $(date +%T)"
    /tmp/claude-0/run_year2.sh $Y > /tmp/claude-0/run_$Y.b.log 2>&1
    tail -2 /tmp/claude-0/run_$Y.b.log
    if grep -q BLOCKED /tmp/claude-0/run_$Y.b.log; then echo "BLOCKED in $Y - queue 3 stopped"; exit 1; fi
    continue
  fi
  # nothing pending: finished only when 2019 and 2018 have 12 months of results and 2017 reaches December
  have=$(for y in 2019 2018; do ls -d new_archive/$y-[0-9][0-9] 2>/dev/null | while read d; do [ -f $d/results.csv ] && echo $d; done; done | wc -l)
  dec17=$(ls new_archive/SCI\ judgements/2017*/links_*-12-2017.txt 2>/dev/null | wc -l)
  if [ "$have" -ge 24 ] && [ "$dec17" -ge 1 ]; then echo "QUEUE2 DONE"; exit 0; fi
  sleep 120
done
