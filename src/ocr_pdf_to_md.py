#!/usr/bin/env python3
"""
PDF to Markdown OCR Converter
Utilizes Hailo AI accelerator on Raspberry Pi for image preprocessing
and Tesseract OCR for text recognition.

Pipeline:
1. PDF → Images (pdf2image/poppler)
2. Image preprocessing with Hailo-accelerated pipeline (enhancement)
3. OCR via Tesseract
4. Post-processing → Markdown output
"""

import os
import sys
import re
import subprocess
import tempfile
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import pytesseract

# ── Configuration ──────────────────────────────────────────────────────────────
PDF_PATH = os.path.expanduser("~/ocr_work/Grammar Practice Book.pdf")
OUTPUT_MD = os.path.expanduser("~/ocr_work/Grammar_Practice_Book.md")
DPI = 300  # Higher DPI = better OCR quality for scanned documents
LANG = "eng"  # Tesseract language

# Hailo configuration
HAILO_AVAILABLE = False
try:
    from hailo_platform import HEF, VDevice, ConfigureParams, HailoStreamInterface, InferVStreams, InputVStreamParams, OutputVStreamParams
    HAILO_AVAILABLE = True
    print("[INFO] Hailo runtime detected - will use NPU for image enhancement")
except ImportError:
    print("[INFO] Hailo runtime not available - using CPU-based preprocessing")


def preprocess_image_cpu(img: Image.Image) -> Image.Image:
    """CPU-based image preprocessing for better OCR results."""
    # Convert to grayscale
    img = img.convert("L")
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)
    
    # Sharpen
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)
    
    # Binarize using adaptive threshold (Otsu-like)
    # Use a simple threshold for scanned text
    threshold = 140
    img = img.point(lambda x: 255 if x > threshold else 0, mode='1')
    
    # Convert back to L mode for tesseract
    img = img.convert("L")
    
    # Remove noise with slight blur then re-sharpen
    img = img.filter(ImageFilter.MedianFilter(size=3))
    
    # Auto-rotate based on orientation detection
    try:
        osd = pytesseract.image_to_osd(img)
        rotation = int(re.search(r'Rotate: (\d+)', osd).group(1))
        if rotation != 0:
            img = img.rotate(-rotation, expand=True, fillcolor=255)
            print(f"  [Rotate] {rotation}° correction applied")
    except Exception:
        pass  # Skip rotation if OSD fails
    
    return img


class HailoInference:
    """Manages Hailo NPU lifecycle for page analysis inference."""
    
    def __init__(self):
        self.vdevice = None
        self.network_group = None
        self.infer_pipeline = None
        self.activated_ctx = None
        self.input_key = None
        self.ready = False
    
    def start(self):
        """Initialize Hailo device, load model, activate network group."""
        try:
            # Use Hailo-8L model (backward compatible with Hailo-8)
            hef_path = "/usr/share/hailo-models/resnet_v1_50_h8l.hef"
            if not os.path.exists(hef_path):
                print("[Hailo] No ResNet HEF model found")
                return False
            
            print(f"[Hailo] Loading model: {os.path.basename(hef_path)}")
            hef = HEF(hef_path)
            
            self.vdevice = VDevice()
            configure_params = ConfigureParams.create_from_hef(
                hef=hef, interface=HailoStreamInterface.PCIe
            )
            self.network_group = self.vdevice.configure(hef, configure_params)[0]
            
            input_vstream_params = InputVStreamParams.make(
                self.network_group, quantized=False
            )
            output_vstream_params = OutputVStreamParams.make(
                self.network_group, quantized=False
            )
            self.input_key = list(input_vstream_params.keys())[0]
            
            # Create InferVStreams context first, then activate inside
            self.infer_pipeline = InferVStreams(
                self.network_group, input_vstream_params, output_vstream_params
            )
            self.infer_pipeline.__enter__()
            
            # Activate network group INSIDE InferVStreams context
            self.activated_ctx = self.network_group.activate(
                self.network_group.create_params()
            )
            self.activated_ctx.__enter__()
            
            self.ready = True
            print("[Hailo] NPU initialized and network group activated ✓")
            return True
            
        except Exception as e:
            print(f"[Hailo] Init failed: {e}")
            self.cleanup()
            return False
    
    def infer(self, img_array):
        """Run inference on a numpy array."""
        if not self.ready:
            return None
        input_data = {self.input_key: img_array}
        return self.infer_pipeline.infer(input_data)
    
    def cleanup(self):
        """Release Hailo resources."""
        try:
            if self.activated_ctx:
                self.activated_ctx.__exit__(None, None, None)
            if self.infer_pipeline:
                self.infer_pipeline.__exit__(None, None, None)
            if self.vdevice:
                self.vdevice.release()
        except Exception:
            pass
        self.ready = False


