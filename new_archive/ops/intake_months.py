"""Turns the owner's uploaded link files (new_archive/SCI judgements/<year> full/links_*.txt) into month folders new_archive/YYYY-MM/links_all.txt (skips months that already have one)."""
import glob, os, re
for f in sorted(glob.glob('new_archive/SCI judgements/*/links_*.txt')):
    m = re.search(r'links_(\d\d)-(\d\d)-(\d{4})_to_(\d\d)-(\d\d)-(\d{4})', f)
    if not m: continue
    d = f'new_archive/{m.group(3)}-{m.group(2)}'
    if os.path.exists(d + '/links_all.txt'): continue
    txt = open(f, 'rb').read().decode('utf-8-sig').replace('\r', '')
    L = [l.strip() for l in txt.splitlines() if l.strip().startswith('https://')]
    os.makedirs(d, exist_ok=True); open(d + '/links_all.txt', 'w').write('\n'.join(L) + '\n'); print('new month folder', d, len(L))
