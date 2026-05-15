# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("=== Testing Trading Page ===")
    page.goto('http://localhost:8501', timeout=60000)
    page.wait_for_timeout(5000)
    page.screenshot(path='t5a.png')

    # Focus the selectbox
    selectbox = page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first
    selectbox.click()
    page.wait_for_timeout(2000)
    page.screenshot(path='t5b_popover.png')

    # 檢查 popover 內容
    popover_text = page.evaluate("""
    () => {
        const popover = document.querySelector('[data-baseweb="popover"]');
        if (!popover) return null;
        const items = popover.querySelectorAll('[role="option"]');
        const texts = [];
        items.forEach(i => texts.push(i.textContent.trim()));
        // 找 "交易下單" 的 index
        const idx = texts.indexOf('交易下單');
        return {total: texts.length, idx: idx, texts: texts};
    }
    """)
    print(f"Popover info: {popover_text}")

    # 用 JS 直接點擊「交易下單」並通知 Streamlit
    page.evaluate("""
    () => {
        const popover = document.querySelector('[data-baseweb="popover"]');
        if (!popover) return;
        const items = popover.querySelectorAll('[role="option"]');
        for (const item of items) {
            if (item.textContent.trim() === '交易下單') {
                item.click();
                // 強制通知 Streamlit
                const event = new Event('change', {bubbles: true});
                item.dispatchEvent(event);
                return;
            }
        }
    }
    """)
    page.wait_for_timeout(5000)

    # 檢查 URL 是否改變（Streamlit 有時候用 hash）
    url = page.url
    print(f"URL: {url}")

    page.screenshot(path='t5c.png', full_page=True)

    # 取出完整 HTML 並檢查
    html = page.content()
    print(f"HTML length: {len(html)}")

    # 檢查 stMarkdown 是否有 "交易" 相關文字
    md_text = page.evaluate("""
    () => {
        const mds = document.querySelectorAll('[data-testid="stMarkdown"]');
        let all = '';
        mds.forEach(m => {
            const t = m.textContent.trim();
            if (t) all += t + ' | ';
        });
        return all;
    }
    """)
    print(f"Markdown content: {md_text[:400]}")

    # 找所有 div 的 text 內容
    all_text = page.evaluate("""
    () => {
        const main = document.querySelector('[data-testid="stMain"]');
        if (!main) return 'NO MAIN';
        return main.textContent.substring(0, 1000);
    }
    """)
    print(f"Main div text: {all_text[:400]}")

    # 嘗試檢查是否真的切換了
    session = page.evaluate("""
    () => {
        // Streamlit 內部狀態
        if (window.streamlit !== undefined) {
            return 'has streamlit';
        }
        return 'no streamlit';
    }
    """)
    print(f"Streamlit state: {session}")

    # Try direct page navigation
    page.goto('http://localhost:8501/?page_selector=%E4%BA%A4%E6%98%93%E4%B8%8B%E5%96%AE', timeout=30000)
    page.wait_for_timeout(5000)
    page.screenshot(path='t5d.png')

    main_after_nav = page.locator('[data-testid="stMain"]').inner_text()
    print(f"After URL nav main: {len(main_after_nav)} chars")

    browser.close()
    print("===")