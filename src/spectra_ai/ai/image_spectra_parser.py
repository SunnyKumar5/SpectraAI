"""
Parser to convert images or PDFs of spectra into structured JSON using Vision LLMs.
"""

import os
from typing import Optional, List
from PIL import Image
from .llm_client import LLMClient
from .prompts.parse_spectra_image import PARSE_SPECTRA_IMAGE_SYSTEM, PARSE_SPECTRA_IMAGE_USER

class ImageSpectraParser:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def parse_files(self, file_paths: List[str]) -> Optional[dict]:
        """
        Takes a list of image or PDF paths, converts them to PIL Images,
        and uses the LLM to extract spectra data into the standard JSON format.
        """
        images = []
        for path in file_paths:
            ext = path.lower().split('.')[-1]
            if ext == 'pdf':
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(path)
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(dpi=300)
                        mode = "RGBA" if pix.alpha else "RGB"
                        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                        images.append(img)
                except ImportError:
                    raise ImportError("pymupdf is required for PDF parsing. Run: pip install pymupdf")
            else:
                # Assume standard image (png, jpeg, jpg)
                img = Image.open(path).convert('RGB')
                images.append(img)
                
        if not images:
            return None

        # Call the LLM
        result_json = self.llm.generate_json(
            system=PARSE_SPECTRA_IMAGE_SYSTEM,
            user=PARSE_SPECTRA_IMAGE_USER,
            temperature=0.1,
            images=images
        )
        
        return result_json
