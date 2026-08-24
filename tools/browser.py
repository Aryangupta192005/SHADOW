"""
tools/browser.py
-----------------
Milestone 1 only implements `open_website`, using the stdlib `webbrowser`
module (opens the user's default browser — no dependency needed).

Milestone 4 will extend this module with Playwright-based automation
(browser_search, browser_click, browser_type, browser_get_text,
browser_download) behind the same tool-registry interface, so nothing
above this layer needs to change.
"""

from __future__ import annotations

import webbrowser

from assistant.logger import get_logger

log = get_logger("tools.browser")


def open_website(url: str) -> dict:
    if not url:
        return {"success": False, "message": "No URL provided."}
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        opened = webbrowser.open(url)
        if opened:
            log.info(f"Opened website: {url}")
            return {"success": True, "message": f"Opened {url} in your browser."}
        return {"success": False, "message": f"Could not open a browser for {url}."}
    except Exception as e:
        log.error(f"Failed to open {url}: {e}")
        return {"success": False, "message": f"Failed to open {url}: {e}"}
