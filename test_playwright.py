from playwright.sync_api import sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://html.duckduckgo.com/html/?q=test")
    results = page.query_selector_all(".result__title a.result__a")
    for r in results[:2]:
        print(r.inner_text(), r.get_attribute("href"))
    browser.close()
