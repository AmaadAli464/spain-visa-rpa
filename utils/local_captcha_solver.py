import re 
import os 
import time 
import pytesseract 
import cv2 
import numpy as np 
from playwright.sync_api import Page 
from PIL import Image, ImageEnhance, ImageFilter 
from sklearn.cluster import KMeans import logging

class EnhancedCaptchaSolver: 
    def init(self, tesseract_cmd: str = None, save_debug: bool = True, debug_dir: str = "captchas"): 
        if tesseract_cmd: 
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        self.save_debug = save_debug
        self.debug_dir = debug_dir

        if save_debug and not os.path.exists(debug_dir):
            os.makedirs(debug_dir)

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

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

    def advanced_preprocess_image(self, image_path: str) -> list:
        """
        Apply multiple preprocessing techniques and return multiple versions
        """
        # Load image
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        processed_images = []
        
        # Method 1: Enhanced contrast with CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        processed_images.append(("clahe", enhanced))
        
        # Method 2: Color-based segmentation for green backgrounds
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Define range for green colors (adjust based on your captcha)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        
        # Create mask for green areas
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Invert mask to get non-green areas (likely text)
        text_mask = cv2.bitwise_not(green_mask)
        
        # Apply mask to original image
        color_seg = cv2.bitwise_and(gray, gray, mask=text_mask)
        processed_images.append(("color_seg", color_seg))
        
        # Method 3: Multiple adaptive thresholding approaches
        adaptive_thresh1 = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        processed_images.append(("adaptive1", adaptive_thresh1))
        
        adaptive_thresh2 = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 3
        )
        processed_images.append(("adaptive2", adaptive_thresh2))
        
        # Method 4: Otsu with different blur levels
        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(("otsu_blur", otsu))
        
        # Method 5: Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
        processed_images.append(("morph", morph))
        
        # Method 6: Edge-based enhancement
        edges = cv2.Canny(enhanced, 50, 150)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        processed_images.append(("edges", dilated_edges))
        
        # Method 7: K-means color quantization
        kmeans_img = self.apply_kmeans_segmentation(img)
        processed_images.append(("kmeans", kmeans_img))
        
        # Method 8: Bilateral filter + threshold
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        _, bilateral_thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(("bilateral", bilateral_thresh))
        
        # Method 9: Contrast stretching
        stretched = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        _, stretched_thresh = cv2.threshold(stretched, 127, 255, cv2.THRESH_BINARY)
        processed_images.append(("stretched", stretched_thresh))
        
        return processed_images

    def apply_kmeans_segmentation(self, img, k=3):
        """
        Use K-means clustering to separate foreground and background
        """
        data = img.reshape((-1, 3))
        data = np.float32(data)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert back to uint8 and reshape
        centers = np.uint8(centers)
        segmented_data = centers[labels.flatten()]
        segmented_image = segmented_data.reshape(img.shape)
        
        # Convert to grayscale and apply threshold
        gray_seg = cv2.cvtColor(segmented_image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray_seg, 127, 255, cv2.THRESH_BINARY)
        
        return binary

    def enhance_with_pil(self, cv_image):
        """
        Additional PIL-based enhancements
        """
        # Convert CV2 image to PIL
        pil_img = Image.fromarray(cv_image)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(2.5)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(pil_img)
        pil_img = enhancer.enhance(2.0)
        
        # Enhance brightness if image is too dark
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(1.2)
        
        # Apply unsharp mask for better edge definition
        pil_img = pil_img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        
        # Resize for better OCR (OCR works better on larger images)
        width, height = pil_img.size
        pil_img = pil_img.resize((width * 4, height * 4), Image.LANCZOS)
        
        return pil_img

    def ocr_with_multiple_configs(self, image):
        """
        Try multiple Tesseract configurations and return best result
        """
        configs = [
            "--psm 10 -c tessedit_char_whitelist=0123456789",
            "--psm 8 -c tessedit_char_whitelist=0123456789",
            "--psm 7 -c tessedit_char_whitelist=0123456789",
            "--psm 13 -c tessedit_char_whitelist=0123456789",
            "--psm 6 -c tessedit_char_whitelist=0123456789",
            "--psm 9 -c tessedit_char_whitelist=0123456789",
            "--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789",
            "--psm 8 --oem 1 -c tessedit_char_whitelist=0123456789",
        ]
        
        results = []
        confidences = []
        
        for config in configs:
            try:
                # Get text with confidence
                data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                
                # Filter out low confidence results
                valid_confidences = [int(conf) for conf in data['conf'] if int(conf) > 20]
                
                if valid_confidences:
                    avg_confidence = sum(valid_confidences) / len(valid_confidences)
                    text = pytesseract.image_to_string(image, config=config).strip()
                    
                    # Clean the text - remove any non-digit characters
                    clean_text = ''.join(filter(str.isdigit, text))
                    
                    if clean_text and len(clean_text) <= 4:  # Reasonable length for captcha numbers
                        results.append(clean_text)
                        confidences.append(avg_confidence)
                        
            except Exception as e:
                continue
        
        if results:
            # Return result with highest confidence
            best_idx = confidences.index(max(confidences))
            return results[best_idx], confidences[best_idx]
        
        return "", 0

    def solve_single_box(self, box, box_index: int, target: str):
        """
        Enhanced single box solving with multiple preprocessing attempts
        """
        img = box.locator("img")
        ts = int(time.time() * 1000)
        raw_path = os.path.join(self.debug_dir, f"raw_box_{box_index}_{ts}.png")
        
        # Take screenshot
        img.screenshot(path=raw_path)
        
        # Get all preprocessed versions
        processed_versions = self.advanced_preprocess_image(raw_path)
        
        best_result = ""
        best_confidence = 0
        best_method = ""
        all_results = []
        
        for method_name, processed_img in processed_versions:
            try:
                # Apply PIL enhancements
                enhanced_img = self.enhance_with_pil(processed_img)
                
                                # Save debug image
                    if self.save_debug:
                        debug_path = os.path.join(self.debug_dir, f"proc_{method_name}_box_{box_index}_{ts}.png")
                        enhanced_img.save(debug_path)
                    
                    # Try OCR with multiple configurations
                    text, confidence = self.ocr_with_multiple_configs(enhanced_img)
                    
                    print(f"Box {box_index} - Method {method_name}: '{text}' (confidence: {confidence:.1f})")
                    
                    # Store all results for voting
                    if text and confidence > 20:
                        all_results.append((text, confidence, method_name))
                    
                    # Update best result if this is better
                    if confidence > best_confidence and text:
                        best_result = text
                        best_confidence = confidence
                        best_method = method_name
                        
                except Exception as e:
                    print(f"Method {method_name} failed for box {box_index}: {e}")
                    continue
            
            # Voting mechanism - if multiple methods agree, increase confidence
            if len(all_results) > 1:
                text_votes = {}
                for text, conf, method in all_results:
                    if text in text_votes:
                        text_votes[text]['count'] += 1
                        text_votes[text]['total_conf'] += conf
                        text_votes[text]['methods'].append(method)
                    else:
                        text_votes[text] = {'count': 1, 'total_conf': conf, 'methods': [method]}
                
                # Find most voted result
                for text, vote_data in text_votes.items():
                    if vote_data['count'] > 1:  # Multiple methods agree
                        avg_conf = vote_data['total_conf'] / vote_data['count']
                        boosted_conf = avg_conf * (1 + vote_data['count'] * 0.2)  # Boost confidence
                        
                        if boosted_conf > best_confidence:
                            best_result = text
                            best_confidence = boosted_conf
                            best_method = f"voting_{vote_data['count']}_methods"
            
            # Final validation and decision
            if best_result and len(best_result) <= 4 and best_result.isdigit():
                print(f"✅ Box {box_index} BEST: '{best_result}' via {best_method} (conf: {best_confidence:.1f})")
                
                # Check if target number is contained in the result
                # Handle cases where OCR might detect extra digits
                contains_target = target in best_result
                
                # Additional check: if result is longer than target, check if target is a substring
                if not contains_target and len(best_result) > len(target):
                    contains_target = target in best_result
                
                # Another check: if they're the same length, exact match
                if not contains_target and len(best_result) == len(target):
                    contains_target = best_result == target
                
                return contains_target
            else:
                print(f"❌ Box {box_index} - No reliable OCR result found")
                return False

        def preprocess_image(self, image_path: str) -> Image.Image:
            """
            Legacy method - kept for backward compatibility but enhanced
            """
            # Use the first method from advanced preprocessing as fallback
            processed_versions = self.advanced_preprocess_image(image_path)
            if processed_versions:
                return self.enhance_with_pil(processed_versions[0][1])
            
            # Original fallback logic
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            pil_image = Image.fromarray(img)
            pil_image = pil_image.resize((pil_image.width * 2, pil_image.height * 2), Image.LANCZOS)
            img = np.array(pil_image)
            _, binary_img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            inverted_img = cv2.bitwise_not(binary_img)
            kernel = np.ones((2, 2), np.uint8)
            cleaned_img = cv2.erode(inverted_img, kernel, iterations=1)
            cleaned_img = cv2.dilate(cleaned_img, kernel, iterations=1)
            return Image.fromarray(cleaned_img)

        def solve_grid_captcha(self, page: Page):
            """
            Enhanced captcha solving with better error handling and validation
            """
            try:
                target = self.get_visible_captcha_number(page)
                visible_boxes = self.get_visible_boxes(page)
                
                print(f"🎯 Target number: {target}")
                print(f"🔍 Found {len(visible_boxes)} visible boxes")
                
                matched_boxes = []
                
                for i, box in enumerate(visible_boxes):
                    if self.solve_single_box(box, i, target):
                        matched_boxes.append(box)
                
                # Click all matches with small delays to avoid issues
                for i, mb in enumerate(matched_boxes):
                    mb.click()
                    if i < len(matched_boxes) - 1:  # Don't delay after last click
                        time.sleep(0.2)
                
                print(f"✅ Successfully clicked {len(matched_boxes)} boxes with number {target}")
                
                if len(matched_boxes) == 0:
                    print("⚠️ No matching boxes found - captcha might not be solved correctly")
                    return False
                
                return True
                
            except Exception as e:
                print(f"❌ Captcha solving failed: {e}")
                return False

