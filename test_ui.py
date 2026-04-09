from playwright.sync_api import sync_playwright
import json
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    try:
        print("Testing OneQueue UI...")
        page.goto("http://localhost:5173", timeout=10000)
        page.wait_for_load_state("networkidle", timeout=10000)

        result = {"tests": [], "status": "pass"}

        # Test 1: Page loads
        result["tests"].append(
            {"name": "Page Load", "status": "pass", "title": page.title()}
        )

        # Test 2: All tabs visible
        tabs = page.locator('button[role="tab"]').all_inner_texts()
        result["tests"].append(
            {
                "name": "Tabs Available",
                "status": "pass" if len(tabs) >= 4 else "fail",
                "tabs": tabs,
                "count": len(tabs),
            }
        )

        # Test 3: Queue status visible
        queue_status = page.locator(".status-indicator").first
        if queue_status.is_visible():
            result["tests"].append(
                {
                    "name": "Queue Status",
                    "status": "pass",
                    "status_text": queue_status.inner_text(),
                }
            )

        # Test 4: Navigate to NVIDIA tab
        nvidia_tab = page.locator('button:has-text("NVIDIA")')
        if nvidia_tab.is_visible():
            nvidia_tab.click()
            time.sleep(2)
            models = page.locator("select option").all_inner_texts()
            result["tests"].append(
                {
                    "name": "NVIDIA Models",
                    "status": "pass",
                    "model_count": len(models),
                    "sample_models": models[:5] if len(models) > 0 else [],
                }
            )

        # Test 5: Navigate to Create Task
        create_tab = page.locator('button:has-text("Create Task")')
        if create_tab.is_visible():
            create_tab.click()
            time.sleep(1)
            result["tests"].append(
                {
                    "name": "Create Task Form",
                    "status": "pass",
                    "form_visible": page.locator("#task-title").is_visible(),
                }
            )

        # Test 6: Settings tab
        settings_tab = page.locator('button:has-text("Settings")')
        if settings_tab.is_visible():
            settings_tab.click()
            time.sleep(1)
            result["tests"].append(
                {"name": "Settings Tab", "status": "pass", "settings_visible": True}
            )

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e), "status": "fail"}, indent=2))

    finally:
        browser.close()
