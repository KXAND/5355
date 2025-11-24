import os
import json
import re
from urllib import request, error
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from consts import (
    ANALYSIS_COOKIES_AGREE_PATH,
    ANALYSIS_UNSURE_COOKIES_PATH,
    HALF_INTERACT_FILE_PATH,
    NOT_INTERACTIVE_FILE_PATH,
    OUTPUT_FILE_REJECT_PATH,
    OUTPUT_FILE_NOACTION_PATH,
    OUTPUT_FILE_NO_AND_RE_PATH,
    PHASE_ACCEPT,
    PHASE_NO_ACTION,
    PHASE_REJECT,
    UNACCESSIBLE_FILE_PATH,
    tracking_cookie_prefixes,
)

import utils
from utils import _read_website_cookies, _write_csv, _write_json
from consts import websiteState, ADS_PATTERNS, ANALYTICS_PATTERNS, ANALYSIS_RESULT_PATH


def _diff_two_cookie_list(list1, list2):
    """
    比较两个列表中不同的字典元素。
    假设字典可哈希化（如转成tuple(sorted(d.items()))）
    """
    if list1 is None:
        list1 = []
    if list2 is None:
        list2 = []
    names1 = {d.get("name") for d in list1 if isinstance(d, dict) and "name" in d}
    names2 = {d.get("name") for d in list2 if isinstance(d, dict) and "name" in d}

    only_in_1_names = names1 - names2
    only_in_2_names = names2 - names1
    both_names = names1 - only_in_1_names - only_in_2_names

    only_in_1 = [d for d in list1 if d.get("name") in only_in_1_names]
    only_in_2 = [d for d in list2 if d.get("name") in only_in_2_names]
    both_in = [d for d in list2 if d.get("name") in both_names]
    return only_in_1, only_in_2, both_in


def diff_all_websites(root_dir):
    # 1: before
    # 2: consent
    # 3: refuse

    count_bf = 0
    count_af = 0
    count3 = 0
    result_only_before = {}
    result_only_after = {}
    result_in_both = {}

    result_only_before["websites.length"] = count_bf
    result_only_after["websites.length"] = count_af
    websites_unacessible = []
    # 遍历所有子文件夹
    for website in os.listdir(root_dir):
        state, data_bf, data_af, data_ac = _read_website_cookies(website)
        if state is websiteState.UNACCSSIBLE:
            websites_unacessible.append(website)
            continue

        diff1, diff2, both = _diff_two_cookie_list(data_bf, data_af)
        if len(diff1) > 0:
            count_bf += 1
            result_only_before[website] = diff1
            result_only_before["websites.length"] = count_bf
        if len(diff2) > 0:
            count_af += 1
            result_only_after[website] = diff2
            result_only_after["websites.length"] = count_af
        if len(both) > 0:
            count3 += 1
            result_in_both[website] = both
            result_in_both["websites.length"] = count3

    # 输出结果

    _write_json(result_only_before, OUTPUT_FILE_NOACTION_PATH)
    _write_json(result_only_after, OUTPUT_FILE_REJECT_PATH)
    _write_json(result_in_both, OUTPUT_FILE_NO_AND_RE_PATH)
    _write_json(websites_unacessible, UNACCESSIBLE_FILE_PATH)
    return result_only_before, result_only_after, result_in_both, websites_unacessible


def _check_is_thridparty(cookie: dict, top_level_url):
    # 1. 解析主域名
    site_domain = urlparse(top_level_url).hostname or ""
    site_domain = site_domain.lstrip(".")

    cookie_domain = (cookie.get("domain") or "").lstrip(".")

    # 2. check if is same domain
    if site_domain not in cookie_domain:
        return True
    return False


def classify_cookie(cookie: dict, top_level_url):
    # this is a session cookie
    expire = cookie.get("expires", -2)
    if expire <= 0:
        return False, "Session"

    # is_third_party = _check_is_thridparty(cookie, top_level_url)

    # check cookie name
    Name = cookie.get("name", "")
    name = Name.lower()
    for key in tracking_cookie_prefixes:
        if name.startswith(key.lower()):
            return True, f"Cookie hit at {key}"

    # if len(Name)>50:
    #     return False, "Long Name Not Found"
    return False, "Not Found"


