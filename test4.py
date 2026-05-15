from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import Page

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Navigate to app")
    page.goto('http://localhost:8501', timeout=60000)
    page.wait_for_timeout(5000)

    print("Click sidebar selectbox")
    select = page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first
    select.click()
    page.wait_for_timeout(2000)

    print("Click 交易下單 in popover via keyboard")
    # 按下 T 鍵快速跳到 "交易下單"
    page.keyboard.press("T")
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    page.screenshot(path='t4.png', full_page=True)

    main = page.locator('[data-testid="stMain"]')
    text = main.inner_text() if main.count() > 0 else ""
    print(f"Main chars: {len(text)}")

    inputs = page.locator('input')
    print(f"Inputs: {inputs.count()}")
    for i, inp in enumerate(inputs.all()):
        try:
            print(f"  [{i}] ph='{inp.get_attribute('placeholder')}' type={inp.get_attribute('type')}")
        except: pass

    buttons = [b.inner_text().strip() for b in page.locator('button').all() if b.inner_text().strip()]
    print(f"Buttons: {buttons}")

    browser.close()
    print("Done")