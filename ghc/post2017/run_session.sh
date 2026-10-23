#!/bin/bash
# One work session of the post-2017 Guwahati fetch (owner approved 2026-10-23). Usage: run_session.sh SECONDS
# Pulls code and data, fetches for SECONDS, commits and pushes ONLY the data branch claude/ghc-bucket (shards_post2017/). Never merges, never touches other branches.
SECS=${1:-3000}
CODE=/home/user/recourse-sci-pool; DATA=/home/user/recourse-ghc-bucket
cd $CODE && git pull -q --rebase origin claude/elegant-lovelace-xb15i2 2>&1 | tail -1
cd $DATA && git pull -q --rebase origin claude/ghc-bucket 2>&1 | tail -1
cd $CODE && python3 -I ghc/post2017/fetch_post2017.py ghc/post2017/worklist_criminal_2018_2026.csv.gz $DATA $SECS 2>&1 | tail -30
cd $DATA && git add -A shards_post2017 >/dev/null 2>&1
if ! git diff --cached --quiet; then
  git commit -qm "Guwahati post-2017 criminal-type documents: monthly shards (open bucket)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BKA5VmevDP2GsevzgKkDnc"
  for i in 1 2 3; do git pull -q --rebase origin claude/ghc-bucket 2>&1 | tail -1; git push -q origin claude/ghc-bucket 2>&1 | tail -1 && break; sleep 5; done
fi
git log -1 --format='data branch head: %h %ci' | cut -c1-80; du -sh $DATA/shards_post2017 2>/dev/null | cut -f1
