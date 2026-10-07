import json
BASE='/tmp/opencode'
data=json.load(open(BASE+'/data.json',encoding='utf-8'))
tpl=open(BASE+'/template.html',encoding='utf-8').read()
j=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
out=tpl.replace('__DATA__',j)
dst='/mnt/d/goethe/A1_Wortliste.html'
open(dst,'w',encoding='utf-8').write(out)
print('wrote',dst,len(out),'bytes; entries',len(data['entries']),'groups',len(data['groups']))
