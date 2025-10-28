import asyncio
import requests
from urllib.parse import urljoin, urlparse
import re
import csv
import json
from bs4 import BeautifulSoup
import time
import warnings
warnings.filterwarnings('ignore')

class GDPRComplianceChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.results = {}
        
    async def check_websites(self,urls):
        sem = asyncio.Semaphore(10)
        async def sem_task(url):
            async with sem:
                return await asyncio.to_thread(self._check_website, url)
        tasks = [sem_task(url) for url in urls]
        tsk_results = await asyncio.gather(*tasks)
        for url,result in zip(urls,tsk_results):
            self.results[url] =result
        
        return self.results


    def _check_website(self, url):
        """主检测函数"""
        print(f"🔍 开始检测网站: {url}")

        result = {'url': url}
        
        try:
            # 标准化URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            response = self.session.get(url, timeout=10, verify=False)
            response.raise_for_status()
            
            result['status_code'] = response.status_code
            # result['content_type'] = response.headers.get('content-type', '')
            
            # 执行各项检测
            self._check_cookies(response,result)
            self._check_privacy_policy(response, url,result)
            self._check_third_party_scripts(response,result)
            # self._check_ssl_encryption(url,result)
            # self._analyze_content(response,result)
            
        except requests.RequestException as e:
            result['error'] = str(e)
            print(f"❌ 请求错误: {e}")
            
        return result
    
    def _check_cookies(self, response, result):
        """检查Cookie使用情况"""
        print("🍪 分析Cookie使用...")
        cookie_analysis = {
            'cookies_found': [],
            'has_consent_banner': False,
            'keywords_or_selectors_hit':[],
            'http_only_cookies': 0,
            'secure_cookies': 0,
            'session_cookies': 0,
            'persistent_cookies': 0
        }
        
        # 检查响应中的Cookie
        cookies = response.cookies
        for cookie in cookies:
            cookie_info = {
                'name': cookie.name,
                'domain': cookie.domain,
                'expires': cookie.expires,
                'secure': cookie.secure,
                'httponly': cookie.has_nonstandard_attr('HttpOnly')
            }
            cookie_analysis['cookies_found'].append(cookie_info)
            
            if cookie.secure:
                cookie_analysis['secure_cookies'] += 1
            if cookie.has_nonstandard_attr('HttpOnly'):
                cookie_analysis['http_only_cookies'] += 1
            if cookie.expires:
                cookie_analysis['persistent_cookies'] += 1
            else:
                cookie_analysis['session_cookies'] += 1
        
        # 检查Cookie同意横幅
        soup = BeautifulSoup(response.text, 'html.parser')
        cookie_keywords = [
            'cookie', 'consent', 'gdpr', 'privacy', '跟踪', 'cookies',
            '同意', '隐私', 'cookie政策'
        ]
        
        text_content = soup.get_text().lower()
        for keyword in cookie_keywords:
            if keyword in text_content:
                cookie_analysis['has_consent_banner'] = True
                cookie_analysis['keywords_or_selectors_hit'].append(keyword)
                
                
        # 检查常见的Cookie横幅选择器
        cookie_selectors = [
            '.cookie-banner', '#cookie-consent', '.gdpr-banner',
            '.privacy-consent', '[class*="cookie"]', '[id*="cookie"]',
            '.cc-banner', '.consent-banner'
        ]
        
        for selector in cookie_selectors:
            if soup.select(selector):
                cookie_analysis['has_consent_banner'] = True
                cookie_analysis['keywords_or_selectors_hit'].append(selector)
                
                
        result['cookie_analysis'] = cookie_analysis
    
    def _check_privacy_policy(self, response, base_url, result):
        """检查隐私政策链接"""
        print("📄 查找隐私政策...")
        privacy_possible_links = []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        privacy_keywords = [
            'privacy', 'gdpr', '数据保护', '隐私政策', '隐私权',
            'privacy policy', 'datenschutz', 'confidentialité'
        ]
        
        # 在链接中查找隐私政策
        links = soup.find_all('a', href=True)
        for link in links:
            link_text = link.get_text(strip=True).lower()
            link_href = str(link.get('href',default='')).lower()
            
            for keyword in privacy_keywords:
                if keyword in link_text or keyword in link_href:
                    url = urljoin(base_url, str(link['href']))
                    privacy_possible_links.append(url)
                    break                
        result['privacy_possible_links'] = privacy_possible_links
    
    def _check_third_party_scripts(self, response, result):
        """检查第三方脚本"""
        print("🔗 分析第三方服务...")
        third_party_analysis = {
            'third_party_domains': [],
            'tracking_scripts': [],
            'social_media_widgets': [],
            'analytics_services': []
        }
        
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script', src=True)
        
        # 常见的第三方服务域名
        third_party_domains = [
            'google-analytics.com', 'googletagmanager.com', 'facebook.net',
            'doubleclick.net', 'hotjar.com', 'linkedin.com', 'twitter.com',
            'youtube.com', 'vimeo.com', 'addthis.com', 'sharethis.com',
            'stripe.com', 'paypal.com', 'disqus.com', 'cloudflare.com'
        ]
        
        analytics_keywords = ['analytics', 'gtag', 'ga.js', 'google-analytics']
        tracking_keywords = ['track', 'pixel', 'beacon', 'conversion']
        
        for script in scripts:
            src = str(script.get('src', ''))  # 确保是字符串
            domain = urlparse(src).netloc
            
            if domain and domain not in third_party_analysis['third_party_domains']:
                third_party_analysis['third_party_domains'].append(domain)
            
            # 分类分析
            src_lower = src.lower()
            if any(keyword in src_lower for keyword in analytics_keywords):
                third_party_analysis['analytics_services'].append(src)
            elif any(keyword in src_lower for keyword in tracking_keywords):
                third_party_analysis['tracking_scripts'].append(src)
            elif any(social in src_lower for social in ['facebook', 'twitter', 'linkedin', 'instagram']):
                third_party_analysis['social_media_widgets'].append(src)
                
        result['third_party_analysis'] = third_party_analysis
    
    def _check_ssl_encryption(self, url, result):
        """检查SSL加密"""
        
        # 我们检查的是 Top 级网站，我们相信它们不会使用不可信的 SSL
        print("🔒 检查SSL加密...")
        uses_https= False
        
        if url.startswith('https://'):
            uses_https = True
            
        result['uses_https'] = uses_https
    
    def _analyze_content(self, response, result):
        """分析页面内容"""
        print("📊 分析页面内容...")
        content_analysis = {
            'gdpr_keywords_found': [],
            'data_processing_mentions': False,
            'user_rights_mentioned': False
        }
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text().lower()
        
        gdpr_keywords = {
            'gdpr': 'GDPR',
            'general data protection regulation': 'GDPR全称',
            '数据保护': '数据保护',
            '个人信息': '个人信息',
            '用户权利': '用户权利',
            '数据主体': '数据主体',
            '数据处理': '数据处理',
            '数据控制者': '数据控制者',
            '同意': '同意',
            'opt-in': '选择加入',
            'opt-out': '选择退出',
            '数据泄露': '数据泄露',
            '数据可移植性': '数据可移植性',
            '被遗忘权': '被遗忘权'
        }
        
        for keyword, display_name in gdpr_keywords.items():
            if keyword in text_content:
                content_analysis['gdpr_keywords_found'].append(display_name)
        
        # 检查特定概念
        if any(word in text_content for word in ['数据处理', 'data processing']):
            content_analysis['data_processing_mentions'] = True
            
        if any(word in text_content for word in ['用户权利', '数据主体权利', 'data subject rights']):
            content_analysis['user_rights_mentioned'] = True
            
        result['content_analysis'] = content_analysis
    

def main():
    input = "./top100.csv"
    output = './result.json'
    
    with open(input,'r') as f:
        data = csv.reader(f)
        urls = [url for _,url in data]
    
    checker = GDPRComplianceChecker()
    results =asyncio.run(checker.check_websites(urls))
    with open(output,'w') as f:
        json.dump(results,f)

if __name__ == "__main__":
    _ =  main()