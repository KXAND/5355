# save_as_audit.py
import asyncio
import json
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright
import aiofiles
import csv
from datetime import datetime, timezone
from asyncio import Semaphore

from consts import (
    ACCEPT_BUTTON_KEYWORDS,
    OUTPUT_DIR,
    INPUT_FILE,
    ERR_LOG,
    PHASE_REJECT,
    PHASE_ACCEPT,
    PHASE_NO_ACTION,
    REJECT_BUTTON_KEYWORDS,
)

from consts import (
    OUTPUT_DIR,
    INPUT_FILE,
    ERR_LOG,
    PHASE_REJECT,
    PHASE_ACCEPT,
    PHASE_NO_ACTION,
)

# --- 配置 ---
CONCURRENCY = 15
# Constants
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
LOCALE = "en-GB"
SECOND = 1000  # 1000ms
LOAD_PAGE_TIMEOUT = 45 * SECOND
LOAD_CONSENT_TIMEOUT = 20
CLICK_TIMEOUT = 3000
error_queue = asyncio.Queue()


def get_safe_name(url: str) -> str:
    if url.startswith("https://"):
        url = url[8:]
    return re.sub(r"[^0-9A-Za-z._-]", "_", url)


async def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(obj, ensure_ascii=False, indent=2))


async def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(text)


async def handle_errors(url, state, exception):
    print(f"[ERROR] at {url}: in {state} putted into queue")
    await error_queue.put(f"[ERROR] at {url}: triggered {exception} in {state}")


async def error_logger():
    error_cnt = 0
    while True:
        msg = await error_queue.get()
        try:
            print(f"[ERROR]: comsumed {error_cnt}")
            error_cnt += 1
            async with aiofiles.open(ERR_LOG, "a") as f:
                await f.write(msg + "\n\n")
        finally:
            error_queue.task_done()



# --- Main capture logic for one URL ---
async def capture_for_url(browser, url, semaphore: Semaphore, idx):
    print(f"🚦 任务 {idx} 开始，URL: {url}, 信号量值: {semaphore._value}")
    async with semaphore:
        print(f"    任务 {idx} 获得信号量 {semaphore._value}")
        # no_action Phase
        await capture_once_for_url(idx,url, browser, PHASE_NO_ACTION)
        print(f"    任务 {idx} Phase 1 结束")
        # reject_action phase
        await capture_once_for_url(idx,url, browser, PHASE_REJECT, click_cookie_banner)
        print(f"    任务 {idx} Phase 2 结束")
        # accept_action phase
        await capture_once_for_url(idx,url, browser, PHASE_ACCEPT, click_cookie_banner)
        print(f"    任务 {idx} Phase 3结束")
        print(f"{idx} : {url} Finished now.\n")


async def click_cookie_banner(page,is_accept):
    """尝试点击 cookie 同意或拒绝按钮"""
    clicked = False

    #  在主文档中查找
    clicked = await try_click_in_frame(page,is_accept)
    if clicked:
        return True

    #  检测所有 iframe（包括跨域）
    for frame in page.frames:
        # 跳过空的 about:blank 等
        if not frame.url or frame.url.startswith("about:"):
            continue
        try:
            clicked = await try_click_in_frame(frame,is_accept)
            if clicked:
                return True
        except Exception:
            continue

    #  尝试点击通用的 cookie/consent 容器
    try:
        containers = await page.query_selector_all(
            "[id*=cookie],[class*=cookie],[id*=consent],[class*=consent]"
        )
        for c in containers[:6]:
            btn = await c.query_selector("button, a, input[type='button']")
            if btn:
                try:
                    print(f"[info] URL: {page.url},phase:{is_accept}: try_click_in_containers")
                    await btn.click(timeout=3000)
                    return True
                except Exception:
                    pass
    except Exception:
        pass

    return False

async def try_click_in_frame(frame, is_accept):
    """在单个 frame 中尝试点击含关键字的按钮"""
    print(f"[info] URL: {frame.url},phase:{is_accept}: try_click_in_frame")
    if is_accept is True:
        keywords = ACCEPT_BUTTON_KEYWORDS
    else:
        keywords = REJECT_BUTTON_KEYWORDS
    for keyword in keywords:
        try:
            btns = await frame.query_selector_all(f'button:has-text("{keyword}")')
            if not btns:
                btns = await frame.query_selector_all(
                    f'a:has-text("{keyword}"), input[type="button"][value*="{keyword}"]'
                )
            for b in btns:
                try:
                    await b.click(timeout=CLICK_TIMEOUT)
                    print(f"[INFO] Clicked {keyword} in frame {frame.url}")
                    return True
                except Exception:
                    continue
        except Exception:
            continue
    print(f"[info] URL: {frame.url},phase:{is_accept}: click_in_frame false")
    return False