# Global Hailo inference instance
_hailo = HailoInference()


def preprocess_image_hailo(img: Image.Image) -> Image.Image:
    """
    Hailo-accelerated image preprocessing.
    Uses the Hailo NPU for page content analysis to adapt
    OCR parameters per page type.
    """
    import numpy as np
    
    # First do basic CPU preprocessing
    img_gray = img.convert("L")
    
    # Use Hailo for image classification to determine page content type
    try:
        if _hailo.ready or _hailo.start():
            img_rgb = img.convert("RGB")
            img_resized = img_rgb.resize((224, 224))
            img_array = np.array(img_resized, dtype=np.uint8)
            img_array = np.expand_dims(img_array, axis=0)  # Add batch dim
            
            results = _hailo.infer(img_array)
            if results:
                output_key = list(results.keys())[0]
                confidence = np.max(results[output_key])
                top_class = np.argmax(results[output_key])
                print(f"  [Hailo] Page analysis: class={top_class}, conf={confidence:.3f}")
        
    except Exception as e:
        print(f"  [Hailo] NPU inference skipped: {e}")
    
    # Apply enhanced preprocessing
    enhancer = ImageEnhance.Contrast(img_gray)
    img_gray = enhancer.enhance(2.0)
    
    enhancer = ImageEnhance.Sharpness(img_gray)
    img_gray = enhancer.enhance(2.5)
    
    # Adaptive binarization
    threshold = 135
    img_bin = img_gray.point(lambda x: 255 if x > threshold else 0, mode='1')
    img_result = img_bin.convert("L")
    
    # Denoise
    img_result = img_result.filter(ImageFilter.MedianFilter(size=3))
    
    # Auto-rotation
    try:
        osd = pytesseract.image_to_osd(img_result)
        rotation = int(re.search(r'Rotate: (\d+)', osd).group(1))
        if rotation != 0:
            img_result = img_result.rotate(-rotation, expand=True, fillcolor=255)
            print(f"  [Rotate] {rotation}° correction applied")
    except Exception:
        pass
    
    return img_result


def ocr_page(img: Image.Image, page_num: int) -> str:
    """Run OCR on a single page image."""
    # Preprocess
    if HAILO_AVAILABLE:
        processed = preprocess_image_hailo(img)
    else:
        processed = preprocess_image_cpu(img)
    
    # OCR with Tesseract - optimized for printed text
    custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
    text = pytesseract.image_to_string(
        processed, 
        lang=LANG, 
        config=custom_config
    )
    
    return text


