"""
Spectral data parsers for SpectraAI.

Parsers convert raw text, files (JCAMP-DX, CSV), and
structured data into typed core data objects.
"""

from .nmr_text_parser import NMRTextParser, parse_h1_nmr_text, parse_c13_nmr_text
from .ir_parser import IRTextParser, parse_ir_text
from .ms_parser import MSTextParser, parse_ms_text

__all__ = [
    "NMRTextParser", "parse_h1_nmr_text", "parse_c13_nmr_text",
    "IRTextParser", "parse_ir_text",
    "MSTextParser", "parse_ms_text",
]
