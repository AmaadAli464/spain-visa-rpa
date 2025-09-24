from playwright.sync_api import Page
# from utils.captcha_solver import CaptchaSolver
from utils.local_captcha_solver import LocalCaptchaSolver
import time


class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.email_field = "div.mb-3:has(label:has-text('Email')) input[type='text']:visible"
        self.verify_button = "button#btnVerify"
        self.captcha_selector = "#captcha-main-div:visible"
        self.password_field = "div:has(label:has-text('Password')) input[type='password']:visible"
        self.submit_button = "button[type='submit']:visible"

        # self.solver = CaptchaSolver()
        self.solver = LocalCaptchaSolver()

    def is_loaded(self):
        return self.page.is_visible(self.verify_button)

    def enter_email(self, email: str):
        self.page.locator(self.email_field).fill(email)

    def click_verify(self):
        self.page.click(self.verify_button)
        time.sleep(3)  # let page transition

    def solve_captcha(self):
        """
        Delegates captcha solving to CaptchaSolver (coordinates type).
        """
        self.page.wait_for_load_state("networkidle", timeout=60000)
        self.page.wait_for_selector(self.captcha_selector)

        self.solver.solve_grid_captcha(self.page)
        # self.solver.solve_coordinates(self.page, self.captcha_selector)
        print("Captcha solved successfully.")

    def enter_password(self, password: str):
        field = self.page.locator(self.password_field).first
        field.fill(password)

    def submit_form(self):
        self.page.click(self.submit_button)
        time.sleep(3)
        print("Form submitted.")