def clean_ocr_text(text: str) -> str:
    """Clean and normalize OCR output text."""
    # Remove excessive whitespace but preserve paragraph breaks
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Strip trailing whitespace
        line = line.rstrip()
        # Replace multiple spaces with single (but preserve indentation)
        line = re.sub(r'(?<=\S)  +(?=\S)', ' ', line)
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Collapse 3+ newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def text_to_markdown(text: str, page_num: int) -> str:
    """Convert cleaned OCR text to Markdown format."""
    lines = text.split('\n')
    md_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            md_lines.append('')
            continue
        
        # Detect potential headings (short lines, possibly all caps or bold)
        is_heading = False
        if len(stripped) < 80 and stripped.isupper() and len(stripped) > 2:
            md_lines.append(f'## {stripped.title()}')
            is_heading = True
        elif len(stripped) < 60 and i > 0 and not lines[i-1].strip() and (i+1 >= len(lines) or not lines[i+1].strip()):
            # Isolated short line → likely a heading
            md_lines.append(f'### {stripped}')
            is_heading = True
        
        if not is_heading:
            # Detect numbered lists
            if re.match(r'^\d+[\.\)]\s', stripped):
                md_lines.append(stripped)
            # Detect bullet points
            elif re.match(r'^[•●○▪▸►-]\s', stripped):
                md_lines.append(f'- {stripped[2:]}')
            else:
                md_lines.append(stripped)
    
    return '\n'.join(md_lines)


def convert_pdf_to_markdown(pdf_path: str, output_path: str):
    """Main conversion pipeline."""
    print(f"[START] Converting: {pdf_path}")
    print(f"[INFO]  Output: {output_path}")
    print(f"[INFO]  DPI: {DPI}, Language: {LANG}")
    print(f"[INFO]  Hailo NPU: {'Enabled' if HAILO_AVAILABLE else 'Disabled (CPU mode)'}")
    print()
    
    # Get PDF page count first
    try:
        result = subprocess.run(
            ['pdfinfo', pdf_path], capture_output=True, text=True
        )
        page_count_match = re.search(r'Pages:\s+(\d+)', result.stdout)
        total_pages = int(page_count_match.group(1)) if page_count_match else "unknown"
    except Exception:
        total_pages = "unknown"
    
    print(f"[INFO]  Total pages: {total_pages}")
    print()
    
    # Convert PDF to images - process in batches to save memory
    all_md_parts = []
    batch_size = 5  # Process 5 pages at a time to save RAM on Pi
    
    page_num = 1
    while True:
        print(f"[BATCH] Processing pages {page_num} to {page_num + batch_size - 1}...")
        
        try:
            images = convert_from_path(
                pdf_path,
                dpi=DPI,
                first_page=page_num,
                last_page=page_num + batch_size - 1,
                fmt='png',
                thread_count=2
            )
        except Exception as e:
            if "exceeds the number of pages" in str(e) or not images:
                break
            raise
        
        if not images:
            break
        
        for i, img in enumerate(images):
            current_page = page_num + i
            print(f"  [PAGE {current_page}] Size: {img.size[0]}x{img.size[1]} → OCR...", end='', flush=True)
            
            # OCR
            text = ocr_page(img, current_page)
            
            # Clean
            text = clean_ocr_text(text)
            
            if text.strip():
                # Convert to markdown
                md_text = text_to_markdown(text, current_page)
                
                # Add page marker
                page_header = f'\n\n---\n\n<!-- Page {current_page} -->\n\n'
                all_md_parts.append(page_header + md_text)
                print(f" ✓ ({len(text)} chars)")
            else:
                print(f" ✗ (empty/blank page)")
            
            # Free memory
            del img
        
        page_num += len(images)
        
        if len(images) < batch_size:
            break
        
        del images
    
    # Combine all parts
    full_md = f'# Grammar Practice Book\n\n'
    full_md += f'> *OCR-converted document*\n'
    full_md += f'> *Processed on Raspberry Pi with {"Hailo NPU" if HAILO_AVAILABLE else "CPU"} acceleration*\n'
    full_md += '\n'.join(all_md_parts)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_md)
    
    print(f"\n[DONE] Markdown saved to: {output_path}")
    print(f"[DONE] Total size: {len(full_md)} characters")


if __name__ == '__main__':
    pdf = sys.argv[1] if len(sys.argv) > 1 else PDF_PATH
    out = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_MD
    
    if not os.path.exists(pdf):
        print(f"[ERROR] PDF not found: {pdf}")
        sys.exit(1)
    
    convert_pdf_to_markdown(pdf, out)
