import os,json
os.chdir('/data/fix'); files=[]
for root,_,fs in os.walk('.'):
    if '__pycache__' in root: continue
    for f in fs:
        p=os.path.join(root,f)[2:]
        files.append({"path":"review-scripts/"+p,"content":open(p).read()})
json.dump({"owner":"DimskOfficial","repo":"Spark","branch":"wip/review-scripts","message":"backup review scripts","files":files},open('/data/backup.json','w'))
print(len(files))
