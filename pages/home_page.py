from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

class HomePage:
    def __init__(self, page: Page):
        self.page = page
        # Locators
        self.disclaimer_popup = "h5:has-text('Website Disclaimer')"
        self.close_button = "button.btn-close[data-bs-dismiss='modal']"
        self.book_menu = "a[href='./']:has-text('Book Appointment')" 
        self.book_appointment_link = "div.col-md-4 ul li a[href*='appointment.thespainvisa.com/Global/account/login']"

    def open(self, url: str):
        self.page.goto(url)

    def handle_disclaimer_popup(self):
        try:
            self.page.wait_for_selector(self.disclaimer_popup, timeout=3000)
            if self.page.is_visible(self.close_button):
                self.page.click(self.close_button)
                print("Disclaimer popup closed.")
        except TimeoutError:
            print("No disclaimer popup found, continuing...")

    def go_to_login_page(self, context):
        """Hover on Book Appointment menu, then click child link to open login in new tab"""
        box = self.page.locator(self.book_menu).bounding_box()
        self.page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
        self.page.wait_for_timeout(800)  # hold hover
        # Use expect_page to capture new tab
        with context.expect_page() as event:
            self.page.click(self.book_appointment_link, force=True)

        # self.page.hover(self.book_menu)
        # self.page.wait_for_selector(self.book_appointment_link, timeout=5000)

        # with context.expect_page() as new_page_event:
        #     self.page.click(self.book_appointment_link)

        new_page = event.value
        #added timeout of 500 second as login page takes lots of time to load even when load manually
        new_page.wait_for_load_state("networkidle", timeout=500000)
        print(f"Navigated to login page: {new_page.url}")
        return new_page
