import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=True,
    )
    page = browser.new_page()

    try:
        print("=== Testing OneQueue UI ===\n")

        # Navigate
        page.goto("http://localhost:5173", timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        page.wait_for_timeout(2000)

        # Check main page
        body = page.inner_text("body").encode("ascii", "ignore").decode("ascii")
        print(f"Main page shows:\n{body[:500]}\n")

        # Click NVIDIA tab
        print("=== Clicking NVIDIA tab ===")
        nvidia_button = page.locator('button:has-text("NVIDIA")')
        if nvidia_button.count() > 0:
            nvidia_button.click()
            page.wait_for_timeout(1000)

            # Get NVIDIA section content
            nvidia_content = (
                page.inner_text("body").encode("ascii", "ignore").decode("ascii")
            )
            print(f"NVIDIA tab shows:\n{nvidia_content[:800]}\n")
        else:
            print("NVIDIA button not found!")

        # Click Settings tab
        print("=== Clicking Settings tab ===")
        settings_button = page.locator('button:has-text("Settings")')
        if settings_button.count() > 0:
            settings_button.click()
            page.wait_for_timeout(1000)

            settings_content = (
                page.inner_text("body").encode("ascii", "ignore").decode("ascii")
            )
            print(f"Settings tab shows:\n{settings_content[:800]}\n")

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        browser.close()
