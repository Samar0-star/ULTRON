# Location: backend/tools/pdf_reader.py
"""
GodLevelPDFProcessor  defensive, hardened
(Extracted into its own module for maintainability.)

Features:
- Text extraction using PyMuPDF with OCR fallback (pytesseract + EasyOCR)
- Table extraction using camelot (optional)
- Image extraction via PyMuPDF
- ZIP processing helpers and parallel processing
"""

import os
import uuid
import zipfile
import tempfile
import logging
import concurrent.futures
import asyncio
import json
import time
import io
import shutil
from typing import Tuple, List, Optional, Union, Dict, Any
from pathlib import Path

# Imaging / OCR (defensive imports)
from PIL import Image
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
try:
    import pytesseract
except ImportError:
    pytesseract = None

# optional numeric + OCR libs
try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:
    np = None
    _HAS_NUMPY = False

# optional advanced libs
try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    pdfplumber = None
    _HAS_PDFPLUMBER = False

try:
    from pdf2image import convert_from_path
    _HAS_PDF2IMAGE = True
except ImportError:
    convert_from_path = None
    _HAS_PDF2IMAGE = False

try:
    import easyocr
    _HAS_EASYOCR = True
except ImportError:
    easyocr = None
    _HAS_EASYOCR = False

try:
    import camelot
    _HAS_CAMELOT = True
except ImportError:
    camelot = None
    _HAS_CAMELOT = False


logger = logging.getLogger(__name__)

