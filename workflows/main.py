from configs.browser_config import launch_browser
from pages.home_page import HomePage
from pages.login_page import LoginPage

def run_main_workflow():
    playwright, browser, context, page = launch_browser(headless=False, slow_mo=150)

    try:
        # Step 1: Go to site
        home = HomePage(page)
        home.open("https://thespainvisa.com/")

        # Step 2: Handle disclaimer
        home.handle_disclaimer_popup()

        login_page_obj = home.go_to_login_page(context)

        # Step 4: Interact with login
        login = LoginPage(login_page_obj)
        if login.is_loaded():
            print("Login page detected.")
    finally:
        browser.close()
        playwright.stop()
