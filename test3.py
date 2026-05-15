# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Step 1: Navigate to app")
    page.goto('http://localhost:8501', timeout=60000)
    page.wait_for_timeout(5000)

    print("Step 2: Click sidebar selectbox")
    select = page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first
    select.click()
    page.wait_for_timeout(2000)

    print("Step 3: Click 交易下單 option")
    # Find the popover and click 交易下單
    def click_trading(page):
        from playwright.sync_api import Page
        page2: Page = page  # type hint workaround
        script = """
        (() => {
            const popover = document.querySelector('[data-baseweb="popover"]');
            if (!popover) return 'NO_POPOVER';
            const items = popover.querySelectorAll('[role="option"]');
            for (let i = 0; i < items.length; i++) {
                if (items[i].textContent.trim() === '交易下單') {
                    items[i].click();
                    return 'CLICKED';
                }
            }
            const found = [];
            items.forEach(x => found.push(x.textContent.trim()));
            return 'NOT_FOUND: ' + found.join(', ');
        })()
        """
        return page2.evaluate("() => { " + script + " }")

    result = click_trading(page)
    print(f"   JavaScript result: {result}")

    page.wait_for_timeout(4000)
    page.screenshot(path='trading_fixed.png', full_page=True)
    print("   Screenshot: trading_fixed.png")

    print("Step 4: Check main content")
    main = page.locator('[data-testid="stMain"]')
    text = main.inner_text() if main.count() > 0 else ""

    print(f"   Main content length: {len(text)} chars")
    for ln in text.split('\n')[:25]:
        if ln.strip():
            print(f"     {ln[:120]}")

    print(f"Step 5: Check form elements")
    print(f"   Inputs: {page.locator('input').count()}")
    print(f"   Buttons: {page.locator('button').count()}")

    # Check if our trading panel elements exist
    st_el = page.locator('[data-testid]')
    print(f"   Streamlit data-testid count: {st_el.count()}")

    for_buttons = []
    for btn in page.locator('button').all():
        try:
            t = btn.inner_text().strip()
            if t:
                for_buttons.append(t)
        except:
            pass
    print(f"   Button texts: {for_buttons}")

    # Check for markdown content (st.markdown)
    md = page.locator('[data-testid="stMarkdown"]')
    print(f"   Markdown elements: {md.count()}")
    if md.count() > 0:
        first_md = md.first.inner_text() if md.count() > 0 else ""
        print(f"   First markdown: {first_md[:80]}")

    browser.close()
    print("Test complete!")