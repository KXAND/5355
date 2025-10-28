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

# --- 配置 ---
CONCURRENCY = 10
OUTPUT_DIR = Path("output")
INPUT_FILE = "./top100.csv"
ERR_LOG = "./err.log"
LANG_BUTTON_KEYWORDS = [
    # English examples and a few common translations (可扩展)
    "accept",
    "accept all",
    "agree",
    "allow all",
    "allow",
    "consent",
    # "decline", "reject", "reject all", "manage preferences", "save preferences",
    # "拒绝",  "全部拒绝",
    "允许",
    "接受",
    "同意",
    "全部接受",
    "accepter",
    "tout accepter",
]
# 可按需要扩充语言词表

# Constants
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
LOCALE = "en-GB"
SECOND = 1000  # 1000ms
LOAD_PAGE_TIMEOUT = 45 * SECOND
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
    print(f"[ERROR] at {url}: triggered {exception} in {state}")
    #await error_queue.put(f"[ERROR] at {url}: triggered {exception} in {state}") 
        
async def error_logger():
    while True:
        msg = await error_queue.get()
        async with aiofiles.open(ERR_LOG, "a") as f:
            await f.write(msg)
            error_queue.task_done()

# --- Main capture logic for one URL ---
async def capture_for_url(browser, url, semaphore: Semaphore, idx):
    async with semaphore:
        # Before Phase
        await capture_once_for_url(url, browser, "before")
       
        # AFTER phase
        await capture_once_for_url(url, browser, "after", click_cookie_banner)
        print(f"{idx} : {url} is Finished now.\n")


async def click_cookie_banner(page):
    """尝试点击 cookie 同意或拒绝按钮"""
    clicked = False
    for keyword in LANG_BUTTON_KEYWORDS:
        try:
            btns = await page.query_selector_all(f'button:has-text("{keyword}")')
            if not btns:
                btns = await page.query_selector_all(
                    f'a:has-text("{keyword}"), input[type="button"][value*="{keyword}"]'
                )
            for b in btns:
                try:
                    await b.click(timeout=5000)
                    clicked = True
                    break
                except Exception:
                    continue
            if clicked:
                break
        except Exception:
            continue

    if not clicked:
        try:
            candidates = await page.query_selector_all(
                "[id*=cookie],[class*=cookie],[id*=consent],[class*=consent]"
            )
            for c in candidates[:6]:
                try:
                    await c.click(timeout=3000)
                    clicked = True
                    break
                except Exception:
                    pass
        except Exception:
            pass

    await page.wait_for_timeout(3000)
    return clicked


async def capture_once_for_url(url, browser, phase, func=None):
    context = await browser.new_context(
        record_har_path=str(OUTPUT_DIR / get_safe_name(url) / phase / "har.har"),
        java_script_enabled=True,
        user_agent=UA,
        locale=LOCALE,
    )
    page = await context.new_page()
    outdir = OUTPUT_DIR / get_safe_name(url) / phase
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=LOAD_PAGE_TIMEOUT)
        await asyncio.sleep(10)  # wait 10s for loading cookie consent
    except Exception as e:
        await handle_errors(url=url, state="load page in " + phase, exception=e)
        await context.close()
        return

    interact_result = None
    if func is not None:
        interact_result = await func(page)
    try:
        # Save screenshot, DOM, cookies, HAR already recorded by context
        await page.screenshot(path=str(outdir / "screenshot.png"), full_page=True)
        dom = await page.content()
        await write_text(outdir / "dom.html", dom)
        cookies = await context.cookies()
        await write_json(outdir / "cookies.json", cookies)
    except Exception as e:
        await handle_errors(url=url, state="load page in " + phase, exception=e)
        await context.close()
        return
    
    meta_filepath = OUTPUT_DIR / get_safe_name(url) / "metadata.json"
    try:
        metadata = json.loads((meta_filepath).read_text(encoding="utf-8"))
    except Exception:
        metadata = {"url": url}
    phase_metadata = {
        "captured_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    if interact_result is not None:
        phase_metadata["interact_result"] = interact_result
    metadata[phase] = phase_metadata

    await write_json(meta_filepath, metadata)

    # CLOSE before-phase context
    await context.close()


# --- Orchestrator ---
async def main(urls):
    semaphore = Semaphore(CONCURRENCY)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
        headless=True
        )  # or False for debugging
        tasks = [capture_for_url(browser, u, semaphore, idx) for idx, u in urls]
        logger_task = asyncio.create_task(error_logger())
        await asyncio.gather(*tasks, return_exceptions=True)
        await error_queue.join()
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
