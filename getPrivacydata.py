import csv
import json

inp = './result.json'
out = 'privacy.csv'

l = []
with open(inp,'r') as f:
    data:dict = json.load(f)
    for url,info in data.items():
        info:dict
        t = [url]
        links = info.get("privacy_possible_links",[])
        if len(links) != 0:
            linkstr = ''
            for link in links:
                linkstr+=link+' '
            t.append(linkstr)
        l.append(t)
    
with open(out,'w',newline='') as f:
    csv.writer(f,delimiter=',').writerows(l)
