# usage: mkpush.py <base> <commit> <branch> <message-file> -> writes /data/push_<branch>.json (split if >900KB)
import subprocess, json, sys, os
base, commit, branch, msgf = sys.argv[1:5]
msg = open(msgf).read()
out = subprocess.check_output(['git','diff','--name-status','--no-renames',base,commit], cwd='/data/Spark', text=True)
files, deleted = [], []
for line in out.splitlines():
    st, path = line.split('\t',1)
    if st == 'D': deleted.append(path); continue
    data = subprocess.check_output(['git','show',f'{commit}:{path}'], cwd='/data/Spark')
    try: files.append({'path':path,'content':data.decode('utf-8')})
    except UnicodeDecodeError: print('BINARY', path)
chunks, cur, size = [], [], 0
for f in files:
    n = len(f['content'].encode())
    if cur and size + n > 900_000: chunks.append(cur); cur, size = [], 0
    cur.append(f); size += n
if cur: chunks.append(cur)
safe = branch.replace('/','_')
for i, c in enumerate(chunks):
    m = msg if len(chunks) == 1 else f"{msg}\n\n(part {i+1}/{len(chunks)})"
    json.dump({'owner':'DimskOfficial','repo':'Spark','branch':branch,'message':m,'files':c}, open(f'/data/push_{safe}_{i}.json','w'))
print('chunks', len(chunks), 'files', len(files), 'deleted', deleted)
