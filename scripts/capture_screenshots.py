"""Capture Home + Research screenshots for the portfolio pack.

Requires a running Streamlit app (default http://localhost:8501) and Playwright.

  pip install playwright
  playwright install chromium
  streamlit run app.py
  python scripts/capture_screenshots.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install Playwright: pip install playwright && playwright install chromium")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(2500)
        # Collapse sidebar if open so the hero is fully visible
        toggle = page.get_by_role("button", name="keyboard_double_arrow_right")
        if toggle.count():
            try:
                toggle.first.click(timeout=2000)
                page.wait_for_timeout(500)
            except Exception:
                pass
        page.screenshot(path=str(OUT / "home.png"), full_page=True)
        print("wrote", OUT / "home.png")

        page.goto(f"{BASE}/Test_a_Rule", wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "research.png"), full_page=True)
        print("wrote", OUT / "research.png")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
