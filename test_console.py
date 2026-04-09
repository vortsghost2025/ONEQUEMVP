import asyncio
from playwright.async_api import async_playwright
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def test_with_console():
    """Test NVIDIA UI with console log capture"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True,
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        # Capture console messages
        console_messages = []
        page.on(
            "console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}")
        )

        print("=" * 60)
        print("Testing NVIDIA UI with Console Capture")
        print("=" * 60)

        print("\n1. Loading page...")
        await page.goto("http://[::1]:5173")
        await page.wait_for_load_state("networkidle")

        # Wait a bit for any errors
        await page.wait_for_timeout(2000)

        print("\n2. Console messages so far:")
        for msg in console_messages:
            print(f"   {msg}")

        print("\n3. Clicking NVIDIA tab...")
        nvidia_tab = page.locator('button:has-text("NVIDIA")')
        await nvidia_tab.click()
        await page.wait_for_timeout(5000)  # Wait for fetch

        print("\n4. Console messages after NVIDIA tab click:")
        for msg in console_messages[len(console_messages) :]:
            print(f"   {msg}")

        await page.screenshot(
            path="S:/TAKE10/screenshots/console_test.png", full_page=True
        )

        print("\n5. All console messages:")
        for msg in console_messages:
            print(f"   {msg}")

        print("\n" + "=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_with_console())
