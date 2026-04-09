from playwright.sync_api import sync_playwright
import time
import os

os.makedirs("screenshots", exist_ok=True)


def log(msg):
    """Print without unicode issues on Windows"""
    print(msg.encode("ascii", "replace").decode("ascii"))


def test_all_tabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        log("Navigating to http://localhost:5174/")
        page.goto("http://localhost:5174/")
        page.wait_for_load_state("networkidle")

        # Take initial screenshot
        page.screenshot(path="screenshots/01_initial.png", full_page=True)
        log("[OK] Initial page loaded")

        # Check Health Dashboard
        health_section = page.locator(".health-dashboard")
        if health_section.is_visible():
            log("[OK] Health Dashboard visible")
        else:
            log("[FAIL] Health Dashboard NOT visible")

        # Check header elements
        title = page.locator(".app-title")
        if title.is_visible():
            log(f"[OK] Title: {title.text_content()}")

        subtitle = page.locator(".app-subtitle")
        if subtitle.is_visible():
            log(f"[OK] Subtitle: {subtitle.text_content()}")

        # Find all tabs
        tabs = page.locator(".tab").all()
        log(f"\nFound {len(tabs)} tabs:")

        for i, tab in enumerate(tabs):
            tab_name = tab.text_content()
            log(f"  {i + 1}. {tab_name}")

        # Test each tab
        tab_names = ["Tasks", "Settings", "NVIDIA"]

        for tab_name in tab_names:
            log(f"\n--- Testing {tab_name} tab ---")
            tab = page.locator(f'.tab:has-text("{tab_name}")')

            if tab.is_visible():
                tab.click()
                page.wait_for_timeout(1000)
                page.screenshot(
                    path=f"screenshots/tab_{tab_name.lower()}.png", full_page=True
                )
                log(f"[OK] {tab_name} tab clicked and screenshot taken")

                # Check for specific content in each tab
                if tab_name == "Tasks":
                    # Check for task form
                    form = page.locator("form")
                    if form.is_visible():
                        log("  [OK] Task form visible")

                    # Check for ModelSelector
                    model_selector = page.locator(".model-selector, select")
                    if model_selector.is_visible():
                        log("  [OK] Model selector visible")

                    # Check for tasks table
                    table = page.locator(".tasks-table")
                    if table.is_visible():
                        log("  [OK] Tasks table visible")
                        rows = page.locator(".tasks-table tbody tr").count()
                        log(f"  [OK] Found {rows} task rows")

                elif tab_name == "Settings":
                    # Check for settings form
                    settings_form = page.locator(".settings-form").first
                    if settings_form.is_visible():
                        log("  [OK] Settings form visible")

                elif tab_name == "NVIDIA":
                    # Check for NVIDIA test component
                    nvidia_section = page.locator(".nvidia-test, .panel").first
                    if nvidia_section.is_visible():
                        log("  [OK] NVIDIA section visible")
            else:
                log(f"[FAIL] {tab_name} tab NOT found")

        # Test ModelSelector dropdown
        log("\n--- Testing ModelSelector ---")
        page.locator('.tab:has-text("Tasks")').click()
        page.wait_for_timeout(500)

        model_dropdown = page.locator("select").first
        if model_dropdown.is_visible():
            model_dropdown.click()
            page.wait_for_timeout(500)
            page.screenshot(path="screenshots/model_dropdown_open.png")
            log("[OK] Model dropdown opened")

            # Get all options
            options = page.locator("select option").all()
            log(f"  Found {len(options)} model options")

            # Check for optgroups
            optgroups = page.locator("optgroup").all()
            log(f"  Found {len(optgroups)} model groups:")
            for group in optgroups:
                label = group.get_attribute("label")
                if label:
                    log(f"    - {label}")

        # Test creating a task with auto model
        log("\n--- Testing Task Creation ---")

        # Fill in task form
        title_input = page.locator("#task-title")
        if title_input.is_visible():
            title_input.fill("UI Test Task")
            log("[OK] Filled task title")

        prompt_input = page.locator("#task-prompt")
        if prompt_input.is_visible():
            prompt_input.fill("Write a haiku about testing")
            log("[OK] Filled task prompt")

        # Check if smart recommendation appears
        page.wait_for_timeout(2000)
        recommendation = page.locator(".recommendation-banner")
        if recommendation.is_visible():
            log("[OK] Smart recommendation visible")
            rec_text = recommendation.text_content()
            if rec_text:
                log(f"  Recommendation: {rec_text[:100]}...")
        else:
            log("  No recommendation visible (may need longer prompt)")

        # Take final screenshot
        page.screenshot(path="screenshots/final_state.png", full_page=True)

        browser.close()

        log("\n=== TEST COMPLETE ===")
        log("Screenshots saved to: screenshots/")


if __name__ == "__main__":
    test_all_tabs()
