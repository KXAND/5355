from pathlib import Path
from enum import Enum

PHASE_NO_ACTION = "no_action"
PHASE_REJECT = "reject"
PHASE_ACCEPT = "accept"


ABSOLUTE_PATH_ROOT = Path("D:\\DocumentsSet\\PolyU\\5355\\Project\\")
OUTPUT_DIR = Path(ABSOLUTE_PATH_ROOT, "output\\")
ANALYSIS_DIR = Path(ABSOLUTE_PATH_ROOT, "analysis\\")
INPUT_FILE = Path(ABSOLUTE_PATH_ROOT, "top100.csv")
INPUT_FILE_ABS = INPUT_FILE

ANALYSIS_RESULT_PATH = ANALYSIS_DIR.joinpath("analysis.json")
ANALYSIS_UNSURE_COOKIES_PATH = ANALYSIS_DIR.joinpath("cookie_query.database")
ANALYSIS_COOKIES_AGREE_PATH = ANALYSIS_DIR.joinpath("only_agrees_cookies.json")
ERR_LOG = ABSOLUTE_PATH_ROOT.joinpath("err.log")

OUTPUT_FILE_NOACTION_PATH = ABSOLUTE_PATH_ROOT.joinpath(
    f"cookie_diff_result_{PHASE_NO_ACTION}.json"
)
OUTPUT_FILE_REJECT_PATH = ANALYSIS_DIR.joinpath(
    f"cookie_diff_result_{PHASE_REJECT}.json"
)
OUTPUT_FILE_NO_AND_RE_PATH = ANALYSIS_DIR.joinpath("cookie_both_in_phases.json")
UNACCESSIBLE_FILE_PATH = ANALYSIS_DIR.joinpath("websites_unaccessible.json")
NOT_INTERACTIVE_FILE_PATH = ANALYSIS_DIR.joinpath("websites_not_interactive.json")
HALF_INTERACT_FILE_PATH = ANALYSIS_DIR.joinpath("haf_interactive.json")
SUPPLEMENTARY_FILE_PATH = ANALYSIS_DIR.joinpath("supplementary.json")
HUMAN_COLLECT_FILE_PATH = ABSOLUTE_PATH_ROOT.joinpath("input/human_collect.csv")

# using startwith parsing
tracking_cookie_prefixes = [
    # Google Analytics / Google Ads
    "_ga",  # GA4 / UA 用户标识
    "_gid",  # GA 短期用户 ID
    "_gat",  # GA 请求速率限制
    "_gat_gtag_",  # GA4 / gtag 版本
    "__utm",  # UA 老版 (如 __utma, __utmz …)
    "_gcl_",  # Google Ads / Analytics 关联 (gcl_aw, gcl_dc, gcl_au)
    "AMP_TOKEN",  # AMP + GA 客户端 ID
    "fpid",  # GA4 server-side first-party linker
    "fplc",  # GA4 first-party linker cookie
    # Adobe Analytics (Experience Cloud)
    "s_vi",  # Adobe visitor ID
    "s_ecid",  # ECID / Experience Cloud ID
    "AMCV_",  # Adobe Marketing Cloud ID
    "mbox",  # 用于 Adobe Target /个性化 / A/B 测试
    # Facebook / Meta Pixel
    "_fbp",  # Facebook 广告 /像素
    "fbc",  # Facebook 点击 ID
    # TikTok
    "_ttp",  # TikTok 广告 /用户标识
    "_tt_sessionId",  # TikTok 会话 ID
    "tt_appInfo",  # TikTok app 信息
    # LinkedIn
    "li_gc",  # LinkedIn 广告 /分析 cookie
    "lidc",  # LinkedIn 数据中心选择
    "bscookie",  # LinkedIn login / cross-domain
    # Twitter
    "personalization_id",  # Twitter 分析 /广告
    "guest_id",  # Twitter 匿名 /跟踪 ID
    # Hotjar (行为分析)
    "_hjSession_",  # Hotjar 会话
    "_hjFirstSeen",  # Hotjar 新用户标识
    "_hjid",  # Hotjar 用户 ID
    # Mixpanel (事件分析)
    "mp_",  # Mixpanel 标识
    # Matomo (开源分析平台)
    "_pk_id",  # Matomo 用户 ID
    "_pk_ses",  # Matomo 会话
    # Segment (多渠道分析)
    "ajs_anonymous_id",  # Segment 匿名 ID
    "ajs_user_id",  # Segment 用户 ID
    # Microsoft / Bing 广告 &分析
    "MUID",  # Microsoft 广告 /识别
    "_uetsid",  # Bing / Microsoft Ads 会话 ID
    "_uetvid",  # Microsoft Ads 再营销 ID
    # Yandex Metrica (俄罗斯分析)
    "_ym_",  # Yandex Metrica 用户会话 /ID
    # HubSpot (营销自动化)
    "__hstc",  # HubSpot 跟踪 cookie
    "hubspotutk",  # HubSpot 用户标识
    "__hssc",  # HubSpot 会话统计
    "__hssrc",  # HubSpot 来源
    # Snowplow (事件分析)
    "sp_",  # Snowplow tracking cookie
]


