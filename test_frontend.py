from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Show browser so you can see
    page = browser.new_page()

    # Capture console logs
    console_messages = []
    page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

    # Capture network failures
    failed_requests = []
    page.on(
        "requestfailed",
        lambda req: failed_requests.append(f"FAILED: {req.url} - {req.failure}"),
    )

    print("=== Navigating to frontend ===")
    page.goto("http://localhost:5173", wait_until="networkidle")

    print("\n=== Taking screenshot ===")
    page.screenshot(path="frontend_screenshot.png", full_page=True)

    print("\n=== Checking queue status ===")
    queue_text = page.locator("div").filter(has_text="Queue:").first.text_content()
    print(f"Queue status: {queue_text}")

    print("\n=== Filling out task form ===")
    page.fill('input[type="text"]', "Test Task from Playwright")
    page.fill("textarea", "Write a haiku about coding")
    page.fill('input[type="text"]', "orca-mini:latest")

    print("\n=== Clicking Create button ===")
    page.click('button[type="submit"]')

    print("\n=== Waiting 3 seconds for response ===")
    time.sleep(3)

    print("\n=== Checking for errors in console ===")
    if console_messages:
        print("Console messages:")
        for msg in console_messages:
            print(f"  {msg}")
    else:
        print("No console messages")

    if failed_requests:
        print("\nFailed requests:")
        for req in failed_requests:
            print(f"  {req}")
    else:
        print("\nNo failed requests")

    print("\n=== Checking tasks list ===")
    page.screenshot(path="frontend_after_submit.png", full_page=True)

    # Get all task rows
    tasks = page.locator("table tbody tr").all()
    print(f"Found {len(tasks)} task(s)")

    for i, task in enumerate(tasks):
        cells = task.locator("td").all()
        if len(cells) >= 4:
            title = cells[0].text_content()
            status = cells[1].text_content()
            attempts = cells[2].text_content()
            print(f"  Task {i + 1}: {title} - {status} (attempts: {attempts})")

    print("\n=== Keeping browser open for 10 seconds so you can see ===")
    time.sleep(10)

    browser.close()

    print("\n=== Test complete ===")
    print(f"Screenshots saved to:")
    print(f"  - frontend_screenshot.png")
    print(f"  - frontend_after_submit.png")
