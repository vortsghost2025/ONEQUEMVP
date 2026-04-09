import asyncio
from playwright.async_api import async_playwright
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def test_nvidia_ui():
    """Test NVIDIA generation through the UI"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True,
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        print("=" * 60)
        print("Testing NVIDIA UI")
        print("=" * 60)

        print("\n1. Navigating to frontend...")
        await page.goto("http://[::1]:5173")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path="S:/TAKE10/screenshots/ui_01_initial.png", full_page=True
        )
        print("   OK - Initial page loaded")

        print("\n2. Clicking NVIDIA tab...")
        nvidia_tab = page.locator('button:has-text("NVIDIA")')
        await nvidia_tab.click()
        await page.wait_for_timeout(3000)  # Wait for models to load
        await page.screenshot(
            path="S:/TAKE10/screenshots/ui_02_nvidia_tab.png", full_page=True
        )
        print("   OK - NVIDIA tab clicked")

        # Check if models loaded
        print("\n3. Checking models dropdown...")
        model_select = page.locator("select").first
        options = await model_select.locator("option").all_text_contents()
        print(f"   Found {len(options)} models")
        if len(options) > 0:
            print(f"   First model: {options[0]}")
        else:
            print("   WARNING: No models in dropdown!")

        # Fill in prompt
        print("\n4. Filling prompt...")
        prompt_textarea = page.locator("textarea").first
        await prompt_textarea.fill("Write a haiku about coding.")
        print("   OK - Prompt: 'Write a haiku about coding.'")

        # Click Generate
        print("\n5. Clicking Generate button...")
        generate_btn = page.locator('button:has-text("Generate")')
        await generate_btn.click()
        print("   Waiting for response (60s timeout)...")

        # Wait for response or error
        try:
            await page.wait_for_selector(".response-area, pre, .output", timeout=60000)
            print("   OK - Response received!")
            await page.screenshot(
                path="S:/TAKE10/screenshots/ui_03_success.png", full_page=True
            )

            # Get response text
            response_el = page.locator(".response-area, pre, .output").first
            text = await response_el.text_content()
            print(f"\n   Generated response:\n   {text[:300]}...")

        except Exception as e:
            print(f"   Timeout: {e}")
            await page.screenshot(
                path="S:/TAKE10/screenshots/ui_03_timeout.png", full_page=True
            )

            # Check for error
            error_el = page.locator('.error, [class*="error"]')
            if await error_el.is_visible():
                error_text = await error_el.text_content()
                print(f"   Error: {error_text}")

        await page.screenshot(
            path="S:/TAKE10/screenshots/ui_04_final.png", full_page=True
        )
        print("\n" + "=" * 60)
        print("Test complete! Screenshots saved to S:/TAKE10/screenshots/")
        print("=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_nvidia_ui())
