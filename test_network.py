import asyncio
from playwright.async_api import async_playwright
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def test_network():
    """Test network requests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True,
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        # Track network requests
        requests = []
        page.on("request", lambda req: requests.append(f"-> {req.method} {req.url}"))
        page.on(
            "response", lambda resp: requests.append(f"<- {resp.status} {resp.url}")
        )

        console = []
        page.on("console", lambda msg: console.append(f"{msg.type}: {msg.text}"))

        print("=" * 60)
        print("Testing Network Requests")
        print("=" * 60)

        print("\n1. Loading page...")
        try:
            await page.goto("http://[::1]:5173", timeout=10000)
        except Exception as e:
            print(f"   Navigation error: {e}")

        await page.wait_for_timeout(3000)

        print("\n2. Clicking NVIDIA tab...")
        try:
            nvidia_tab = page.locator('button:has-text("NVIDIA")')
            if await nvidia_tab.is_visible(timeout=5000):
                await nvidia_tab.click()
                await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"   Click error: {e}")

        print("\n3. Network requests:")
        for req in requests:
            if "nvidia" in req.lower() or "api" in req.lower():
                print(f"   {req}")

        print("\n4. Console messages:")
        for msg in console:
            print(f"   {msg}")

        print("\n" + "=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_network())
