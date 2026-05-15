# -*- coding: utf-8 -*-
import base64

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto('http://localhost:8501', timeout=60000)
    page.wait_for_timeout(5000)

    # Switch to 交易下單
    select = page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first
    select.click()
    page.wait_for_timeout(1500)
    page.evaluate("""
    () => {
        const pop = document.querySelector('[data-baseweb="popover"]');
        if (!pop) return;
        const items = pop.querySelectorAll('[role="option"]');
        items.forEach(it => {
            if (it.textContent.trim() === '交易下單') it.click();
        });
    }
    """)
    page.wait_for_timeout(5000)

    # --- SAVE SCREENSHOT ---
    el = page.locator('[data-testid="stMain"]')
    el.screenshot(path='main_screenshot.png')
    print("Screenshot saved: main_screenshot.png")

    # --- Get ALL visible text ---
    all_visible = page.evaluate("""
    () => {
        const main = document.querySelector('[data-testid="stMain"]');
        if (!main) return 'NO MAIN';
        return {
            innerHTML: main.innerHTML.substring(0, 2000),
            textContent: main.textContent.substring(0, 1000),
            childCount: main.children.length
        };
    }
    """)
    print(f"Main childCount: {all_visible['childCount']}")
    print(f"Main HTML preview: {all_visible['innerHTML'][:500]}")

    # --- Check ALL stElementContainers ---
    container_info = page.evaluate("""
    () => {
        const containers = document.querySelectorAll('[data-testid="stElementContainer"]');
        const info = [];
        containers.forEach((c, i) => {
            const visible = c.offsetParent !== null;
            const hasText = c.textContent.trim().length > 0;
            info.push({
                idx: i,
                visible: visible,
                hasText: hasText,
                text: c.textContent.trim().substring(0, 50)
            });
        });
        return info;
    }
    """)
    print(f"\nElement containers:")
    for item in container_info[:15]:
        if item['hasText']:
            print(f"  [{item['idx']}] visible={item['visible']} text='{item['text']}'")

    # --- Check blocks ---
    blocks = page.evaluate("""
    () => {
        const blocks = document.querySelectorAll('[data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"]');
        const info = [];
        blocks.forEach((b, i) => {
            const visible = b.style.display !== 'none';
            info.push({idx: i, visible: visible, display: b.style.display});
        });
        return info;
    }
    """)
    print(f"\nVertical/Horizontal blocks:")
    for b in blocks:
        if b['visible'] or len([x for x in blocks if x['visible']]) == 0:
            print(f"  [{b['idx']}] visible={b['visible']}")

    # --- Check if stMainBlockContainer exists ---
    mainblock = page.locator('[data-testid="stMainBlockContainer"]')
    print(f"\nstMainBlockContainer count: {mainblock.count()}")
    if mainblock.count() > 0:
        style = mainblock.first.evaluate("el => el.style.cssText + ' display=' + window.getComputedStyle(el).display")
        print(f"stMainBlockContainer style: {style}")

    # --- Try to count ALL divs with text ---
    all_divs = page.evaluate("""
    () => {
        const main = document.querySelector('[data-testid="stMain"]');
        let count = 0;
        let textDivs = [];
        function walk(node) {
            if (node.nodeType === 3) {
                const t = node.textContent.trim();
                if (t && node.parentElement && node.parentElement.children.length === 1) {
                    textDivs.push(t.substring(0, 30));
                }
                count++;
            }
            for (const child of node.childNodes) {
                walk(child);
            }
        }
        if (main) walk(main);
        return {totalNodes: count, textNodes: textDivs.slice(0, 30)};
    }
    """)
    print(f"\nTotal nodes in main: {all_divs['totalNodes']}")
    print(f"Text nodes: {all_divs['textNodes'][:15]}")

    browser.close()
    print("Done")