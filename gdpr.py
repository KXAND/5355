import requests
from urllib.parse import urljoin, urlparse
import re
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
        
    def check_website(self, url):
        """主检测函数"""
        print(f"🔍 开始检测网站: {url}")
        self.results = {'url': url}
        
        try:
            # 标准化URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            response = self.session.get(url, timeout=10, verify=False)
            response.raise_for_status()
            
            self.results['status_code'] = response.status_code
            self.results['content_type'] = response.headers.get('content-type', '')
            
            # 执行各项检测
            self._check_cookies(response)
            self._check_privacy_policy(response, url)
            self._check_third_party_scripts(response)
            self._check_ssl_encryption(url)
            self._analyze_content(response)
            self._check_contact_info(response)
            
            # 生成合规评分
            self._calculate_compliance_score()
            
        except requests.RequestException as e:
            self.results['error'] = str(e)
            print(f"❌ 请求错误: {e}")
            
        return self.results
    
    def _check_cookies(self, response):
        """检查Cookie使用情况"""
        print("🍪 分析Cookie使用...")
        cookie_analysis = {
            'cookies_found': [],
            'has_consent_banner': False,
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
                break
                
        # 检查常见的Cookie横幅选择器
        cookie_selectors = [
            '.cookie-banner', '#cookie-consent', '.gdpr-banner',
            '.privacy-consent', '[class*="cookie"]', '[id*="cookie"]',
            '.cc-banner', '.consent-banner'
        ]
        
        for selector in cookie_selectors:
            if soup.select(selector):
                cookie_analysis['has_consent_banner'] = True
                break
                
        self.results['cookie_analysis'] = cookie_analysis
    
    def _check_privacy_policy(self, response, base_url):
        """检查隐私政策链接"""
        print("📄 查找隐私政策...")
        privacy_analysis = {
            'privacy_links_found': [],
            'policy_accessible': False,
            'policy_content': ''
        }
        
        soup = BeautifulSoup(response.text, 'html.parser')
        privacy_keywords = [
            'privacy', 'gdpr', '数据保护', '隐私政策', '隐私权',
            'privacy policy', 'datenschutz', 'confidentialité'
        ]
        
        # 在链接中查找隐私政策
        links = soup.find_all('a', href=True)
        for link in links:
            link_text = link.get_text().lower()
            link_href = link['href'].lower()
            
            for keyword in privacy_keywords:
                if keyword in link_text or keyword in link_href:
                    privacy_analysis['privacy_links_found'].append({
                        'text': link.get_text().strip(),
                        'href': link['href']
                    })
                    break
        
        # 尝试访问第一个找到的隐私政策链接
        if privacy_analysis['privacy_links_found']:
            first_link = privacy_analysis['privacy_links_found'][0]['href']
            try:
                policy_url = urljoin(base_url, first_link)
                policy_response = self.session.get(policy_url, timeout=5)
                if policy_response.status_code == 200:
                    privacy_analysis['policy_accessible'] = True
                    policy_soup = BeautifulSoup(policy_response.text, 'html.parser')
                    privacy_analysis['policy_content'] = policy_soup.get_text()[:500] + "..."
            except:
                pass
                
        self.results['privacy_analysis'] = privacy_analysis
    
    def _check_third_party_scripts(self, response):
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
            src = script['src']
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
                
        self.results['third_party_analysis'] = third_party_analysis
    
    def _check_ssl_encryption(self, url):
        """检查SSL加密"""
        print("🔒 检查SSL加密...")
        ssl_analysis = {'uses_https': False}
        
        if url.startswith('https://'):
            ssl_analysis['uses_https'] = True
            
        self.results['ssl_analysis'] = ssl_analysis
    
    def _analyze_content(self, response):
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
            
        self.results['content_analysis'] = content_analysis
    
    def _check_contact_info(self, response):
        """检查联系信息"""
        print("📞 查找联系信息...")
        contact_analysis = {
            'email_found': False,
            'phone_found': False,
            'contact_form': False,
            'dpo_mentioned': False
        }
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text()
        
        # 查找邮箱
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, text_content):
            contact_analysis['email_found'] = True
        
        # 查找电话
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        if re.search(phone_pattern, text_content):
            contact_analysis['phone_found'] = True
            
        # 查找联系表单
        form_selectors = ['form[action*="contact"]', 'form[id*="contact"]', 
                         'form[class*="contact"]', '#contact-form']
        for selector in form_selectors:
            if soup.select(selector):
                contact_analysis['contact_form'] = True
                break
                
        # 检查数据保护官提及
        dpo_keywords = ['数据保护官', 'DPO', 'Data Protection Officer']
        if any(keyword in text_content for keyword in dpo_keywords):
            contact_analysis['dpo_mentioned'] = True
            
        self.results['contact_analysis'] = contact_analysis
    
    def _calculate_compliance_score(self):
        """计算合规评分"""
        print("📈 计算合规评分...")
        score = 0
        max_score = 0
        issues = []
        recommendations = []
        
        # Cookie评分 (权重: 25%)
        max_score += 25
        cookie_analysis = self.results.get('cookie_analysis', {})
        if cookie_analysis.get('has_consent_banner'):
            score += 15
        else:
            issues.append("未发现明显的Cookie同意横幅")
            recommendations.append("添加明确的Cookie同意管理解决方案")
            
        if cookie_analysis.get('secure_cookies', 0) > 0:
            score += 10
        else:
            issues.append("未发现安全Cookie")
            recommendations.append("为所有Cookie设置Secure标志")
        
        # 隐私政策评分 (权重: 25%)
        max_score += 25
        privacy_analysis = self.results.get('privacy_analysis', {})
        if privacy_analysis.get('privacy_links_found'):
            score += 15
        else:
            issues.append("未找到隐私政策链接")
            recommendations.append("在网站显著位置添加隐私政策链接")
            
        if privacy_analysis.get('policy_accessible'):
            score += 10
        else:
            issues.append("隐私政策页面可能无法访问")
            recommendations.append("确保隐私政策链接有效")
        
        # 第三方服务评分 (权重: 20%)
        max_score += 20
        third_party = self.results.get('third_party_analysis', {})
        if not third_party.get('tracking_scripts'):
            score += 20
        else:
            score += 10
            issues.append("检测到可能的追踪脚本")
            recommendations.append("确保所有追踪脚本在获得用户同意后加载")
        
        # SSL加密评分 (权重: 10%)
        max_score += 10
        ssl_analysis = self.results.get('ssl_analysis', {})
        if ssl_analysis.get('uses_https'):
            score += 10
        else:
            issues.append("网站未使用HTTPS加密")
            recommendations.append("启用SSL证书，使用HTTPS协议")
        
        # 内容评分 (权重: 10%)
        max_score += 10
        content_analysis = self.results.get('content_analysis', {})
        if content_analysis.get('gdpr_keywords_found'):
            score += 5
        if content_analysis.get('user_rights_mentioned'):
            score += 5
        else:
            issues.append("未提及用户数据权利")
            recommendations.append("在隐私政策中明确说明用户的数据权利")
        
        # 联系信息评分 (权重: 10%)
        max_score += 10
        contact_analysis = self.results.get('contact_analysis', {})
        if contact_analysis.get('email_found') or contact_analysis.get('contact_form'):
            score += 10
        else:
            issues.append("缺少明确的联系方式")
            recommendations.append("提供数据保护相关的联系方式")
        
        compliance_percentage = (score / max_score) * 100 if max_score > 0 else 0
        
        self.results['compliance_score'] = {
            'percentage': round(compliance_percentage, 1),
            'score': score,
            'max_score': max_score,
            'issues': issues,
            'recommendations': recommendations,
            'level': self._get_compliance_level(compliance_percentage)
        }
    
    def _get_compliance_level(self, percentage):
        """获取合规等级"""
        if percentage >= 80:
            return "良好"
        elif percentage >= 60:
            return "一般"
        elif percentage >= 40:
            return "较差"
        else:
            return "严重不足"
    
    def generate_report(self):
        """生成检测报告"""
        if 'error' in self.results:
            print(f"❌ 检测失败: {self.results['error']}")
            return
        
        score_info = self.results['compliance_score']
        
        print("\n" + "="*60)
        print("📊 GDPR合规性检测报告")
        print("="*60)
        print(f"🌐 检测网站: {self.results['url']}")
        print(f"🏆 合规评分: {score_info['percentage']}% ({score_info['level']})")
        print(f"📊 得分: {score_info['score']}/{score_info['max_score']}")
        
        print("\n🔍 详细分析:")
        print(f"  🍪 Cookie同意横幅: {'✅ 已发现' if self.results['cookie_analysis']['has_consent_banner'] else '❌ 未发现'}")
        print(f"  📄 隐私政策: {'✅ 已找到' if self.results['privacy_analysis']['privacy_links_found'] else '❌ 未找到'}")
        print(f"  🔒 SSL加密: {'✅ 使用HTTPS' if self.results['ssl_analysis']['uses_https'] else '❌ 使用HTTP'}")
        print(f"  🔗 第三方服务: 发现 {len(self.results['third_party_analysis']['third_party_domains'])} 个第三方域名")
        print(f"  📞 联系信息: {'✅ 已提供' if (self.results['contact_analysis']['email_found'] or self.results['contact_analysis']['contact_form']) else '❌ 未提供'}")
        
        if score_info['issues']:
            print(f"\n⚠️  发现的问题:")
            for issue in score_info['issues']:
                print(f"   • {issue}")
        
        if score_info['recommendations']:
            print(f"\n💡 改进建议:")
            for recommendation in score_info['recommendations']:
                print(f"   • {recommendation}")
        
        print("\n" + "="*60)

def main():
    """主函数"""
    print("GDPR合规性自动检测工具")
    print("请输入要检测的网站URL:")
    
    url = input().strip()
    
    checker = GDPRComplianceChecker()
    results = checker.check_website(url)
    checker.generate_report()

if __name__ == "__main__":
    main()