"""
Image Processor Tool (Ultra Beast Edition)
Robust image ingestion, OCR (pytesseract), cleaning, EXIF metadata extraction,
resizing, optional OpenCV processing, and embedding generation with GPU-aware model.
"""

import logging, os, io, time, hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import asyncio

from PIL import Image, ExifTags, ImageOps
import numpy as np

# defensive cv2 + pytesseract + sentence-transformers
try:
    import cv2
except Exception:
    cv2 = None
try:
    import pytesseract
except Exception:
    pytesseract = None
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

logger = logging.getLogger("image_processor")
logger.addHandler(logging.NullHandler())

@dataclass
class ImageProcessResult:
    text: str
    metadata: Dict[str, Any]
    embeddings: Optional[np.ndarray]
    image_shape: Optional[tuple]
    timestamp: datetime
    provenance: Dict[str, Any] = None

class ImageProcessor:
    def __init__(self, emb_model_name: str = "clip-ViT-B-32", device="cpu"):
        self._emb_model_name = emb_model_name
        self._device = device
        self._emb = None
        self._load_model()

    def _load_model(self):
        # TEMPORARILY DISABLED to reduce memory usage - avoids loading 400MB clip-ViT-B-32 model
        logger.info("Image embedding model loading DISABLED to save memory")
        return

        if SentenceTransformer is None:
            logger.warning("SentenceTransformer not available - image embeddings disabled")
            return
        try:
            self._emb = SentenceTransformer(self._emb_model_name, device=("cuda" if self._device.startswith("cuda") else "cpu"))
            logger.info(f"Loaded image embedding model {self._emb_model_name}")
        except Exception as e:
            logger.error(f"Failed to load image embedding model: {e}")
            self._emb = None

    def _extract_exif(self, pil_img: Image.Image) -> Dict[str, Any]:
        try:
            raw = pil_img._getexif()
            if not raw:
                return {}
            return {ExifTags.TAGS.get(k,k): v for k,v in raw.items() if k in ExifTags.TAGS}
        except Exception:
            return {}

    def _preprocess(self, pil_img: Image.Image, resize: Optional[tuple]=None, to_grayscale: bool=False) -> Image.Image:
        img = pil_img.convert("RGB")
        if resize:
            img = ImageOps.fit(img, resize, Image.LANCZOS)
        if to_grayscale:
            img = img.convert("L")
        return img

    def process_image(self, path_or_bytes: Any, resize: Optional[tuple]=(1024,1024), ocr_lang: str = "eng") -> ImageProcessResult:
        ts = time.time()
        # load PIL image from path or bytes
        if isinstance(path_or_bytes, (bytes, bytearray)):
            pil = Image.open(io.BytesIO(path_or_bytes))
        else:
            pil = Image.open(path_or_bytes)

        img = self._preprocess(pil, resize=resize)
        text = ""
        if pytesseract is not None:
            try:
                text = pytesseract.image_to_string(img, lang=ocr_lang)
            except Exception as e:
                logger.error(f"OCR failed: {e}")
                text = ""
        meta = self._extract_exif(pil)
        emb = None
        if self._emb:
            try:
                emb = self._emb.encode([text], show_progress_bar=False)[0]
            except Exception as e:
                logger.error(f"Image embedding failed: {e}")
                emb = None

        prov = {"source": getattr(path_or_bytes, "name", None) or "bytes", "processing_time": time.time()-ts}
        shape = img.size
        return ImageProcessResult(text=text, metadata=meta, embeddings=emb, image_shape=shape, timestamp=datetime.now(), provenance=prov)

    async def aprocess_image(self, path_or_bytes: Any, resize: Optional[tuple]=(1024,1024), ocr_lang: str = "eng") -> ImageProcessResult:
        return await asyncio.to_thread(self.process_image, path_or_bytes, resize, ocr_lang)

# singleton
image_processor = ImageProcessor()
    