def classify_dom(dom):
    soup = BeautifulSoup(dom, "html.parser")
    urls = []
    reasons = []
    found_analytics = False
    found_ads = False
    # scripts
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if src:
            urls.append(src)
        # inline script content
        # if tag.string:
        #     urls.append(tag.string)

    # images
    for tag in soup.find_all(["img", "iframe", "link"]):
        src = tag.get("src") or tag.get("href")
        if src:
            urls.append(src)

    urls = [u.lower() for u in urls]

    # 3. Pattern matching on collected items
    for url in urls:
        for pattern in ANALYTICS_PATTERNS:
            match = re.search(
                r".{0,50}" + re.escape(pattern) + r".{0,50}", url, re.IGNORECASE
            )
            if match:
                match = match.group(0).split("?", 1)[0]
                found_analytics = True
                reasons.append(f"Dom analysis hit at {pattern} in {url}")
                print(f"Dom ad hit at {pattern}")
                break

        for pattern in ADS_PATTERNS:
            match = re.search(
                r".{0,50}" + re.escape(pattern) + r".{0,50}", url, re.IGNORECASE
            )
            if match:
                match = match.group(0).split("?", 1)[0]
                found_ads = True
                reasons.append(f"Dom ad hit at {pattern} in {match}")
                print(f"Dom ad hit at {pattern}")
                break

    if found_ads or found_analytics:
        return True, reasons
    else:
        return False, ["Not detected."]


def analyze(
    result_noaction,
    result_reject,
    result_accept,
    websites_unaccessible=None,
    websites_not_interactive=None,
    half_interact=None,
):
    websites = utils.get_website_list()

    # analyze websites
    analyze_results = []
    only_agree_cookies = {}
    unsure_cookies = []
    for website in websites:
        reasons = []
        if websites_unaccessible is not None and website in websites_unaccessible:
            reasons.append("unaccessible")
            analyze_results.append((website, None, reasons))
            continue
        if websites_not_interactive is not None and website in websites_not_interactive:
            reasons.append("not interactive")
            analyze_results.append((website, None, reasons))
            continue
        if half_interact is not None and any(t[0] == website for t in half_interact):
            reasons.append("half_interact")
            analyze_results.append((website, None, reasons))
            continue

        # get cookies
        opt_noaction = result_noaction.get(website)
        opt_reject_cookies = result_reject.get(website)
        opt_agree = result_accept.get(website)
        if opt_noaction is None:
            reasons.append("no_action access unsuccessful")
            analyze_results.append((website, None, reasons))
            continue
        if opt_reject_cookies is None:
            reasons.append("reject_action access unsuccessful")
            analyze_results.append((website, None, reasons))
            continue
        if opt_agree is None:
            reasons.append("accept_action access unsuccessful")
            analyze_results.append((website, None, reasons))
            continue
        # -----------------
        # check NoAction State:如果没有操作就有AD，那么就是违规
        has_least_one_hit = False
        for cookie in opt_noaction:
            result, reason = classify_cookie(cookie, website)
            if result is True:
                reasons.append(reason)
                has_least_one_hit = True
            elif result == False and reason == "Not Found":
                record = (cookie.get("name"), website)
                if record not in unsure_cookies:
                    unsure_cookies.append(record)
        # 检查 dom
        # if has_least_one_hit == False:
        #     dom = utils._read_doms(website, PHASE_NO_ACTION)
        #     result, reason = classify_dom(dom)
        #     if result is True:
        #         reasons.append(reason)

        # -----------------
        # Reject State: 如果拒绝了依然加载，那么也是违规
        # check cookie
        has_least_one_hit = False
        for cookie in opt_reject_cookies:
            result, reason = classify_cookie(cookie, website)
            if result is True:
                reasons.append(reason)
                has_least_one_hit = True
            elif result == False and reason == "Not Found":
                record = (cookie.get("name"), website)
                if record not in unsure_cookies:
                    unsure_cookies.append(record)

        # check dom
        # if has_least_one_hit == False:
        #     dom = utils._read_doms(website, PHASE_REJECT)
        #     result, reason = classify_dom(dom)
        #     if result is True:
        #         reasons.append(reason)

        if len(reasons) != 0:
            analyze_results.append((website, True, reasons))
        else:
            analyze_results.append((website, False, reasons))

        # -------------
        # Agree Option: 没想好干什么，先记下多的cookie
        only_agree, _, _ = _diff_two_cookie_list(opt_agree, opt_noaction)
        if len(only_agree) != 0:
            only_agree_cookies[website] = only_agree

    _write_json(only_agree_cookies, ANALYSIS_COOKIES_AGREE_PATH)
    # _write_json(analyze_results, ANALYSIS_RESULT_PATH)
    _write_csv(analyze_results, ANALYSIS_RESULT_PATH)
    _write_csv(unsure_cookies, ANALYSIS_UNSURE_COOKIES_PATH)


