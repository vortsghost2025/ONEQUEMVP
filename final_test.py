import asyncio
from playwright.async_api import async_playwright
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def final_test():
    """Final end-to-end test"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True,
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        print("=" * 60)
        print("FINAL END-TO-END TEST")
        print("=" * 60)

        # Load page
        print("\n1. Loading OneQueue...")
        await page.goto("http://[::1]:5173")
        await page.wait_for_load_state("networkidle")

        # Check all tabs load
        print("\n2. Testing all tabs...")
        tabs = ["Tasks", "Create Task", "NVIDIA", "Settings"]
        for tab in tabs:
            btn = page.locator(f'button:has-text("{tab}")')
            await btn.click()
            await page.wait_for_timeout(500)
            print(f"   - {tab}: OK")

        # Test NVIDIA
        print("\n3. Testing NVIDIA generation...")
        nvidia_btn = page.locator('button:has-text("NVIDIA")')
        await nvidia_btn.click()
        await page.wait_for_timeout(2000)

        # Fill and generate
        textarea = page.locator("textarea").first
        await textarea.fill("What is 2+2?")
        gen_btn = page.locator('button:has-text("Generate")')
        await gen_btn.click()
        await page.wait_for_selector("pre, .response-area", timeout=60000)

        response = page.locator("pre, .response-area").first
        text = await response.text_content()
        print(f"   Response: {text[:100]}...")

        # Screenshot
        await page.screenshot(
            path="S:/TAKE10/screenshots/final_success.png", full_page=True
        )

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(final_test())