class GodLevelPDFProcessor:
    """God-Level PDF Processing System with OCR, table extraction, and advanced features"""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        max_workers: int = 4,
        enable_advanced_features: bool = True,
    ):
        self.max_workers = max_workers
        self.enable_advanced_features = enable_advanced_features
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # EasyOCR reader (optional)
        self.easyocr_reader = None
        if _HAS_EASYOCR and enable_advanced_features:
            try:
                # only initialize if numpy available (easyocr uses numpy arrays)
                if _HAS_NUMPY:
                    self.easyocr_reader = easyocr.Reader(["en"])
                else:
                    logger.warning("numpy not installed: skipping EasyOCR initialization")
            except Exception as e:
                logger.warning("Failed to initialize EasyOCR: %s", e)

    # -------------------------
    # Text extraction (PyMuPDF) with OCR fallback
    # -------------------------
    def extract_text_with_ocr_fallback(self, pdf_path: Union[str, Path]) -> str:
        text_parts: List[str] = []
        pdf_path = str(pdf_path)
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error("Failed to open PDF %s: %s", pdf_path, e)
            raise

        try:
            for page_num, page in enumerate(doc, start=1):
                try:
                    extracted = page.get_text() or ""
                    # Use OCR if little or no text
                    if not extracted.strip() or len(extracted.strip()) < 50:
                        logger.info("Using OCR for page %d in %s", page_num, Path(pdf_path).name)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                        ocr_text = self._enhanced_ocr(img)
                        extracted = ocr_text if ocr_text else extracted
                    text_parts.append(f"\n\n--- Page {page_num} ---\n\n{extracted}")
                except Exception as e:
                    logger.exception("Failed on page %d of %s: %s", page_num, pdf_path, e)
                    text_parts.append(f"\n\n--- Page {page_num} (error) ---\n\n")
        finally:
            try:
                doc.close()
            except Exception:
                pass

        return "\n".join(text_parts).strip()

    def _enhanced_ocr(self, img: Image.Image) -> str:
        results: List[str] = []

        # Tesseract
        try:
            tesseract_text = pytesseract.image_to_string(img, config="--psm 6")
            if tesseract_text and tesseract_text.strip():
                results.append(tesseract_text)
        except Exception as e:
            logger.warning("Tesseract OCR failed: %s", e)

        # EasyOCR
        if self.easyocr_reader:
            try:
                import numpy as _np  # local import - we already checked availability
                arr = _np.array(img)
                easy_res = self.easyocr_reader.readtext(arr, detail=0)
                easy_text = "\n".join(easy_res)
                if easy_text.strip():
                    results.append(easy_text)
            except Exception as e:
                logger.warning("EasyOCR failed: %s", e)

        # Choose longest result (heuristic)
        if results:
            return max(results, key=len)
        return ""

    # -------------------------
    # Table & image extraction
    # -------------------------
    def extract_tables(self, pdf_path: Union[str, Path]) -> List[Dict[str, Any]]:
        if not (_HAS_CAMELOT and self.enable_advanced_features):
            return []
        try:
            tables = []
            camelot_tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="stream")
            for i, table in enumerate(camelot_tables):
                tables.append({
                    "page": table.page,
                    "content": table.df.to_dict(),
                    "accuracy": getattr(table, "accuracy", None),
                    "whitespace": getattr(table, "whitespace", None),
                    "order": i,
                })
            logger.info("Extracted %d tables from %s", len(tables), Path(pdf_path).name)
            return tables
        except Exception as e:
            logger.warning("Camelot table extraction failed for %s: %s", pdf_path, e)
            return []

    def extract_images(self, pdf_path: Union[str, Path]) -> List[Dict[str, Any]]:
        images = []
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            logger.error("Failed to open PDF for image extraction %s: %s", pdf_path, e)
            return images

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image.get("image")
                        image_ext = base_image.get("ext")
                        images.append({
                            "page": page_num + 1,
                            "index": img_index,
                            "format": image_ext,
                            "size": len(image_bytes) if image_bytes else 0,
                            "width": base_image.get("width", 0),
                            "height": base_image.get("height", 0),
                        })
                    except Exception as e:
                        logger.warning("Failed to extract image on page %d idx %d: %s", page_num + 1, img_index, e)
        finally:
            try:
                doc.close()
            except Exception:
                pass

        logger.info("Extracted %d images from %s", len(images), Path(pdf_path).name)
        return images

    def _chunk_text(self, text: str) -> List[str]:
        """Pure python overlapping chunk generator with positive step guard."""
        if not text:
            return []
        eff_size = max(1, int(self.chunk_size or 1000))
        eff_overlap = max(0, int(self.chunk_overlap or 0))
        step = max(1, eff_size - eff_overlap)
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = start + eff_size
            chunks.append(text[start:end])
            if end >= text_len:
                break
            start += step
        return chunks

    # -------------------------
    # Single PDF processing (text/chunks/tables/images)
    # -------------------------
    def process_single_pdf(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        pdf_path = Path(pdf_path)
        logger.info("Processing PDF: %s", pdf_path.name)
        result: Dict[str, Any] = {
            "metadata": {
                "filename": pdf_path.name,
                "file_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
                "processed_at": time.time(),
                "file_id": str(uuid.uuid4()),
            },
            "content": {},
        }
        try:
            text = self.extract_text_with_ocr_fallback(pdf_path)
            result["content"]["text"] = text
            if self.enable_advanced_features:
                result["content"]["tables"] = self.extract_tables(pdf_path)
                result["content"]["images"] = self.extract_images(pdf_path)

            # split into chunks
            chunks = self._chunk_text(text)
            result["content"]["chunks"] = chunks
            logger.info("Successfully processed %s (chunks=%d)", pdf_path.name, len(chunks))
        except Exception as e:
            logger.exception("Failed to process %s: %s", pdf_path.name, e)
            result["error"] = str(e)
        return result

    # -------------------------
    # Parallel processing helpers
    # -------------------------
    def process_multiple_pdfs(self, pdf_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {executor.submit(self.process_single_pdf, p): p for p in pdf_paths}
            for future in concurrent.futures.as_completed(future_to_path):
                p = future_to_path[future]
                try:
                    results[str(p)] = future.result()
                except Exception as e:
                    results[str(p)] = {"error": str(e)}
        return results

    # -------------------------
    # ZIP processing helpers
    # -------------------------
    def extract_zip_to_temp(self, zip_path: str) -> str:
        temp_dir = tempfile.mkdtemp()
        real_temp = os.path.realpath(temp_dir)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for member in zip_ref.infolist():
                target_path = os.path.realpath(os.path.join(real_temp, member.filename))
                if not (target_path == real_temp or target_path.startswith(real_temp + os.sep)):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    raise ValueError(f"Blocked unsafe ZIP path traversal entry: {member.filename}")
                zip_ref.extract(member, real_temp)
        return temp_dir

    def get_all_pdf_paths(self, folder_path: str) -> List[str]:
        pdf_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
        return pdf_files

    def process_zip_file(self, zip_path: str) -> Dict[str, Any]:
        temp_dir = self.extract_zip_to_temp(zip_path)
        try:
            pdf_paths = self.get_all_pdf_paths(temp_dir)
            if not pdf_paths:
                raise ValueError("No PDF files found in ZIP")
            results = self.process_multiple_pdfs(pdf_paths)
            return results
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def save_processing_report(self, results: Dict[str, Any], output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info("Processing report saved to %s", output_path)


# Example usage guard (very small demo)
if __name__ == "__main__":
    p = GodLevelPDFProcessor(max_workers=2, enable_advanced_features=True)
    # Replace with an actual file to test:
    # print(p.process_single_pdf("example.pdf"))