class websiteState(Enum):
    UNACCSSIBLE = (-1,)
    ACCSSIBLE = (0,)
    INTERACT_FAILED = (1,)
    INTERACT_HALF_FAILED = (4,)
    GDPR_COMPLIANT = (2,)
    GDPR_NON_COMPLIANT = (3,)


ANALYTICS_PATTERNS = [
    r"google-analytics\.com",
    r"gtag/js",
    r"analytics\.js",
    r"ga\(",
    r"googletagmanager\.com/gtm",
    r"matomo",
    r"mixpanel",
    r"segment\.js",
    r"hotjar\.com",
    r"heap-analytics",
    r"clarity/msft",
]

ADS_PATTERNS = [
    r"doubleclick\.net",
    r"googletagmanager\.com/gtm",
    r"gads",
    r"adsystem",
    r"adservice",
    r"bat\.bing\.com",
    r"connect\.facebook\.net",
    r"fbq\(",
    r"tiktok\.com",
    r"analytics/tiktok",
    r"snap\.licdn\.com",
]

ACCEPT_BUTTON_KEYWORDS = [
    # English
    "accept",
    "accept all",
    "accept all cookies",
    "allow",
    "allow all",
    "allow all cookies",
    "agree",
    "agree and continue",
    "agree and proceed",
    "i agree",
    "i accept",
    "yes, i agree",
    "consent",
    "give consent",
    "accept non-essential",
    "accept non-essential cookies",
    "accept optional cookies",
    "accept analytics",
    "accept marketing cookies",
    "enable all",
    "enable cookies",
    "continue with cookies",
    "ok",
    "okay",
    "got it",
    "that's fine",
    "continue",
    # French
    "accepter",
    "tout accepter",
    "accepter tout",
    "accepter les cookies",
    "accepter tous les cookies",
    "autoriser",
    "tout autoriser",
    "autoriser tous les cookies",
    "j'accepte",
    "oui, j'accepte",
    "consentir",
    "donner son consentement",
    "accepter les cookies non essentiels",
    "accepter les cookies optionnels",
    "continuer avec les cookies",
    "ok",
    "d'accord",
    "c'est bon",
    # Germany
    "akzeptieren",
    "alle akzeptieren",
    "alle cookies akzeptieren",
    "zustimmen",
    "ja, ich stimme zu",
    "ich stimme zu",
    "ich akzeptiere",
    "einverstanden",
    "ok",
    "okay",
    "verstanden",
    "fortfahren",
    "weiter",
    "cookies zulassen",
    "alle zulassen",
    "alle cookies zulassen",
    "zulassen",
    "zustimmen und fortfahren",
    "zustimmen und weiter",
    "zustimmen und fortsetzen",
    "cookie-nutzung zustimmen",
    "nicht notwendige cookies akzeptieren",
    "optionale cookies akzeptieren",
    "analyse-cookies akzeptieren",
    "marketing-cookies akzeptieren",
    "mit cookies fortfahren",
    "einwilligen",
    "einwilligung geben",
    # Chinese
    "接受",
    "全部接受",
    "接受全部",
    "接受所有",
    "同意",
    "同意所有",
    "允许",
    "允许所有",
    "接受cookie",
    "允许cookie",
    "全部允许",
    "确认并继续",
    "继续",
    "好",
    "好的",
]


REJECT_BUTTON_KEYWORDS = [
    # English
    "decline",
    "decline all",
    "reject",
    "reject all",
    "reject all cookies",
    "reject non-essential",
    "reject non-essential cookies",
    "refuse non-essential cookies",
    "required only",
    "disable",
    "disable all",
    "deny",
    "deny all",
    "opt out",
    "opt-out",
    "accept only essential cookies",
    "only necessary",
    "only essential cookies",
    "necessary only",
    "strictly necessary only",
    "use necessary cookies only",
    "essential cookies only",
    "I do not agree",
    "I do not accept",
    # French
    "refuser",
    "tout refuser",
    "refuser tout",
    "refuser les cookies",
    "refuser tous les cookies",
    "refuser non essentiels",
    "refuser tout sauf essentiels",
    "utiliser uniquement les cookies nécessaires",
    "cookies nécessaires uniquement",
    "désactiver",
    "désactiver tout",
    "désactiver les cookies",
    "désactiver tous les cookies",
    "enregistrer les parametres",
    "Enregistrer les paramètres"
    # Germany
    "ablehnen",
    "alles ablehnen",
    "alle ablehnen",
    "alle Cookies ablehnen",
    "nicht notwendige ablehnen",
    "nur notwendige Cookies",
    "nur notwendige Cookies verwenden",
    "nur erforderliche Cookies",
    "nur essentielle Cookies",
    "nur notwendige",
    "Strikt notwendige Cookies",
    "nur strikt notwendige Cookies",
    "Cookies deaktivieren",
    "alles deaktivieren",
    "alle Cookies deaktivieren",
    "ich stimme nicht zu",
    "ich akzeptiere nicht",
    "Opt-out",
    "opt out"
    # Chinese
    "拒绝",
    "全部拒绝",
    "拒绝全部",
    "拒绝所有",
    "拒绝非必要",
    "仅使用必要cookie",
    "仅必要",
    "只使用必要cookie",
    "禁用所有",
    "禁用cookie",
]
