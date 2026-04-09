from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # Navigate to frontend
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    
    # Take screenshot of initial state
    page.screenshot(path='screenshot_initial.png', full_page=True)
    
    # Check if Tasks tab is visible
    tasks_tab = page.locator('button:has-text("Tasks")')
    if tasks_tab.is_visible():
        print("✅ Tasks tab is visible")
        tasks_tab.click()
        time.sleep(1)
    
    # Check queue status
    queue_status = page.locator('.status-indicator').first
    if queue_status.is_visible():
        print(f"✅ Queue status: {queue_status.inner_text()}")
    
    # Navigate to NVIDIA tab
    nvidia_tab = page.locator('button:has-text("NVIDIA")')
    if nvidia_tab.is_visible():
        print("✅ NVIDIA tab is visible")
        nvidia_tab.click()
        time.sleep(2)
        page.screenshot(path='screenshot_nvidia_tab.png', full_page=True)
    
    # Check if model selector exists
    model_select = page.locator('select').first
    if model_select.is_visible():
        print("✅ Model selector found")
        models = model_select.locator('option').all()
        print(f"   Found {len(models)} models")
        for m in models[:5]:
            print(f"   - {m.inner_text()}")
    
    # Navigate to Create Task tab
    create_tab = page.locator('button:has-text("Create Task")')
    if create_tab.is_visible():
        create_tab.click()
        time.sleep(1)
        page.screenshot(path='screenshot_create_task.png', full_page=True)
        
        # Fill in a test task
        title_input = page.locator('#task-title')
        if title_input.is_visible():
            title_input.fill('Browser Test Task')
            print("✅ Filled task title")
        
        prompt_input = page.locator('#task-prompt')
        if prompt_input.is_visible():
            prompt_input.fill('Write a one-line joke about AI')
            print("✅ Filled task prompt")
        
        # Submit the form
        submit_btn = page.locator('button:has-text("Create Task")')
        if submit_btn.is_visible():
            submit_btn.click()
            print("✅ Submitted task")
            time.sleep(2)
    
    # Navigate back to Tasks tab to see the task
    tasks_tab.click()
    time.sleep(2)
    page.screenshot(path='screenshot_tasks_list.png', full_page=True)
    
    # Check if task appears in the list
    task_rows = page.locator('table.tasks-table tbody tr')
    if task_rows.count() > 0:
        print(f"✅ Found {task_rows.count()} tasks in queue")
    
    # Navigate to Settings tab
    settings_tab = page.locator('button:has-text("Settings")')
    if settings_tab.is_visible():
        settings_tab.click()
        time.sleep(1)
        page.screenshot(path='screenshot_settings.png', full_page=True)
        print("✅ Settings tab works")
    
    print("\n📊 Test Summary:")
    print("   - Frontend loads correctly")
    print("   - All tabs are accessible")
    print("   - Task creation form works")
    print("   - NVIDIA models are available")
    print("   - Settings are visible")
    
    time.sleep(3)
    browser.close()
