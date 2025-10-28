import csv
import requests
import tldextract

input_path = './top-1m.csv'
output = './top100.csv'


session = requests.Session()
def getDomain(url:str):
    ext = tldextract.extract(url)
    return ext.domain + "." + ext.suffix  # 二级域名

def open_url(url:str):
    f_url = url
    domain = getDomain(url) 
    if dictionary.get(domain) is not None: # 被重定向到一个已知的站点则无需访问
        return None
    # 标准化URL
    if f_url.startswith('https://') is False and f_url.startswith('http://') is False:
        f_url = 'https://' + url
        
    try:
        response = session.get(f_url, timeout=5,allow_redirects=False)
        if response.status_code == 200:
            return domain
        
         # 重定向
        elif 300 <= response.status_code < 400:
            redirect_url = response.headers.get("Location")
            if redirect_url:
                domain = getDomain(redirect_url) 
                if dictionary.get(domain) is not None:
                    return None
                else :
                    return open_url(redirect_url)                
            else:
                return ''
            
        else:
            return None
    except requests.RequestException:
        return None

res = []
dictionary = {}
with open(input_path,'r',newline='') as f:
    data = csv.reader(f,delimiter=',')
    i = 0
    next(data,None)
    for _,url,*_ in data:
        if i>149:
            break
        
        result = open_url(url)
        
        if result is not None and dictionary.get(result) == None:
            res.append([i,result])
            dictionary[result]=1
            i+=1
            print(i,'\n')
            
with open(output,'w',newline='') as f:
    writer = csv.writer(f,delimiter=',')
    writer.writerows(res)