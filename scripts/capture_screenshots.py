"""Capture genuine Django application screenshots for Coursera using Playwright."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("DEMO_SITE_URL", "http://127.0.0.1:8000")
OUTPUT = Path("screenshots")
OUTPUT.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    page = context.new_page()

    page.goto(f"{BASE}/admin/login/", wait_until="domcontentloaded")
    page.locator("#id_username").fill("admin")
    page.locator("#id_password").fill(os.environ["DEMO_ADMIN_PASSWORD"])
    page.locator('input[type="submit"]').click()
    page.wait_for_url(f"{BASE}/admin/")
    assert "Authentication and Authorization" in page.locator("body").inner_text()
    assert "Online Course" in page.locator("body").inner_text()
    page.screenshot(path=str(OUTPUT / "03-admin-site.png"), full_page=True)

    context.clear_cookies()
    page.goto(f"{BASE}/onlinecourse/login/", wait_until="domcontentloaded")
    page.locator("#username").fill("demo")
    page.locator("#psw").fill(os.environ["DEMO_STUDENT_PASSWORD"])
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"{BASE}/onlinecourse/")
    page.get_by_role("link", name="View course").first.click()

    page.get_by_label("Django", exact=True).check()
    page.get_by_label("HyperText Markup Language", exact=True).check()
    page.get_by_label("Object-Relational Mapping", exact=True).check()
    page.get_by_role("button", name="Submit exam").click()
    page.get_by_text("Congratulations!", exact=False).wait_for()
    assert "100%" in page.locator("body").inner_text()
    assert "Exam results" in page.locator("body").inner_text()
    page.screenshot(path=str(OUTPUT / "07-final.png"), full_page=True)
    browser.close()
print("Captured screenshots/03-admin-site.png and screenshots/07-final.png")
