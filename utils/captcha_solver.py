from twocaptcha import TwoCaptcha

class CaptchaSolver:
    def __init__(self):
        self.api_key = "a0aa07af3e6316a114d4f0e409291bf7"
        self.solver = TwoCaptcha(self.api_key)

    def solve_coordinates(self, page, captcha_selector: str):
        """
        Takes a screenshot of the captcha element, sends it to 2Captcha,
        retrieves coordinates, and clicks the right spots on the page.
        """
        captcha_element = page.query_selector(captcha_selector)
        if not captcha_element:
            raise Exception("Captcha element not found")

        # Save screenshot of captcha
        captcha_image_path = "captcha.png"
        captcha_element.screenshot(path=captcha_image_path)

        # Send to 2Captcha
        try:
            result = self.solver.coordinates(captcha_image_path)
            coords = result.get("coordinates", [])
        except Exception as e:
            raise Exception(f"Captcha solving failed: {e}")

        # Get element bounding box
        box = captcha_element.bounding_box()
        if not box:
            raise Exception("Could not get bounding box of captcha")

        # Click all coordinates returned
        for coord in coords:
            page.mouse.click(box["x"] + coord["x"], box["y"] + coord["y"])
