from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.email_fields = "input[type='text']"
        self.verify_button = "button#btnVerify"

    def is_loaded(self):
        return self.page.is_visible(self.verify_button)

    def enter_email(self, email: str):
        # Find all email fields
        fields = self.page.query_selector_all(self.email_fields)

        for field in fields:
            # Only fill if the field is enabled (not disabled)
            if field.is_enabled():
                field.fill(email)
                print(f"Entered email into field with id={field.get_attribute('id')}")
                break
        else:
            raise Exception("No enabled email field found.")

    def submit(self):
        self.page.click(self.verify_button)
        print("Verify button clicked.")
