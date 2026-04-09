import asyncio
from playwright.async_api import async_playwright
import json
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def test_nvidia_generation():
    """Test NVIDIA generation through the UI"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True,
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        print("📋 Navigating to frontend...")
        await page.goto("http://[::1]:5173")
        await page.wait_for_load_state("networkidle")

        # Take initial screenshot
        await page.screenshot(
            path="S:/TAKE10/screenshots/01_initial.png", full_page=True
        )
        print("✅ Initial screenshot saved")

        # Click NVIDIA tab
        print("\n📌 Clicking NVIDIA tab...")
        nvidia_tab = page.locator('button:has-text("NVIDIA")')
        await nvidia_tab.click()
        await page.wait_for_timeout(1000)
        await page.screenshot(
            path="S:/TAKE10/screenshots/02_nvidia_tab.png", full_page=True
        )
        print("✅ NVIDIA tab screenshot saved")

        # Check for models dropdown
        print("\n📋 Checking model selection...")
        model_select = page.locator("select").first
        if await model_select.is_visible():
            # Get available models
            models = await model_select.locator("option").all_text_contents()
            print(f"Found {len(models)} models")

            # Select a model (use the first curated one)
            await model_select.select_option(index=0)
            await page.wait_for_timeout(500)
            print("✅ Selected first model")

        # Fill in prompt
        print("\n📝 Filling in prompt...")
        prompt_input = page.locator("textarea").first
        if await prompt_input.is_visible():
            await prompt_input.fill("Write a short poem about AI.")
            print("✅ Prompt filled: 'Write a short poem about AI.'")

        # Click Generate button
        print("\n🚀 Clicking Generate button...")
        generate_btn = page.locator('button:has-text("Generate")')
        if await generate_btn.is_visible():
            await generate_btn.click()
            print("⏳ Waiting for generation (30s timeout)...")

            # Wait for response or error
            try:
                await page.wait_for_selector("text=Response:", timeout=30000)
                print("✅ Generation completed!")
                await page.screenshot(
                    path="S:/TAKE10/screenshots/03_generation_success.png",
                    full_page=True,
                )

                # Get the response text
                response_area = page.locator(".response-area, .output-area, pre").first
                if await response_area.is_visible():
                    response_text = await response_area.text_content()
                    print(f"\n📝 Generated Response:\n{response_text[:500]}...")

            except Exception as e:
                print(f"⏱️ Timeout or error: {e}")
                await page.screenshot(
                    path="S:/TAKE10/screenshots/03_generation_timeout.png",
                    full_page=True,
                )

                # Check for error message
                error_msg = page.locator('.error, [class*="error"]')
                if await error_msg.is_visible():
                    error_text = await error_msg.text_content()
                    print(f"❌ Error message: {error_text}")

        # Final screenshot
        await page.screenshot(path="S:/TAKE10/screenshots/04_final.png", full_page=True)
        print("\n✅ Final screenshot saved")

        await browser.close()
        print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_nvidia_generation())
