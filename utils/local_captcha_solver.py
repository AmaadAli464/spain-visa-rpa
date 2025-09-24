# utils/local_captcha_solver.py
import re
import os
import pytesseract
from PIL import Image
from playwright.sync_api import Page


class LocalCaptchaSolver:
    def __init__(self, tesseract_cmd: str = None):
        """
        Initialize solver. Optionally configure Tesseract binary path.
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def get_visible_captcha_number(self, page: Page) -> str:
        """
        Finds the captcha instruction text currently visible in #captcha-main-div,
        extracts and returns the target number (e.g., '754').
        """
        script = """
        () => {
            const candidates = document.querySelectorAll("#captcha-main-div div.box-label");

            for (const el of candidates) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;

                const elemAtPoint = document.elementFromPoint(
                    rect.left + rect.width / 2,
                    rect.top + rect.height / 2
                );

                if (elemAtPoint === el || el.contains(elemAtPoint)) {
                    return el.textContent.trim();
                }
            }
            return null;
        }
        """

        text = page.evaluate(script)

        if text:
            # Example: "Please select all boxes with number 754"
            match = re.search(r"\d+", text)
            if match:
                number = match.group(0)
                print(f"✅ Captcha number detected: {number}")
                return number
            else:
                raise ValueError(f"Captcha text found but no number detected: '{text}'")
        else:
            raise ValueError("No visible captcha element found in DOM")

    def get_visible_boxes(self, page: Page):
        """
        Returns Playwright locators for only the visible grid boxes (#captcha-main-div div.col-4).
        """
        script = """
        () => {
            const candidates = document.querySelectorAll("#captcha-main-div div.col-4");
            const visible = [];
            for (const el of candidates) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;

                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;
                const elemAtPoint = document.elementFromPoint(cx, cy);

                if (elemAtPoint === el || el.contains(elemAtPoint)) {
                    visible.push(el.getAttribute("id"));
                }
            }
            return visible;
        }
        """
        box_ids = page.evaluate(script)
        return [page.locator(f"#{bid}") for bid in box_ids]

    def solve_grid_captcha(self, page: Page):
        """
        Full captcha solving flow:
        - Extract target number
        - OCR visible boxes
        - Click boxes that match
        """
        target = self.get_visible_captcha_number(page)
        visible_boxes = self.get_visible_boxes(page)

        print(f"🔍 Found {len(visible_boxes)} visible boxes.")
        matched_boxes = []

        for i, box in enumerate(visible_boxes):
            img = box.locator("img")
            path = f"box_{i}.png"
            img.screenshot(path=path)

            # OCR - restrict to digits only
            text = pytesseract.image_to_string(
                Image.open(path),
                config="--psm 6 -c tessedit_char_whitelist=0123456789"
            ).strip()

            print(f"🖼️ Box {i} OCR -> '{text}'")

            if target in text:
                matched_boxes.append(box)

            os.remove(path)

        # Click all matches
        for mb in matched_boxes:
            mb.click()

        print(f"✅ Clicked {len(matched_boxes)} boxes with number {target}.")
