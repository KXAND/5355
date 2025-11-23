import csv
import json
import os
from pathlib import Path
from consts import (
    INPUT_FILE_ABS,
    PHASE_ACCEPT,
    PHASE_NO_ACTION,
    PHASE_REJECT,
    websiteState,
    OUTPUT_DIR,
)


def get_website_list():
    with open(INPUT_FILE_ABS, "r", encoding="utf-8") as f:
        data = csv.reader(f, delimiter=",")
        return [url for idx, url in data]
    return []


def _load_json(path):
    """读取 JSON 文件，如果不存在返回空列表"""
    if not os.path.exists(path):
        print(f"[警告] 文件不存在: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[错误] 解析 JSON 失败: {path} ({e})")
            return None


def _read_doms(website, phase):
    path = os.path.join(OUTPUT_DIR, website, phase, "dom.html")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        dom = f.read()
    return dom


def _read_metadata(website):
    metadata_path = os.path.join(OUTPUT_DIR, website, "metadata.json")
    metadata = _load_json(metadata_path)
    if metadata is not None:
        return metadata
    return None


def _read_website_cookies(website):
    folder_path = os.path.join(OUTPUT_DIR, website)
    if not os.path.isdir(folder_path):
        return websiteState.UNACCSSIBLE, None, None, None

    json_path_no = os.path.join(folder_path, PHASE_NO_ACTION, "cookies.json")
    json_path_re = os.path.join(folder_path, PHASE_REJECT, "cookies.json")
    json_path_ac = os.path.join(folder_path, PHASE_ACCEPT, "cookies.json")
    metadata_path = os.path.join(folder_path, "metadata.json")

    # check metadata
    metadata = _load_json(metadata_path)
    if metadata is None:
        return websiteState.UNACCSSIBLE, None, None, None
    elif (
        metadata.get(PHASE_NO_ACTION) is None
        or metadata.get(PHASE_REJECT) is None
        or metadata.get(PHASE_ACCEPT) is None
    ):
        return websiteState.UNACCSSIBLE, None, None, None
    elif (
        metadata.get(PHASE_REJECT).get("interact_result") == False
        or metadata.get(PHASE_ACCEPT).get("interact_result") == False
    ):
        return websiteState.INTERACT_FAILED, None, None, None

    data_no = _load_json(json_path_no)
    data_re = _load_json(json_path_re)
    data_ac = _load_json(json_path_ac)
    return websiteState.ACCSSIBLE, data_no, data_re, data_ac


def get_all_metadatas_as_dict() -> dict[str,dict]:
    result = {}
    for website in os.listdir(OUTPUT_DIR):
        metadata = _read_metadata(website)
        result[website] = metadata
    return result


def get_all_cookies_as_dict():
    result_noaction = {}
    result_reject = {}
    result_accept = {}
    websites_unacessible = []
    websites_not_interactive = []

    # 遍历所有子文件夹
    for website in os.listdir(OUTPUT_DIR):
        state, cookies_no, cookies_re, cookies_ac = _read_website_cookies(website)
        if state is websiteState.UNACCSSIBLE:
            websites_unacessible.append(website)
            continue
        elif state is websiteState.INTERACT_FAILED:
            websites_not_interactive.append(website)
            continue

        result_noaction[website] = cookies_no
        result_reject[website] = cookies_re
        result_accept[website] = cookies_ac

    return (
        result_noaction,
        result_reject,
        result_accept,
        websites_unacessible,
        websites_not_interactive,
    )


def _write_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
