import logging
import re
from twocaptcha import TwoCaptcha

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class CaptchaSolver:
    def __init__(self):
        self.api_key = "62adb248a238336da88e6a50389d2c69"
        self.solver = TwoCaptcha(self.api_key)

    def solve_coordinates(self, page, captcha_selector: str):
        captcha_element = page.query_selector(captcha_selector)
        if not captcha_element:
            raise Exception("❌ Captcha element not found")

        # Save screenshot
        captcha_image_path = "captcha.png"
        captcha_element.screenshot(path=captcha_image_path)
        logging.info(f"📸 Captcha screenshot saved: {captcha_image_path}")

        try:
            logging.info("➡️ Sending captcha to 2Captcha...")
            result = self.solver.coordinates(captcha_image_path)
            logging.info(f"⬅️ Raw response from 2Captcha: {result}")
        except Exception as e:
            logging.error(f"❌ Captcha solving failed: {e}")
            raise

        code_str = result.get("code")
        if not code_str or not code_str.startswith("coordinates:"):
            raise Exception(f"❌ Unexpected 2Captcha response: {code_str}")

        # Parse coordinates
        coords = []
        matches = re.findall(r"x=(\d+),y=(\d+)", code_str)
        for mx, my in matches:
            coords.append({"x": int(mx), "y": int(my)})

        if not coords:
            raise Exception(f"❌ Could not parse coordinates from: {code_str}")

        # Get captcha box
        box = captcha_element.bounding_box()
        if not box:
            raise Exception("❌ Could not get bounding box of captcha")

        logging.info(f"📦 Captcha bounding box: {box}")
        for coord in coords:
            x = box["x"] + coord["x"]
            y = box["y"] + coord["y"]
            logging.info(f"🖱️ Clicking at: ({x}, {y})")
            page.mouse.click(x, y)
