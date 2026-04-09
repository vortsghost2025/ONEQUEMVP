import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=True,
    )
    page = browser.new_page()

    try:
        print("Navigating to http://localhost:5173...")
        page.goto("http://localhost:5173", timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        page.wait_for_timeout(2000)

        # Get page title
        title = page.title()
        print(f"Page title: {title}")

        # Get all text content
        body_text = page.inner_text("body")
        print(f"\n=== PAGE CONTENT (first 1000 chars) ===")
        # Remove emojis for display
        clean_text = body_text.encode("ascii", "ignore").decode("ascii")
        print(clean_text[:1000])

        # Check for error messages
        errors = page.locator(".error").all_inner_texts()
        if errors:
            print(f"\n=== ERRORS FOUND ===")
            for err in errors:
                clean_err = err.encode("ascii", "ignore").decode("ascii")
                print(f"  - {clean_err}")

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        browser.close()
        print("\nBrowser closed.")