def human_sup_analyze(result_noaction:dict, result_reject, result_accept):
    # analyze websites
    analyze_results = []
    only_agree_cookies = {}
    unsure_cookies = []
    for [website,_] in result_noaction.items():
        reasons = []
        
        # get cookies
        opt_noaction = result_noaction.get(website)
        opt_reject_cookies = result_reject.get(website)
        opt_agree = result_accept.get(website)
        if opt_noaction is None:
            reasons.append("no_action access unsuccessful")
            analyze_results.append((website, None, reasons))
            continue
        if opt_reject_cookies is None:
            reasons.append("reject_action access unsuccessful")
            analyze_results.append((website, None, reasons))
            continue
        if opt_agree is None:
            reasons.append("accept_action access unsuccessful")
            analyze_results.append((website, None, reasons))
            continue
        # -----------------
        # check NoAction State:如果没有操作就有AD，那么就是违规
        has_least_one_hit = False
        for cookie in opt_noaction:
            result, reason = classify_cookie(cookie, website)
            if result is True:
                reasons.append(reason)
                has_least_one_hit = True
            elif result == False and reason == "Not Found":
                record = (cookie.get("name"), website)
                if record not in unsure_cookies:
                    unsure_cookies.append(record)
        # 检查 dom
        # if has_least_one_hit == False:
        #     dom = utils._read_doms(website, PHASE_NO_ACTION)
        #     result, reason = classify_dom(dom)
        #     if result is True:
        #         reasons.append(reason)

        # -----------------
        # Reject State: 如果拒绝了依然加载，那么也是违规
        # check cookie
        has_least_one_hit = False
        for cookie in opt_reject_cookies:
            result, reason = classify_cookie(cookie, website)
            if result is True:
                reasons.append(reason)
                has_least_one_hit = True
            elif result == False and reason == "Not Found":
                record = (cookie.get("name"), website)
                if record not in unsure_cookies:
                    unsure_cookies.append(record)

        # check dom
        # if has_least_one_hit == False:
        #     dom = utils._read_doms(website, PHASE_REJECT)
        #     result, reason = classify_dom(dom)
        #     if result is True:
        #         reasons.append(reason)

        if len(reasons) != 0:
            analyze_results.append((website, True, reasons))
        else:
            analyze_results.append((website, False, reasons))

        # -------------
        # Agree Option: 没想好干什么，先记下多的cookie
        only_agree, _, _ = _diff_two_cookie_list(opt_agree, opt_noaction)
        if len(only_agree) != 0:
            only_agree_cookies[website] = only_agree

    _write_json(only_agree_cookies, ANALYSIS_COOKIES_AGREE_PATH)
    # _write_json(analyze_results, ANALYSIS_RESULT_PATH)
    _write_csv(analyze_results, ANALYSIS_RESULT_PATH)
    _write_csv(unsure_cookies, ANALYSIS_UNSURE_COOKIES_PATH)


def get_half_interacted_websites():
    result = []
    data = utils.get_all_metadatas_as_dict()
    for url, web in data.items():
        if web is not None:
            re = web.get(PHASE_REJECT)
            ac = web.get(PHASE_ACCEPT)
            if ac is not None and re is not None:
                res_re = re.get("interact_result")
                res_ac = ac.get("interact_result")
                if res_ac != res_re:
                    result.append((url, res_re, res_ac))
    return result


# get data
# (
#     result_noaction,
#     result_reject,
#     result_accept,
#     websites_unaccessible,
#     websites_not_interactive,
# ) = utils.get_all_cookies_as_dict()

result_noaction, result_reject, result_accept = (
    utils.get_cookies_as_dict_from_human_collect()
)


# half_interact = get_half_interacted_websites()
# _write_json(half_interact, HALF_INTERACT_FILE_PATH)
human_sup_analyze(result_noaction, result_reject, result_accept)
# analyze(result_noaction, result_reject, result_accept)


# _write_json(websites_unaccessible, UNACCESSIBLE_FILE_PATH)
# _write_json(websites_not_interactive, NOT_INTERACTIVE_FILE_PATH)
