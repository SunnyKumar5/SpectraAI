"""
JCAMP-DX File Parser for SpectraAI.

Reads JCAMP-DX format (.dx, .jdx) spectral data files commonly
exported from NMR spectrometers (Bruker, JEOL, Varian) and IR
instruments. Extracts header metadata and data tables.

Reference: IUPAC JCAMP-DX standard (DOI: 10.1351/pac198860121685)
"""

from __future__ import annotations

import re
from typing import Optional

from ..core.nmr_data import NMRData, NMRPeak
from ..core.ir_data import IRData, IRAbsorption


# ── JCAMP label-data record pattern ──────────────────────────────────────────
_LDR_PATTERN = re.compile(r"^##(.+?)=\s*(.*)", re.MULTILINE)
# Data table row: X  Y1  Y2  ...
_DATA_ROW = re.compile(r"([-+]?\d+\.?\d*(?:[eE][-+]?\d+)?)")


class JCAMPParser:
    """
    Parser for JCAMP-DX spectral data files.

    Supports NMR and IR data blocks. Reads both XY (XYDATA)
    and peak table (PEAKTABLE) formats.

    Usage:
        parser = JCAMPParser()
        result = parser.parse_file("spectrum.jdx")
        # result is NMRData or IRData depending on data type
    """

    def parse_file(self, filepath: str) -> dict:
        """
        Parse a JCAMP-DX file and return structured data.

        Args:
            filepath: Path to .jdx / .dx file

        Returns:
            dict with keys:
                'type':    'NMR' | 'IR' | 'MASS' | 'UV' | 'UNKNOWN'
                'header':  dict of JCAMP header fields
                'x':       list of x-axis values
                'y':       list of y-axis values
                'peaks':   list of (x, y) peak tuples (if PEAKTABLE)
        """
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return self.parse_text(content)

    def parse_text(self, content: str) -> dict:
        """Parse JCAMP-DX text content."""
        header = self._extract_header(content)
        data_type = self._determine_type(header)

        result = {
            "type": data_type,
            "header": header,
            "x": [],
            "y": [],
            "peaks": [],
        }

        # Extract data based on format
        if "PEAKTABLE" in header:
            result["peaks"] = self._extract_peak_table(content)
        elif "XYDATA" in header or "XYPOINTS" in header:
            x, y = self._extract_xy_data(content, header)
            result["x"] = x
            result["y"] = y

        return result

    def parse_nmr(self, filepath: str) -> Optional[NMRData]:
        """
        Parse a JCAMP-DX NMR file into NMRData.

        Returns NMRData with peaks extracted from the file,
        or None if parsing fails.
        """
        try:
            data = self.parse_file(filepath)
        except Exception:
            return None

        if data["type"] not in ("NMR", "UNKNOWN"):
            return None

        header = data["header"]
        nucleus = header.get(".OBSERVENUCLEUS", "1H").strip("^").strip()
        frequency = 0
        freq_str = header.get(".OBSERVEFREQUENCY", "")
        if freq_str:
            try:
                frequency = int(float(freq_str))
            except ValueError:
                pass

        solvent = header.get(".SOLVENTNAME", "CDCl3")

        peaks = []
        if data["peaks"]:
            for x_val, y_val in data["peaks"]:
                peaks.append(NMRPeak(chemical_shift=x_val))
        elif data["x"] and data["y"]:
            # Extract peaks from continuous data via simple peak picking
            peaks = self._pick_peaks_from_xy(data["x"], data["y"])

        return NMRData(
            nucleus=nucleus,
            frequency=frequency,
            solvent=solvent,
            peaks=peaks,
        )

    def parse_ir(self, filepath: str) -> Optional[IRData]:
        """
        Parse a JCAMP-DX IR file into IRData.

        Returns IRData with absorptions extracted from the file,
        or None if parsing fails.
        """
        try:
            data = self.parse_file(filepath)
        except Exception:
            return None

        absorptions = []
        if data["peaks"]:
            for x_val, y_val in data["peaks"]:
                if 400 <= x_val <= 4000:
                    absorptions.append(IRAbsorption(wavenumber=x_val))
        elif data["x"] and data["y"]:
            # Simple peak detection from continuous IR data
            import numpy as np
            x = np.array(data["x"])
            y = np.array(data["y"])
            # For transmittance data, peaks are minima
            is_transmittance = "TRANSMITTANCE" in str(data["header"].get("YUNITS", "")).upper()
            if is_transmittance:
                y = -y  # invert for peak finding
            indices = self._find_local_maxima(y, min_distance=10)
            for idx in indices:
                wn = x[idx]
                if 400 <= wn <= 4000:
                    absorptions.append(IRAbsorption(wavenumber=float(wn)))

        return IRData(absorptions=absorptions)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _extract_header(self, content: str) -> dict:
        """Extract all labeled data records from JCAMP header."""
        header = {}
        for match in _LDR_PATTERN.finditer(content):
            label = match.group(1).strip().upper()
            value = match.group(2).strip()
            header[label] = value
        return header

    def _determine_type(self, header: dict) -> str:
        """Determine the spectral data type from header fields."""
        data_type = header.get("DATATYPE", header.get("DATA TYPE", "")).upper()
        if "NMR" in data_type or "NUCLEAR" in data_type:
            return "NMR"
        elif "INFRARED" in data_type or "IR" in data_type:
            return "IR"
        elif "MASS" in data_type:
            return "MASS"
        elif "UV" in data_type or "ULTRAVIOLET" in data_type:
            return "UV"

        # Check x-axis units for hints
        x_units = header.get("XUNITS", "").upper()
        if "PPM" in x_units or "HZ" in x_units:
            return "NMR"
        elif "1/CM" in x_units or "WAVENUMBER" in x_units:
            return "IR"
        elif "M/Z" in x_units:
            return "MASS"

        return "UNKNOWN"

    def _extract_peak_table(self, content: str) -> list[tuple[float, float]]:
        """Extract peaks from a PEAKTABLE block."""
        peaks = []
        in_table = False

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("##PEAKTABLE") or line.startswith("##PEAK TABLE"):
                in_table = True
                continue
            if line.startswith("##END") or (line.startswith("##") and in_table):
                if in_table and line.startswith("##END"):
                    break
                if in_table and not line.startswith("##PEAKTABLE"):
                    in_table = False
                    break
            if in_table and line and not line.startswith("##"):
                numbers = _DATA_ROW.findall(line)
                if len(numbers) >= 2:
                    peaks.append((float(numbers[0]), float(numbers[1])))

        return peaks

    def _extract_xy_data(self, content: str, header: dict) -> tuple[list, list]:
        """Extract continuous XY data."""
        x_values = []
        y_values = []
        in_data = False

        # Get axis parameters for decompression
        first_x = float(header.get("FIRSTX", "0"))
        last_x = float(header.get("LASTX", "0"))
        n_points = int(header.get("NPOINTS", "0"))
        x_factor = float(header.get("XFACTOR", "1"))
        y_factor = float(header.get("YFACTOR", "1"))

        for line in content.split("\n"):
            line = line.strip()
            if "XYDATA" in line or "XYPOINTS" in line:
                in_data = True
                continue
            if line.startswith("##END") and in_data:
                break
            if line.startswith("##") and in_data:
                in_data = False
                break
            if in_data and line and not line.startswith("##"):
                numbers = _DATA_ROW.findall(line)
                if numbers:
                    x_val = float(numbers[0]) * x_factor
                    for y_str in numbers[1:]:
                        x_values.append(x_val)
                        y_values.append(float(y_str) * y_factor)
                        if n_points > 0 and last_x != first_x:
                            x_val += (last_x - first_x) / (n_points - 1)

        return x_values, y_values

    def _pick_peaks_from_xy(self, x: list, y: list,
                             threshold: float = 0.05) -> list[NMRPeak]:
        """Simple peak picking from continuous XY data."""
        peaks = []
        if len(x) < 3:
            return peaks

        y_max = max(abs(v) for v in y) if y else 1.0
        for i in range(1, len(y) - 1):
            if (y[i] > y[i-1] and y[i] > y[i+1] and
                    abs(y[i]) / y_max > threshold):
                peaks.append(NMRPeak(chemical_shift=round(x[i], 2)))

        return peaks

    def _find_local_maxima(self, y, min_distance: int = 5) -> list[int]:
        """Find indices of local maxima in array."""
        maxima = []
        for i in range(min_distance, len(y) - min_distance):
            if all(y[i] >= y[i-j] for j in range(1, min_distance + 1)):
                if all(y[i] >= y[i+j] for j in range(1, min_distance + 1)):
                    maxima.append(i)
        return maxima
