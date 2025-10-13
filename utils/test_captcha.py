import os
import glob
import re
import time
import pytesseract
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from sklearn.cluster import KMeans
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing
from functools import partial

class FastCaptchaOCRTester:
    def __init__(self, tesseract_cmd: str = None, save_debug: bool = True, debug_dir: str = "ocr_test_debug", max_workers: int = None):
        """
        Initialize standalone OCR tester with parallelism support
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        self.save_debug = save_debug
        self.debug_dir = debug_dir
        self.max_workers = max_workers or min(8, multiprocessing.cpu_count())

        if save_debug and not os.path.exists(debug_dir):
            os.makedirs(debug_dir)

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Use only the most effective methods for speed
        self.fast_methods = ['clahe', 'adaptive1', 'color_seg', 'otsu_blur']

    def get_image_files(self, folder_path: str) -> list:
        """
        Get unique image files from folder (fixes duplicate issue)
        """
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        image_files = set()  # Use set to avoid duplicates
        
        # Get all files in directory
        for file in os.listdir(folder_path):
            file_lower = file.lower()
            if any(file_lower.endswith(ext) for ext in image_extensions):
                image_files.add(os.path.join(folder_path, file))
        
        return sorted(list(image_files))  # Convert to sorted list

    def fast_preprocess_image(self, image_path: str) -> list:
        """
        Apply only the most effective preprocessing techniques for speed
        """
        img = cv2.imread(image_path)
        if img is None:
            return []
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_images = []
        
        # Method 1: CLAHE (usually most effective)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        processed_images.append(("clahe", enhanced))
        
        # Method 2: Adaptive threshold (fast and effective)
        adaptive_thresh1 = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        processed_images.append(("adaptive1", adaptive_thresh1))
        
        # Method 3: Color segmentation for green backgrounds
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        text_mask = cv2.bitwise_not(green_mask)
        color_seg = cv2.bitwise_and(gray, gray, mask=text_mask)
        processed_images.append(("color_seg", color_seg))
        
        # Method 4: Otsu with blur (reliable)
        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(("otsu_blur", otsu))
        
        return processed_images

    def fast_enhance_with_pil(self, cv_image):
        """
        Faster PIL enhancements with reduced processing
        """
        pil_img = Image.fromarray(cv_image)
        
        # Reduce enhancement levels for speed
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(2.0)
        
        enhancer = ImageEnhance.Sharpness(pil_img)
        pil_img = enhancer.enhance(1.5)
        
        # Smaller scaling for speed (2x instead of 4x)
        width, height = pil_img.size
        pil_img = pil_img.resize((width * 2, height * 2), Image.LANCZOS)
        
        return pil_img

    def fast_ocr_configs(self, image):
        """
        Use only the most effective OCR configurations with early stopping
        """
        configs = [
            "--psm 10 -c tessedit_char_whitelist=0123456789",
            "--psm 8 -c tessedit_char_whitelist=0123456789",
            "--psm 7 -c tessedit_char_whitelist=0123456789",
        ]
        
        best_result = ""
        best_confidence = 0
        
        for config in configs:
            try:
                text = pytesseract.image_to_string(image, config=config).strip()
                clean_text = ''.join(filter(str.isdigit, text))
                
                if clean_text and len(clean_text) <= 4:
                    # Get confidence
                    data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                    valid_confidences = [int(conf) for conf in data['conf'] if int(conf) > 20]
                    
                    if valid_confidences:
                        avg_confidence = sum(valid_confidences) / len(valid_confidences)
                        
                        if avg_confidence > best_confidence:
                            best_result = clean_text
                            best_confidence = avg_confidence
                        
                        # Early stopping for high confidence
                        if avg_confidence > 85:
                            break
                            
            except Exception:
                continue
        
        return best_result, best_confidence

    def process_single_image(self, args):
        """
        Process a single image (for parallel processing)
        """
        image_path, image_index, target_number = args
        
        if not os.path.exists(image_path):
            return None
        
        try:
            processed_versions = self.fast_preprocess_image(image_path)
        except Exception as e:
            print(f"❌ Failed to preprocess {os.path.basename(image_path)}: {e}")
            return None
        
        best_result = ""
        best_confidence = 0
        best_method = ""
        all_results = []
        
        for method_name, processed_img in processed_versions:
            try:
                enhanced_img = self.fast_enhance_with_pil(processed_img)
                
                # Save debug image if needed
                if self.save_debug:
                    debug_path = os.path.join(self.debug_dir, f"test_{method_name}_{image_index}_{os.path.basename(image_path)}")
                    enhanced_img.save(debug_path)
                
                text, confidence = self.fast_ocr_configs(enhanced_img)
                
                if text and confidence > 20:
                    all_results.append((text, confidence, method_name))
                
                if confidence > best_confidence and text:
                    best_result = text
                    best_confidence = confidence
                    best_method = method_name
                
                # Early stopping for target match with high confidence
                if target_number and text and target_number in text and confidence > 75:
                    break
                    
            except Exception as e:
                continue
        
        # Simple voting for multiple results
        if len(all_results) > 1:
            text_votes = {}
            for text, conf, method in all_results:
                if text in text_votes:
                    text_votes[text]['count'] += 1
                    text_votes[text]['total_conf'] += conf
                else:
                    text_votes[text] = {'count': 1, 'total_conf': conf}
            
            # Find most voted result
            for text, vote_data in text_votes.items():
                if vote_data['count'] > 1:
                    avg_conf = vote_data['total_conf'] / vote_data['count']
                    boosted_conf = avg_conf * (1 + vote_data['count'] * 0.2)
                    
                    if boosted_conf > best_confidence:
                        best_result = text
                        best_confidence = boosted_conf
                        best_method = f"voting_{vote_data['count']}_methods"
        
        # Check if matches target
        matches_target = False
        if target_number and best_result:
            matches_target = target_number in best_result
        
        return {
            'image_path': image_path,
            'image_name': os.path.basename(image_path),
            'best_result': best_result,
            'best_confidence': best_confidence,
            'best_method': best_method,
            'all_results': all_results,
            'matches_target': matches_target
        }

    def test_ocr_on_folder(self, folder_path: str, target_number: str = None):
        """
        Test OCR on all images in a folder with parallel processing
        """
        # Get unique image files (fixes duplicate issue)
        image_files = self.get_image_files(folder_path)
        
        if not image_files:
            print(f"❌ No image files found in {folder_path}")
            return []
        
        print(f"🔍 Found {len(image_files)} unique images to test")
        print(f"🚀 Using {self.max_workers} parallel workers")
        print("=" * 80)
        
        # Prepare arguments for parallel processing
        args_list = [(image_path, i, target_number) for i, image_path in enumerate(image_files)]
        
        start_time = time.time()
        results = []
        
        # Use ThreadPoolExecutor for I/O bound OCR operations
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_args = {executor.submit(self.process_single_image, args): args for args in args_list}
            
            # Collect results as they complete
            for i, future in enumerate(future_to_args):
                try:
                    result = future.result(timeout=60)  # 60 second timeout per image
                    if result:
                        results.append(result)
                        
                        # Print progress
                        status = "✅ MATCH" if result['matches_target'] else "❌ NO MATCH"
                        print(f"📸 {i+1}/{len(image_files)} - {result['image_name']}: '{result['best_result']}' ({result['best_confidence']:.1f}) {status if target_number else ''}")
                    
                except Exception as e:
                    args = future_to_args[future]
                    print(f"❌ Error processing {os.path.basename(args[0])}: {e}")
        
        end_time = time.time()
        print(f"\n⏱️ Total processing time: {end_time - start_time:.2f} seconds")
        print(f"⚡ Average time per image: {(end_time - start_time) / len(image_files):.2f} seconds")
        
        # Summary
        self.print_summary(results, target_number)
        return results

    def print_summary(self, results, target_number=None):
        """
        Print summary of all test results
        """
        print("\n" + "=" * 80)
        print("📊 SUMMARY REPORT")
        print("=" * 80)
        
        total_images = len(results)
        successful_ocr = len([r for r in results if r['best_result']])
        
        print(f"Total images tested: {total_images}")
        print(f"Successful OCR: {successful_ocr} ({successful_ocr/total_images*100:.1f}%)")
        
        if target_number:
            matches = len([r for r in results if r['matches_target']])
            print(f"Target matches: {matches} ({matches/total_images*100:.1f}%)")
        
        if total_images > 0:
            print(f"Average confidence: {sum(r['best_confidence'] for r in results)/total_images:.1f}")
        
        # Method performance
        method_counts = {}
        for result in results:
            method = result['best_method']
            method_counts[method] = method_counts.get(method, 0) + 1
        
        print(f"\n🏆 Best performing methods:")
        for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {method}: {count} times ({count/total_images*100:.1f}%)")
        
        # Failed cases
        failed_cases = [r for r in results if not r['best_result']]
        if failed_cases:
            print(f"\n❌ Failed OCR cases:")
            for case in failed_cases:
                print(f"  {case['image_name']}")
        
        # Success cases with target
        if target_number:
            success_cases = [r for r in results if r['matches_target']]
            if success_cases:
                print(f"\n✅ Successful matches:")
                for case in success_cases:
                    print(f"  {case['image_name']}: '{case['best_result']}' via {case['best_method']}")

    def test_specific_images(self, image_paths: list, target_number: str = None):
        """
        Test OCR on specific image files with parallel processing
        """
        print(f"🔍 Testing {len(image_paths)} specific images")
        print(f"🚀 Using {self.max_workers} parallel workers")
        print("=" * 80)
        
        # Filter existing files
        existing_files = [path for path in image_paths if os.path.exists(path)]
        
        if not existing_files:
            print("❌ No valid image files found")
            return []
        
        # Prepare arguments
        args_list = [(image_path, i, target_number) for i, image_path in enumerate(existing_files)]
        
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_args = {executor.submit(self.process_single_image, args): args for args in args_list}
            
            for i, future in enumerate(future_to_args):
                try:
                    result = future.result(timeout=60)
                    if result:
                        results.append(result)
                        
                        status = "✅ MATCH" if result['matches_target'] else "❌ NO MATCH"
                        print(f"📸 {i+1}/{len(existing_files)} - {result['image_name']}: '{result['best_result']}' ({result['best_confidence']:.1f}) {status if target_number else ''}")
                
                except Exception as e:
                    args = future_to_args[future]
                    print(f"❌ Error processing {os.path.basename(args[0])}: {e}")
        
        end_time = time.time()
        print(f"\n⏱️ Total processing time: {end_time - start_time:.2f} seconds")
        
        self.print_summary(results, target_number)
        return results


# Usage example:
if __name__ == "__main__":
    # Create fast tester with parallel processing
    tester = FastCaptchaOCRTester(
        tesseract_cmd=r"C:\Users\amaad.ali\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        save_debug=True, 
        debug_dir="ocr_test_debug",
        max_workers=4  # Adjust based on your CPU cores
    )
    
    # Test all images in a folder
    folder_path = "captchas2"
    target_number = "539"
    
    results = tester.test_ocr_on_folder(folder_path, target_number)
    
    # Or test specific images
    # specific_images = ["image1.png", "image2.png", "image3.png"]
    # results = tester.test_specific_images(specific_images, target_number)