async def capture_once_for_url(idx,url, browser, phase, func=None):
    context = await browser.new_context(
        # har record may cause context.close() uncecessful
        # record_har_path=str(OUTPUT_DIR / get_safe_name(url) / phase / "har.har"),
        java_script_enabled=True,
        user_agent=UA,
        locale=LOCALE,
    )
    page = await context.new_page()
    outdir = OUTPUT_DIR / get_safe_name(url) / phase
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"[info] 任务 {idx}  URL: {url},phase:{phase}: page, context created")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=LOAD_PAGE_TIMEOUT)
        await asyncio.sleep(LOAD_CONSENT_TIMEOUT)  # wait for loading cookie consent
        print(f"[info] 任务 {idx}  URL: {url},phase:{phase}: page loaded")
    except Exception as e:
        print(f"[ERROR] 任务 {idx}  URL: {url},phase:{phase}: page has problem")
        await handle_errors(url=url, state="load page in " + phase, exception=e)
        await context.close()
        return

    interact_result = None
    if func is not None:
        if phase == PHASE_REJECT:
            interact_result = await func(page, False)
        elif phase == PHASE_ACCEPT:
            interact_result = await func(page, True)
    print(f"[info] 任务 {idx}  URL: {url},phase:{phase}: function interacted")
    try:
        # Save screenshot, DOM, cookies, HAR already recorded by context
        await page.screenshot(path=str(outdir / "screenshot.png"), full_page=True)
        print(f"[info] 任务 {idx}  URL: {url},phase:{phase}: screenshoted")
        
        dom = await page.content()
        await write_text(outdir / "dom.html", dom)
        print(f"[info] 任务 {idx}  URL: {url},phase:{phase}: domed")
        
        cookies = await context.cookies()
        await write_json(outdir / "cookies.json", cookies)
        print(f"[info] 任务 {idx}  URL: {url},phase:{phase}: cookie jsoned")
    except Exception as e:
        print(f"[ERROR] 任务 {idx}  URL: {url},phase:{phase}: get page data problem")
        await handle_errors(url=url, state="load page in " + phase, exception=e)
        await context.close()
        return

    meta_filepath = OUTPUT_DIR / get_safe_name(url) / "metadata.json"
    try:
        metadata = json.loads((meta_filepath).read_text(encoding="utf-8"))
    except Exception:
        print(f"[ERROR] 任务 {idx}  URL: {url},phase:{phase}: matadata problem")
        metadata = {"url": url}
    phase_metadata = {
        "captured_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    print(f"[info] 任务 {idx}  URL: {url},phase:{phase}: metadataed")
    if interact_result is not None:
        phase_metadata["interact_result"] = interact_result
    metadata[phase] = phase_metadata

    await write_json(meta_filepath, metadata)
    print(f"[info] 任务 {idx}  URL: {url},phase:{phase}: metadata wrote to json")
    # CLOSE before-phase context
    await page.route("**/*", lambda route: route.abort())
    await context.close()


# --- Orchestrator ---
async def main(urls):
    semaphore = Semaphore(CONCURRENCY)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)  # or False for debugging
        browser = await pw.chromium.launch(headless=True)  # or False for debugging
        tasks = [capture_for_url(browser, u, semaphore, idx) for idx, u in urls]
        logger_task = asyncio.create_task(error_logger())
        await asyncio.gather(*tasks, return_exceptions=True)
        await error_queue.join()
        await asyncio.sleep(0.1)  # 等最后flush
        await asyncio.sleep(0.1)  # 等最后flush
        logger_task.cancel()
        await browser.close()


if __name__ == "__main__":
    urls = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = csv.reader(f, delimiter=",")
        for idx, url in data:
            s = url.strip()
            if s:
                urls.append([idx, s] if s.startswith("http") else [idx, "https://" + s])
    asyncio.run(main(urls))
