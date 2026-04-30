#!/usr/bin/env python3
"""
SpectraAI — Multi-Spectral Generative AI Suite
Quick run script for development.

Usage:
    python run.py
    python run.py --debug
    python run.py --no-splash
"""
import sys
import os

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from spectra_ai.main import main

if __name__ == "__main__":
    main()
