from playwright.sync_api import sync_playwright

def launch_browser(headless: bool = False, slow_mo: int = 100):
    """
    Launches Chromium with configurable settings.
    """
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()
    return playwright, browser, context, page
