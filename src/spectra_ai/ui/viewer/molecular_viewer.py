"""
MolecularViewer — 3D molecular structure viewer powered by 3Dmol.js.

Renders SDF conformers in a QWebEngineView with:
  - Stick / Ball+Stick / Spacefill / Wireframe display styles
  - Custom CPK colour scheme (dark-theme optimised)
  - Conformer carousel (◀ / ▶)
  - Heteroatom highlight toggle
  - Atom-click bridge (Python ↔ JS via QWebChannel)
  - Background conformer generation via QThread (RDKit optional)
  - Graceful fallback to a styled QLabel when PyQtWebEngine is absent
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QCheckBox, QSizePolicy, QFrame, QMessageBox,
    QFileDialog, QRadioButton,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer, QSettings
from PyQt5.QtGui import QFont, QPixmap

# ── Optional: PyQtWebEngine ───────────────────────────────────────────────────
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtWebChannel import QWebChannel
    from PyQt5.QtCore import pyqtSlot
    _HAS_WEBENGINE = True
except ImportError:
    _HAS_WEBENGINE = False
    # Dummy decorator so the rest of the module parses without error
    def pyqtSlot(*args, **kwargs):  # type: ignore[misc]
        def decorator(func):
            return func
        return decorator

from ..styles.colors import Colors, FONT_FAMILY
from ...chem.conformer_generator import ConformerGenerator

# ── 3Dmol.js paths ────────────────────────────────────────────────────────────
_VIEWER_DIR = Path(__file__).parent
_3DMOL_LOCAL = _VIEWER_DIR / "3dmol-min.js"
_3DMOL_CDN = "https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"

# ── Custom CPK colour map (dark-theme optimised) ──────────────────────────────
_ELEMENT_COLORS = {
    "C": "#E2E8F0",
    "N": "#60A5FA",
    "O": "#F87171",
    "S": "#FCD34D",
    "F": "#A78BFA",
    "Cl": "#34D399",
    "Br": "#FB923C",
    "I":  "#E879F9",
    "H":  "#64748B",
    "P":  "#F97316",
    "Si": "#94A3B8",
    "B":  "#FDE68A",
}


# ══════════════════════════════════════════════════════════════════════════════
#  QWebChannel bridge: Python ↔ JavaScript
# ══════════════════════════════════════════════════════════════════════════════

class AtomClickBridge(QObject):
    """
    QObject exposed to JavaScript via QWebChannel.

    JavaScript calls:
        bridge.atomClicked(atomIndex)
        bridge.viewerReady()
        bridge.screenshotReady(base64png)
        bridge.measurementReady(type, value, atomIndicesJson)
    """

    atom_clicked_signal = pyqtSignal(int)
    viewer_ready_signal = pyqtSignal()
    screenshot_ready_signal = pyqtSignal(str)       # base64 PNG data
    measurement_ready_signal = pyqtSignal(str, float, str)  # type, value, atomsJson

    @pyqtSlot(int)
    def atomClicked(self, atom_index: int):  # noqa: N802 — JS naming
        self.atom_clicked_signal.emit(atom_index)

    @pyqtSlot()
    def viewerReady(self):  # noqa: N802
        self.viewer_ready_signal.emit()

    @pyqtSlot(str)
    def screenshotReady(self, base64_png: str):  # noqa: N802
        self.screenshot_ready_signal.emit(base64_png)

    @pyqtSlot(str, float, str)
    def measurementReady(self, mtype: str, value: float, atoms_json: str):  # noqa: N802
        self.measurement_ready_signal.emit(mtype, value, atoms_json)


# ══════════════════════════════════════════════════════════════════════════════
#  Background thread for conformer generation
# ══════════════════════════════════════════════════════════════════════════════

class _ConformerWorker(QThread):
    """Generate conformers off the main thread."""

    finished = pyqtSignal(list)   # list[tuple[str, float]] (sdf_block, energy)

    def __init__(self, smiles: str, n: int = 10, parent=None):
        super().__init__(parent)
        self._smiles = smiles
        self._n = n

    def run(self):
        gen = ConformerGenerator()
        results = gen.generate_with_energies(self._smiles, self._n)
        if not results:
            # Fallback to plain generate
            blocks = gen.generate(self._smiles, self._n)
            results = [(b, 0.0) for b in blocks]
        self.finished.emit(results)


# ══════════════════════════════════════════════════════════════════════════════
#  HTML template builder
# ══════════════════════════════════════════════════════════════════════════════

def _build_viewer_html(use_local_js: bool) -> str:
    """
    Return the full HTML page for the 3D viewer.

    The JavaScript section is built as a plain string (no f-string) to avoid
    brace-escaping issues. Only CSS colour values are injected via f-string in
    the header portion.
    """
    color_map_js = json.dumps(_ELEMENT_COLORS)

    # Relative path works when setHtml is called with the viewer dir as base URL
    js_src_tag = ('<script src="3dmol-min.js"></script>' if use_local_js
                  else f'<script src="{_3DMOL_CDN}"></script>')

    # ── HTML + CSS (f-string: needs Python colour values) ─────────────────────
    html_head = (
        '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<style>\n'
        '* { margin:0; padding:0; box-sizing:border-box; }\n'
        f'html, body {{ width:100%; height:100%; background:#080D1A; overflow:hidden; }}\n'
        '#bg-grid {\n'
        '  position:absolute; top:0; left:0; width:100%; height:100%;\n'
        '  background:\n'
        '    radial-gradient(ellipse at 20% 50%, rgba(6,182,212,0.06) 0%, transparent 60%),\n'
        '    radial-gradient(ellipse at 80% 50%, rgba(139,92,246,0.05) 0%, transparent 60%),\n'
        '    linear-gradient(rgba(30,45,69,0.18) 1px, transparent 1px),\n'
        '    linear-gradient(90deg, rgba(30,45,69,0.18) 1px, transparent 1px);\n'
        '  background-size: 100% 100%, 100% 100%, 40px 40px, 40px 40px;\n'
        '  pointer-events:none; z-index:0;\n'
        '}\n'
        '#viewer { width:100%; height:100%; position:absolute; top:0; left:0; z-index:1; }\n'
        '#loading {\n'
        '  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);\n'
        f'  color:{Colors.TEXT_SECONDARY}; font-family:\'{FONT_FAMILY}\',sans-serif;\n'
        '  font-size:14px; text-align:center; pointer-events:none; z-index:10;\n'
        '}\n'
        '#atom-info {\n'
        '  position:absolute; bottom:12px; left:50%; transform:translateX(-50%);\n'
        '  background:rgba(8,13,26,0.92); color:#F1F5F9;\n'
        '  padding:5px 14px; border-radius:20px; font-size:12px;\n'
        f'  font-family:\'{FONT_FAMILY}\',sans-serif;\n'
        '  border:1px solid rgba(59,130,246,0.3); display:none;\n'
        '  pointer-events:none; z-index:20; white-space:nowrap;\n'
        '  box-shadow: 0 0 12px rgba(6,182,212,0.15);\n'
        '}\n'
        '#axis-corner {\n'
        '  position:absolute; bottom:42px; left:10px;\n'
        '  font-size:13px; font-weight:700; letter-spacing:5px;\n'
        '  pointer-events:none; z-index:20; opacity:0.7;\n'
        '}\n'
        '</style>\n</head>\n<body>\n'
        '<div id="bg-grid"></div>\n'
        '<div id="viewer"></div>\n'
        '<div id="loading">Loading 3D viewer\u2026</div>\n'
        '<div id="atom-info"></div>\n'
        '<div id="axis-corner">'
        '<span style="color:#FF5555">X</span>'
        '<span style="color:#4ADE80">Y</span>'
        '<span style="color:#60A5FA">Z</span>'
        '</div>\n\n'
        + js_src_tag + '\n'
        '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>\n'
        '<script>\n"use strict";\n\n'
        'var ELEMENT_COLORS = '
    )

    # ── Pure JavaScript (plain string — zero f-string brace escaping) ─────────
    js = (
        color_map_js + ';\n\n'

        'var _viewer     = null;\n'
        'var _models     = [];\n'
        'var _bridge     = null;\n'
        'var _style      = "stick";\n'
        'var _showH      = true;\n'
        'var _clickShape = null;\n'
        'var _bgColor    = "0x080D1A";\n'
        'var _atomLabels  = [];\n'
        'var _measureMode = false;\n'
        'var _mAtoms      = [];\n'
        'var _mShapes     = [];\n'
        'var _mLabels     = [];\n'
        'var _coordMode   = false;\n'
        'var _originAtom  = null;\n'
        'var _axisShapes  = [];\n'
        'var _axisLabels  = [];\n\n'

        '// ── Init: wait for 3Dmol + QWebChannel ─────────────────────────────\n'
        'function tryInit() {\n'
        '  if (typeof $3Dmol === "undefined" || typeof QWebChannel === "undefined") {\n'
        '    setTimeout(tryInit, 100);\n'
        '    return;\n'
        '  }\n'
        '  new QWebChannel(qt.webChannelTransport, function(ch) {\n'
        '    _bridge = ch.objects.bridge;\n'
        '    _initViewer();\n'
        '  });\n'
        '}\n'
        '// Timeout error message if 3Dmol never loads\n'
        'setTimeout(function() {\n'
        '  if (!_viewer) {\n'
        '    document.getElementById("loading").innerHTML =\n'
        '      "3D library failed to load.<br>Check internet connection or install 3dmol-min.js locally.";\n'
        '  }\n'
        '}, 12000);\n'
        'tryInit();\n\n'

        'var _hoverShape = null;\n\n'

        '// Re-register click + hover handlers on current atoms.\n'
        '// Must be called after every addModel() because setClickable\n'
        '// only marks atoms that exist at call-time.\n'
        'function _registerClickHandlers() {\n'
        '  if (!_viewer) return;\n'
        '  _viewer.setClickable({}, true, function(atom, viewer) {\n'
        '    if (_measureMode) { _onMeasureClick(atom, viewer); return; }\n'
        '    if (_coordMode) { if (atom) setOriginAtom(atom, viewer); return; }\n'
        '    if (_clickShape) { viewer.removeShape(_clickShape); _clickShape = null; }\n'
        '    if (!atom) return;\n'
        '    _clickShape = viewer.addSphere({\n'
        '      center: {x: atom.x, y: atom.y, z: atom.z},\n'
        '      radius: 0.48, color: "#FFD700", alpha: 0.72\n'
        '    });\n'
        '    var info = document.getElementById("atom-info");\n'
        '    var bText = atom.bonds && atom.bonds.length\n'
        '      ? "  \u2022  " + atom.bonds.length + "\u00a0bonds" : "";\n'
        '    info.textContent = atom.elem\n'
        '      + (atom.resn ? "  \u2022  " + atom.resn : "")\n'
        '      + "  \u2022  idx\u00a0" + (atom.index !== undefined ? atom.index : "?")\n'
        '      + bText;\n'
        '    info.style.display = "block";\n'
        '    viewer.render();\n'
        '    if (_bridge) { _bridge.atomClicked(atom.index !== undefined ? atom.index : 0); }\n'
        '  });\n'
        '  _viewer.setHoverable({}, true,\n'
        '    function(atom, viewer) {\n'
        '      if (_hoverShape) { viewer.removeShape(_hoverShape); }\n'
        '      if (!atom) return;\n'
        '      _hoverShape = viewer.addSphere({\n'
        '        center: {x: atom.x, y: atom.y, z: atom.z},\n'
        '        radius: 0.36, color: "#FFFFFF", alpha: 0.28\n'
        '      });\n'
        '      viewer.render();\n'
        '    },\n'
        '    function(atom, viewer) {\n'
        '      if (_hoverShape) { viewer.removeShape(_hoverShape); _hoverShape = null; }\n'
        '      viewer.render();\n'
        '    }\n'
        '  );\n'
        '}\n\n'

        'function _initViewer() {\n'
        '  var el = document.getElementById("viewer");\n'
        '  if (el.clientWidth < 10 || el.clientHeight < 10) {\n'
        '    setTimeout(_initViewer, 200);\n'
        '    return;\n'
        '  }\n'
        '  document.getElementById("loading").style.display = "none";\n'
        '  _viewer = $3Dmol.createViewer(el, {\n'
        '    backgroundColor: _bgColor, antialias: true, id: "main"\n'
        '  });\n'
        '  _viewer.render();\n'
        '  window.addEventListener("resize", function() { if (_viewer) _viewer.resize(); });\n'
        '  if (_bridge) { _bridge.viewerReady(); }\n'
        '}\n\n'

        'function loadMolecule(sdfBlock) {\n'
        '  if (!_viewer) return;\n'
        '  _viewer.removeAllModels();\n'
        '  _viewer.removeAllShapes();\n'
        '  _viewer.removeAllLabels();\n'
        '  _models = [];\n'
        '  _clickShape = null;\n'
        '  _axisShapes=[]; _axisLabels=[]; _originAtom=null;\n'
        '  _mShapes=[]; _mLabels=[]; _mAtoms=[];\n'
        '  document.getElementById("atom-info").style.display = "none";\n'
        '  var model = _viewer.addModel(sdfBlock, "sdf");\n'
        '  _models.push(model);\n'
        '  applyStyle(_style);\n'
        '  _registerClickHandlers();\n'
        '  if (_atomLabels.length > 0) { toggleLabels(false); toggleLabels(true); }\n'
        '  _viewer.zoomTo();\n'
        '  _viewer.render();\n'
        '}\n\n'

        'function applyStyle(name) {\n'
        '  if (!_viewer || _models.length === 0) return;\n'
        '  _style = name;\n'
        '  var cs = {colorscheme: {prop: "elem", map: ELEMENT_COLORS}};\n'
        '  if (name === "stick") {\n'
        '    _viewer.setStyle({}, {stick: cs});\n'
        '  } else if (name === "ballstick") {\n'
        '    _viewer.setStyle({}, {stick: {colorscheme: cs.colorscheme, radius: 0.12},\n'
        '                           sphere: {colorscheme: cs.colorscheme, scale: 0.25}});\n'
        '  } else if (name === "spacefill") {\n'
        '    _viewer.setStyle({}, {sphere: cs});\n'
        '  } else if (name === "wire") {\n'
        '    _viewer.setStyle({}, {line: cs});\n'
        '  }\n'
        '  if (!_showH) { _viewer.setStyle({elem: "H"}, {hidden: true}); }\n'
        '  _viewer.render();\n'
        '}\n\n'

        'function toggleHydrogens(show) { _showH = show; applyStyle(_style); }\n\n'

        'function highlightHeteroatoms() {\n'
        '  if (!_viewer || _models.length === 0) return;\n'
        '  _viewer.setStyle({}, {stick: {color: "#3A3A4A"}});\n'
        '  _viewer.setStyle({elem: "C"}, {stick: {color: "#3A3A4A"}});\n'
        '  _viewer.setStyle({elem: "H"}, _showH ? {stick: {color: "#3A3A4A"}} : {hidden: true});\n'
        '  var hetero = ["N","O","S","F","Cl","Br","I","P","Si","B"];\n'
        '  for (var i = 0; i < hetero.length; i++) {\n'
        '    var el  = hetero[i];\n'
        '    var col = ELEMENT_COLORS[el] || "#ffffff";\n'
        '    if (_style === "spacefill") {\n'
        '      _viewer.setStyle({elem: el}, {sphere: {color: col}});\n'
        '    } else {\n'
        '      _viewer.setStyle({elem: el}, {stick: {color: col, radius: 0.22}});\n'
        '    }\n'
        '  }\n'
        '  _viewer.render();\n'
        '}\n\n'

        'function unhighlightAll() { applyStyle(_style); }\n\n'

        '// ── Atom labels ──────────────────────────────────────────────────────\n'
        'function toggleLabels(show) {\n'
        '  for (var i=0; i<_atomLabels.length; i++) { _viewer.removeLabel(_atomLabels[i]); }\n'
        '  _atomLabels = [];\n'
        '  if (show && _viewer && _models.length > 0) {\n'
        '    try {\n'
        '      var atoms = _models[0].selectedAtoms({});\n'
        '      if (atoms && atoms.length) {\n'
        '        for (var i=0; i<atoms.length; i++) {\n'
        '          var a = atoms[i];\n'
        '          if (!a.elem || a.elem === "H") continue;\n'
        '          var lbl = _viewer.addLabel(a.elem, {\n'
        '            position: {x:a.x, y:a.y, z:a.z},\n'
        '            backgroundColor: "rgba(0,0,0,0.65)",\n'
        '            fontColor: ELEMENT_COLORS[a.elem] || "#FFFFFF",\n'
        '            fontSize: 11, borderThickness: 0, inFront: true\n'
        '          });\n'
        '          _atomLabels.push(lbl);\n'
        '        }\n'
        '      }\n'
        '    } catch(e) { console.warn("toggleLabels:", e); }\n'
        '  }\n'
        '  _viewer.render();\n'
        '}\n\n'

        '// ── Measurement mode ─────────────────────────────────────────────────\n'
        'function setMeasureMode(on) {\n'
        '  _measureMode = on;\n'
        '  if (!on) clearMeasure();\n'
        '  if (on && _coordMode) { _coordMode = false; clearCoordSystem(); }\n'
        '}\n\n'

        'function clearMeasure() {\n'
        '  for (var i=0;i<_mShapes.length;i++) { if (_viewer) _viewer.removeShape(_mShapes[i]); }\n'
        '  for (var i=0;i<_mLabels.length;i++) { if (_viewer) _viewer.removeLabel(_mLabels[i]); }\n'
        '  _mShapes=[]; _mLabels=[]; _mAtoms=[];\n'
        '  var info=document.getElementById("atom-info");\n'
        '  if (info) info.style.display="none";\n'
        '  if (_viewer) _viewer.render();\n'
        '}\n\n'

        '// ── Coordinate-origin mode ────────────────────────────────────────────\n'
        'function setCoordMode(on) {\n'
        '  _coordMode = on;\n'
        '  if (!on) clearCoordSystem();\n'
        '  if (on && _measureMode) { _measureMode = false; clearMeasure(); }\n'
        '}\n\n'

        'function clearCoordSystem() {\n'
        '  for (var i=0;i<_axisShapes.length;i++) { if (_viewer) _viewer.removeShape(_axisShapes[i]); }\n'
        '  for (var i=0;i<_axisLabels.length;i++) { if (_viewer) _viewer.removeLabel(_axisLabels[i]); }\n'
        '  _axisShapes=[]; _axisLabels=[]; _originAtom=null;\n'
        '  if (_viewer) _viewer.render();\n'
        '}\n\n'

        'function _drawAxes(ox,oy,oz,viewer) {\n'
        '  var len=2.0,r=0.07;\n'
        '  _axisShapes.push(viewer.addArrow({start:{x:ox,y:oy,z:oz},end:{x:ox+len,y:oy,z:oz},radius:r,color:"#FF4444",alpha:0.92,mid:1.0}));\n'
        '  _axisLabels.push(viewer.addLabel("X",{position:{x:ox+len+0.22,y:oy,z:oz},fontColor:"#FF4444",fontSize:13,backgroundColor:"rgba(0,0,0,0.7)",borderThickness:0,inFront:true}));\n'
        '  _axisShapes.push(viewer.addArrow({start:{x:ox,y:oy,z:oz},end:{x:ox,y:oy+len,z:oz},radius:r,color:"#4ADE80",alpha:0.92,mid:1.0}));\n'
        '  _axisLabels.push(viewer.addLabel("Y",{position:{x:ox,y:oy+len+0.22,z:oz},fontColor:"#4ADE80",fontSize:13,backgroundColor:"rgba(0,0,0,0.7)",borderThickness:0,inFront:true}));\n'
        '  _axisShapes.push(viewer.addArrow({start:{x:ox,y:oy,z:oz},end:{x:ox,y:oy,z:oz+len},radius:r,color:"#60A5FA",alpha:0.92,mid:1.0}));\n'
        '  _axisLabels.push(viewer.addLabel("Z",{position:{x:ox,y:oy,z:oz+len+0.22},fontColor:"#60A5FA",fontSize:13,backgroundColor:"rgba(0,0,0,0.7)",borderThickness:0,inFront:true}));\n'
        '  _axisShapes.push(viewer.addSphere({center:{x:ox,y:oy,z:oz},radius:0.22,color:"#FFFFFF",alpha:0.95}));\n'
        '  viewer.render();\n'
        '}\n\n'

        'function setOriginAtom(atom,viewer) {\n'
        '  var info=document.getElementById("atom-info");\n'
        '  if (_originAtom===null) {\n'
        '    _originAtom={x:atom.x,y:atom.y,z:atom.z,elem:atom.elem||"?",idx:atom.index||0};\n'
        '    _drawAxes(atom.x,atom.y,atom.z,viewer);\n'
        '    info.textContent=atom.elem+" (idx "+_originAtom.idx+") \u2192 Origin (0,0,0)  \u2022  click any atom for relative coords";\n'
        '    info.style.display="block";\n'
        '  } else if (atom.index===_originAtom.idx) {\n'
        '    clearCoordSystem();\n'
        '    info.textContent="Coord origin cleared  \u2014  click an atom to set new origin";\n'
        '    info.style.display="block";\n'
        '    setTimeout(function(){info.style.display="none";},2500);\n'
        '  } else {\n'
        '    var dx=atom.x-_originAtom.x,dy=atom.y-_originAtom.y,dz=atom.z-_originAtom.z;\n'
        '    var dist=Math.sqrt(dx*dx+dy*dy+dz*dz);\n'
        '    info.textContent=atom.elem+": ("+dx.toFixed(2)+", "+dy.toFixed(2)+", "+dz.toFixed(2)+")\u00c5  \u2022  r="+dist.toFixed(3)+"\u00c5";\n'
        '    info.style.display="block";\n'
        '    var vec=viewer.addArrow({start:{x:_originAtom.x,y:_originAtom.y,z:_originAtom.z},end:{x:atom.x,y:atom.y,z:atom.z},radius:0.05,color:"#FBBF24",alpha:0.8,mid:1.0});\n'
        '    _axisShapes.push(vec);\n'
        '    viewer.render();\n'
        '  }\n'
        '}\n\n'

        'function _onMeasureClick(atom, viewer) {\n'
        '  if (!atom) return;\n'
        '  // After 4 atoms (dihedral shown) start fresh on next click\n'
        '  if (_mAtoms.length >= 4) { clearMeasure(); }\n'
        '  _mAtoms.push({x:atom.x, y:atom.y, z:atom.z, elem:atom.elem||"?", idx:atom.index||0});\n'
        '  var palC=["#00E5A0","#FF8C00","#CC66FF","#60A5FA"];\n'
        '  var col=palC[(_mAtoms.length-1)%4];\n'
        '  var sh=viewer.addSphere({center:{x:atom.x,y:atom.y,z:atom.z},radius:0.35,color:col,alpha:0.85});\n'
        '  _mShapes.push(sh);\n'
        '  var info=document.getElementById("atom-info");\n'
        '  if (_mAtoms.length===1) {\n'
        '    info.textContent=atom.elem+" selected \\u2014 click 2nd atom to measure distance";\n'
        '    info.style.display="block";\n'
        '  } else if (_mAtoms.length===2) {\n'
        '    var a=_mAtoms[0],b=_mAtoms[1];\n'
        '    var dx=a.x-b.x,dy=a.y-b.y,dz=a.z-b.z;\n'
        '    var dist=Math.sqrt(dx*dx+dy*dy+dz*dz);\n'
        '    var cyl=viewer.addArrow({start:{x:a.x,y:a.y,z:a.z},end:{x:b.x,y:b.y,z:b.z},radius:0.06,color:"#00E5A0",alpha:0.75,mid:1.0});\n'
        '    _mShapes.push(cyl);\n'
        '    var mid={x:(a.x+b.x)/2,y:(a.y+b.y)/2+0.3,z:(a.z+b.z)/2};\n'
        '    var lbl=viewer.addLabel(dist.toFixed(2)+"\\u00c5",{position:mid,backgroundColor:"rgba(0,10,20,0.9)",fontColor:"#00E5A0",fontSize:12});\n'
        '    _mLabels.push(lbl);\n'
        '    info.textContent=a.elem+"-"+b.elem+": "+dist.toFixed(3)+"\\u00c5  (click 3rd for angle, 4th for dihedral)";\n'
        '    info.style.display="block";\n'
        '    if (_bridge) _bridge.measurementReady("distance", dist, JSON.stringify([a.idx,b.idx]));\n'
        '  } else if (_mAtoms.length===3) {\n'
        '    var a=_mAtoms[0],b=_mAtoms[1],c=_mAtoms[2];\n'
        '    var bax=a.x-b.x,bay=a.y-b.y,baz=a.z-b.z;\n'
        '    var bcx=c.x-b.x,bcy=c.y-b.y,bcz=c.z-b.z;\n'
        '    var la=Math.sqrt(bax*bax+bay*bay+baz*baz);\n'
        '    var lc=Math.sqrt(bcx*bcx+bcy*bcy+bcz*bcz);\n'
        '    var angle=Math.acos(Math.max(-1,Math.min(1,(bax*bcx+bay*bcy+baz*bcz)/(la*lc))))*180/Math.PI;\n'
        '    var cyl2=viewer.addArrow({start:{x:b.x,y:b.y,z:b.z},end:{x:c.x,y:c.y,z:c.z},radius:0.06,color:"#FF8C00",alpha:0.75,mid:1.0});\n'
        '    _mShapes.push(cyl2);\n'
        '    var lbl2=viewer.addLabel(angle.toFixed(1)+"\\u00b0",{position:{x:b.x,y:b.y+0.5,z:b.z},backgroundColor:"rgba(0,10,20,0.9)",fontColor:"#FF8C00",fontSize:12});\n'
        '    _mLabels.push(lbl2);\n'
        '    info.textContent=a.elem+"-"+b.elem+"-"+c.elem+": "+angle.toFixed(1)+"\\u00b0  (click 4th for dihedral)";\n'
        '    info.style.display="block";\n'
        '    if (_bridge) _bridge.measurementReady("angle", angle, JSON.stringify([a.idx,b.idx,c.idx]));\n'
        '  } else if (_mAtoms.length===4) {\n'
        '    var a=_mAtoms[0],b=_mAtoms[1],c=_mAtoms[2],d=_mAtoms[3];\n'
        '    // Dihedral: angle between planes (a,b,c) and (b,c,d)\n'
        '    var b1x=b.x-a.x,b1y=b.y-a.y,b1z=b.z-a.z;\n'
        '    var b2x=c.x-b.x,b2y=c.y-b.y,b2z=c.z-b.z;\n'
        '    var b3x=d.x-c.x,b3y=d.y-c.y,b3z=d.z-c.z;\n'
        '    // n1 = b1 x b2, n2 = b2 x b3\n'
        '    var n1x=b1y*b2z-b1z*b2y, n1y=b1z*b2x-b1x*b2z, n1z=b1x*b2y-b1y*b2x;\n'
        '    var n2x=b2y*b3z-b2z*b3y, n2y=b2z*b3x-b2x*b3z, n2z=b2x*b3y-b2y*b3x;\n'
        '    var ln1=Math.sqrt(n1x*n1x+n1y*n1y+n1z*n1z)||1;\n'
        '    var ln2=Math.sqrt(n2x*n2x+n2y*n2y+n2z*n2z)||1;\n'
        '    var cosD=(n1x*n2x+n1y*n2y+n1z*n2z)/(ln1*ln2);\n'
        '    var dihedral=Math.acos(Math.max(-1,Math.min(1,cosD)))*180/Math.PI;\n'
        '    // Sign from cross product\n'
        '    var m1x=n1y*b2z-n1z*b2y, m1y=n1z*b2x-n1x*b2z, m1z=n1x*b2y-n1y*b2x;\n'
        '    var lm=Math.sqrt(m1x*m1x+m1y*m1y+m1z*m1z)||1;\n'
        '    var sinD=(m1x*n2x+m1y*n2y+m1z*n2z)/(lm*ln2);\n'
        '    dihedral=Math.atan2(sinD,cosD)*180/Math.PI;\n'
        '    var cyl3=viewer.addArrow({start:{x:c.x,y:c.y,z:c.z},end:{x:d.x,y:d.y,z:d.z},radius:0.06,color:"#CC66FF",alpha:0.75,mid:1.0});\n'
        '    _mShapes.push(cyl3);\n'
        '    var lbl3=viewer.addLabel(dihedral.toFixed(1)+"\\u00b0",{position:{x:(b.x+c.x)/2,y:(b.y+c.y)/2+0.7,z:(b.z+c.z)/2},backgroundColor:"rgba(0,10,20,0.9)",fontColor:"#CC66FF",fontSize:12});\n'
        '    _mLabels.push(lbl3);\n'
        '    info.textContent=a.elem+"-"+b.elem+"-"+c.elem+"-"+d.elem+": "+dihedral.toFixed(1)+"\\u00b0 dihedral";\n'
        '    info.style.display="block";\n'
        '    if (_bridge) _bridge.measurementReady("dihedral", dihedral, JSON.stringify([a.idx,b.idx,c.idx,d.idx]));\n'
        '  }\n'
        '  viewer.render();\n'
        '}\n\n'

        'function setBackground(hex) {\n'
        '  _bgColor = hex;\n'
        '  if (_viewer) { _viewer.setBackgroundColor(hex); _viewer.render(); }\n'
        '  document.body.style.background = hex;\n'
        '  var grid = document.getElementById("bg-grid");\n'
        '  if (grid) grid.style.display = (hex === "0x080D1A" || hex === "#080D1A") ? "block" : "none";\n'
        '}\n\n'

        'function resetView() {\n'
        '  if (!_viewer) return;\n'
        '  if (_clickShape) { _viewer.removeShape(_clickShape); _clickShape = null; }\n'
        '  document.getElementById("atom-info").style.display = "none";\n'
        '  _viewer.zoomTo(); _viewer.render();\n'
        '}\n\n'

        '// ── Correlation highlights with pulsing glow ────────────────────────\n'
        'var _corrShapes = [];\n'
        'var _corrLabels = [];\n'
        'var _corrAtoms  = [];  // [{x,y,z}] for pulse animation\n'
        'var _corrColor  = "#EC4899";\n'
        'var _pulseTimer = null;\n'
        'var _pulsePhase = 0;\n\n'

        'function highlightAtoms(indices, color, labelText) {\n'
        '  clearHighlight();\n'
        '  if (!_viewer || !_models.length || !indices || !indices.length) return;\n'
        '  var atoms = _models[0].selectedAtoms({});\n'
        '  if (!atoms) return;\n'
        '  _corrColor = color || "#EC4899";\n'
        '  _corrAtoms = [];\n'
        '  for (var i = 0; i < indices.length; i++) {\n'
        '    var idx = indices[i];\n'
        '    if (idx < 0 || idx >= atoms.length) continue;\n'
        '    var a = atoms[idx];\n'
        '    if (!a) continue;\n'
        '    _corrAtoms.push({x: a.x, y: a.y, z: a.z});\n'
        '    // Inner solid sphere\n'
        '    var sh = _viewer.addSphere({\n'
        '      center: {x: a.x, y: a.y, z: a.z},\n'
        '      radius: 0.45, color: _corrColor, alpha: 0.7\n'
        '    });\n'
        '    _corrShapes.push(sh);\n'
        '    // Outer glow ring\n'
        '    var glow = _viewer.addSphere({\n'
        '      center: {x: a.x, y: a.y, z: a.z},\n'
        '      radius: 0.75, color: _corrColor, alpha: 0.15, wireframe: true\n'
        '    });\n'
        '    _corrShapes.push(glow);\n'
        '    if (labelText) {\n'
        '      var lbl = _viewer.addLabel(labelText, {\n'
        '        position: {x: a.x, y: a.y + 1.4, z: a.z},\n'
        '        backgroundColor: "rgba(8,13,26,0.88)",\n'
        '        fontColor: _corrColor,\n'
        '        fontSize: 11, borderThickness: 0.5,\n'
        '        borderColor: _corrColor, inFront: true,\n'
        '        showBackground: true\n'
        '      });\n'
        '      _corrLabels.push(lbl);\n'
        '    }\n'
        '  }\n'
        '  _viewer.render();\n'
        '  // Start pulse animation\n'
        '  _pulsePhase = 0;\n'
        '  if (_pulseTimer) clearInterval(_pulseTimer);\n'
        '  _pulseTimer = setInterval(_pulseStep, 60);\n'
        '  // Auto-stop after 3 seconds\n'
        '  setTimeout(function() {\n'
        '    if (_pulseTimer) { clearInterval(_pulseTimer); _pulseTimer = null; }\n'
        '  }, 3000);\n'
        '}\n\n'

        'function _pulseStep() {\n'
        '  if (!_viewer || _corrAtoms.length === 0) return;\n'
        '  _pulsePhase += 0.15;\n'
        '  var scale = 0.75 + 0.2 * Math.sin(_pulsePhase);\n'
        '  var alpha = 0.12 + 0.08 * Math.sin(_pulsePhase);\n'
        '  // Update outer glow spheres (every other shape starting at index 1)\n'
        '  for (var i = 1; i < _corrShapes.length; i += 2) {\n'
        '    try {\n'
        '      _viewer.removeShape(_corrShapes[i]);\n'
        '      var pos = _corrAtoms[Math.floor(i/2)];\n'
        '      if (pos) {\n'
        '        _corrShapes[i] = _viewer.addSphere({\n'
        '          center: {x: pos.x, y: pos.y, z: pos.z},\n'
        '          radius: scale, color: _corrColor, alpha: alpha, wireframe: true\n'
        '        });\n'
        '      }\n'
        '    } catch(e) {}\n'
        '  }\n'
        '  _viewer.render();\n'
        '}\n\n'

        'function clearHighlight() {\n'
        '  if (_pulseTimer) { clearInterval(_pulseTimer); _pulseTimer = null; }\n'
        '  if (!_viewer) return;\n'
        '  for (var i = 0; i < _corrShapes.length; i++) { _viewer.removeShape(_corrShapes[i]); }\n'
        '  for (var i = 0; i < _corrLabels.length; i++) { _viewer.removeLabel(_corrLabels[i]); }\n'
        '  _corrShapes = []; _corrLabels = []; _corrAtoms = [];\n'
        '  _viewer.render();\n'
        '}\n\n'

        '// Highlight bonds between atom pairs (for IR correlation)\n'
        'function highlightBonds(bondPairs, color) {\n'
        '  clearHighlight();\n'
        '  if (!_viewer || !_models.length || !bondPairs || !bondPairs.length) return;\n'
        '  var atoms = _models[0].selectedAtoms({});\n'
        '  if (!atoms) return;\n'
        '  var c = color || "#F59E0B";\n'
        '  _corrColor = c;\n'
        '  _corrAtoms = [];\n'
        '  for (var i = 0; i < bondPairs.length; i++) {\n'
        '    var a1 = bondPairs[i][0], a2 = bondPairs[i][1];\n'
        '    if (a1 < 0 || a1 >= atoms.length || a2 < 0 || a2 >= atoms.length) continue;\n'
        '    var p1 = atoms[a1], p2 = atoms[a2];\n'
        '    if (!p1 || !p2) continue;\n'
        '    // Thick glowing cylinder for the bond\n'
        '    var cyl = _viewer.addCylinder({\n'
        '      start: {x: p1.x, y: p1.y, z: p1.z},\n'
        '      end:   {x: p2.x, y: p2.y, z: p2.z},\n'
        '      radius: 0.14, color: c, alpha: 0.8,\n'
        '      fromCap: 1, toCap: 1\n'
        '    });\n'
        '    _corrShapes.push(cyl);\n'
        '    // Glow around each atom\n'
        '    var s1 = _viewer.addSphere({center:{x:p1.x,y:p1.y,z:p1.z},radius:0.4,color:c,alpha:0.5});\n'
        '    var s2 = _viewer.addSphere({center:{x:p2.x,y:p2.y,z:p2.z},radius:0.4,color:c,alpha:0.5});\n'
        '    _corrShapes.push(s1); _corrShapes.push(s2);\n'
        '    _corrAtoms.push({x:p1.x,y:p1.y,z:p1.z});\n'
        '    _corrAtoms.push({x:p2.x,y:p2.y,z:p2.z});\n'
        '  }\n'
        '  _viewer.render();\n'
        '}\n\n'

        'function rotateToAtom(idx) {\n'
        '  if (!_viewer || !_models.length) return;\n'
        '  var atoms = _models[0].selectedAtoms({});\n'
        '  if (!atoms || idx < 0 || idx >= atoms.length) return;\n'
        '  var a = atoms[idx];\n'
        '  if (a) _viewer.center({x: a.x, y: a.y, z: a.z}, 800);\n'
        '}\n\n'

        'function clearViewer() {\n'
        '  if (_viewer) {\n'
        '    _viewer.removeAllModels(); _viewer.removeAllShapes();\n'
        '    for (var i=0;i<_atomLabels.length;i++) { _viewer.removeLabel(_atomLabels[i]); }\n'
        '    _atomLabels = [];\n'
        '    for (var i=0;i<_axisLabels.length;i++) { _viewer.removeLabel(_axisLabels[i]); }\n'
        '    for (var i=0;i<_mLabels.length;i++) { _viewer.removeLabel(_mLabels[i]); }\n'
        '    for (var i=0;i<_corrShapes.length;i++) { _viewer.removeShape(_corrShapes[i]); }\n'
        '    for (var i=0;i<_corrLabels.length;i++) { _viewer.removeLabel(_corrLabels[i]); }\n'
        '    _axisShapes=[]; _axisLabels=[]; _originAtom=null;\n'
        '    _mShapes=[]; _mLabels=[]; _mAtoms=[];\n'
        '    _corrShapes=[]; _corrLabels=[];\n'
        '    _viewer.render();\n'
        '  }\n'
        '  _models = []; _clickShape = null;\n'
        '  document.getElementById("loading").style.display = "block";\n'
        '  document.getElementById("loading").textContent = "No molecule loaded";\n'
        '  document.getElementById("atom-info").style.display = "none";\n'
        '}\n\n'

        '// ── Electrostatic Surface Mode ──────────────────────────────────────\n'
        'var _surfaceObj = null;\n'
        'function loadSurface(sdfString, chargesJson) {\n'
        '  if (!_viewer) return;\n'
        '  _viewer.removeAllModels(); _viewer.removeAllShapes();\n'
        '  _viewer.removeAllSurfaces();\n'
        '  _models = [];\n'
        '  var model = _viewer.addModel(sdfString, "sdf");\n'
        '  _models.push(model);\n'
        '  var cs = {colorscheme: {prop: "elem", map: ELEMENT_COLORS}};\n'
        '  _viewer.setStyle({}, {stick: {colorscheme: cs.colorscheme, radius: 0.08}});\n'
        '  // Apply partial charges as atom property\n'
        '  var charges = {};\n'
        '  try { charges = JSON.parse(chargesJson); } catch(e) {}\n'
        '  var atoms = model.selectedAtoms({});\n'
        '  if (atoms) {\n'
        '    for (var i = 0; i < atoms.length; i++) {\n'
        '      var c = charges[String(i)];\n'
        '      if (c !== undefined) atoms[i].properties = {partialCharge: c};\n'
        '    }\n'
        '  }\n'
        '  _surfaceObj = _viewer.addSurface($3Dmol.SurfaceType.VDW, {\n'
        '    opacity: 0.72,\n'
        '    colorscheme: {\n'
        '      gradient: "rwb",\n'
        '      min: -0.3, max: 0.3,\n'
        '      prop: "partialCharge"\n'
        '    }\n'
        '  });\n'
        '  _registerClickHandlers();\n'
        '  _viewer.zoomTo();\n'
        '  _viewer.render();\n'
        '}\n\n'

        'function clearSurface() {\n'
        '  if (!_viewer) return;\n'
        '  _viewer.removeAllSurfaces();\n'
        '  _surfaceObj = null;\n'
        '  _viewer.render();\n'
        '}\n\n'

        '// ── Screenshot ──────────────────────────────────────────────────────\n'
        'function takeScreenshot() {\n'
        '  if (!_viewer) return;\n'
        '  var uri = _viewer.pngURI();\n'
        '  if (_bridge && uri) {\n'
        '    // Strip data:image/png;base64, prefix\n'
        '    var b64 = uri.replace(/^data:image\\/png;base64,/, "");\n'
        '    _bridge.screenshotReady(b64);\n'
        '  }\n'
        '}\n\n'

        '// ── Scaffold Core Highlight ─────────────────────────────────────────\n'
        'var _scaffoldActive = false;\n'
        'function highlightScaffold(atomIndices, on) {\n'
        '  _scaffoldActive = on;\n'
        '  if (!_viewer || !_models.length) return;\n'
        '  if (!on) { applyStyle(_style); return; }\n'
        '  var cs = {colorscheme: {prop: "elem", map: ELEMENT_COLORS}};\n'
        '  // Mute all atoms\n'
        '  _viewer.setStyle({}, {stick: {color: "#475569", radius: 0.10}});\n'
        '  if (!_showH) _viewer.setStyle({elem: "H"}, {hidden: true});\n'
        '  // Highlight scaffold atoms\n'
        '  if (atomIndices && atomIndices.length) {\n'
        '    for (var i = 0; i < atomIndices.length; i++) {\n'
        '      _viewer.setStyle({index: atomIndices[i]}, {stick: {colorscheme: cs.colorscheme, radius: 0.20}});\n'
        '    }\n'
        '  }\n'
        '  _viewer.render();\n'
        '}\n\n'

        '// ── Functional Group Highlights ─────────────────────────────────────\n'
        'var _fgShapes = [];\n'
        'function highlightFunctionalGroup(groupName, indices, color, on) {\n'
        '  if (!_viewer || !_models.length) return;\n'
        '  if (!on) {\n'
        '    // Remove shapes for this group\n'
        '    for (var i = 0; i < _fgShapes.length; i++) {\n'
        '      try { _viewer.removeShape(_fgShapes[i]); } catch(e) {}\n'
        '    }\n'
        '    _fgShapes = [];\n'
        '    applyStyle(_style);\n'
        '    _viewer.render();\n'
        '    return;\n'
        '  }\n'
        '  var atoms = _models[0].selectedAtoms({});\n'
        '  if (!atoms) return;\n'
        '  for (var i = 0; i < indices.length; i++) {\n'
        '    var idx = indices[i];\n'
        '    if (idx < 0 || idx >= atoms.length) continue;\n'
        '    var a = atoms[idx];\n'
        '    if (!a) continue;\n'
        '    var sh = _viewer.addSphere({\n'
        '      center: {x: a.x, y: a.y, z: a.z},\n'
        '      radius: 0.50, color: color, alpha: 0.45\n'
        '    });\n'
        '    _fgShapes.push(sh);\n'
        '  }\n'
        '  _viewer.render();\n'
        '}\n\n'

        '// ── HBD / HBA Highlights ────────────────────────────────────────────\n'
        'var _hbShapes = [];\n'
        'var _hbTimer = null;\n'
        'var _hbPhase = 0;\n'
        'function highlightHBonds(hbdIndices, hbaIndices, on) {\n'
        '  // Clear previous\n'
        '  if (_hbTimer) { clearInterval(_hbTimer); _hbTimer = null; }\n'
        '  for (var i = 0; i < _hbShapes.length; i++) {\n'
        '    try { if (_viewer) _viewer.removeShape(_hbShapes[i]); } catch(e) {}\n'
        '  }\n'
        '  _hbShapes = [];\n'
        '  if (!on || !_viewer || !_models.length) { if (_viewer) _viewer.render(); return; }\n'
        '  var atoms = _models[0].selectedAtoms({});\n'
        '  if (!atoms) return;\n'
        '  function addSpheres(idxArr, col) {\n'
        '    for (var i = 0; i < idxArr.length; i++) {\n'
        '      var a = atoms[idxArr[i]];\n'
        '      if (!a) continue;\n'
        '      var sh = _viewer.addSphere({center:{x:a.x,y:a.y,z:a.z}, radius:0.52, color:col, alpha:0.4});\n'
        '      _hbShapes.push(sh);\n'
        '    }\n'
        '  }\n'
        '  addSpheres(hbdIndices, "#3B82F6");\n'
        '  addSpheres(hbaIndices, "#EF4444");\n'
        '  _viewer.render();\n'
        '  // Pulse\n'
        '  _hbPhase = 0;\n'
        '  _hbTimer = setInterval(function() {\n'
        '    _hbPhase += 0.12;\n'
        '    var alpha = 0.2 + 0.3 * Math.abs(Math.sin(_hbPhase));\n'
        '    // Cannot update existing shape opacity in 3Dmol — skip pulse rebuild for perf\n'
        '  }, 800);\n'
        '}\n\n'

        '// ── NMR Assignment Labels on 3D Viewer ──────────────────────────────\n'
        'var _nmrLabels = [];\n'
        'function showNMRLabels(atomLabelData, on) {\n'
        '  // Clear existing\n'
        '  for (var i = 0; i < _nmrLabels.length; i++) {\n'
        '    try { if (_viewer) _viewer.removeLabel(_nmrLabels[i]); } catch(e) {}\n'
        '  }\n'
        '  _nmrLabels = [];\n'
        '  if (!on || !_viewer || !_models.length) { if (_viewer) _viewer.render(); return; }\n'
        '  var atoms = _models[0].selectedAtoms({});\n'
        '  if (!atoms) return;\n'
        '  for (var i = 0; i < atomLabelData.length; i++) {\n'
        '    var d = atomLabelData[i];\n'
        '    var idx = d.index;\n'
        '    if (idx < 0 || idx >= atoms.length) continue;\n'
        '    var a = atoms[idx];\n'
        '    if (!a) continue;\n'
        '    var text = "";\n'
        '    var color = "#06B6D4";\n'
        '    if (d.h1) { text = "\\u03B4 " + d.h1; color = "#06B6D4"; }\n'
        '    else if (d.c13) { text = "\\u03B4 " + d.c13; color = "#F59E0B"; }\n'
        '    if (!text) continue;\n'
        '    var lbl = _viewer.addLabel(text, {\n'
        '      position: {x: a.x, y: a.y + 1.2, z: a.z},\n'
        '      backgroundColor: "rgba(15,22,35,0.85)",\n'
        '      fontColor: color,\n'
        '      fontSize: 11, borderThickness: 1,\n'
        '      borderColor: "#8B5CF6", inFront: true,\n'
        '      showBackground: true\n'
        '    });\n'
        '    _nmrLabels.push(lbl);\n'
        '  }\n'
        '  _viewer.render();\n'
        '}\n'
    )

    return html_head + js + '</script>\n</body>\n</html>'


# ══════════════════════════════════════════════════════════════════════════════
#  MolecularViewer widget
# ══════════════════════════════════════════════════════════════════════════════

class MolecularViewer(QWidget):
    """
    3D molecular structure viewer.

    Falls back to a styled placeholder if PyQtWebEngine is not installed.

    Signals
    -------
    atom_clicked(int)      Index of the clicked atom
    conformer_loading()    Conformer generation has started
    conformer_ready()      Conformers are loaded in the viewer
    """

    atom_clicked = pyqtSignal(int)
    conformer_loading = pyqtSignal()
    conformer_ready = pyqtSignal()
    measurement_signal = pyqtSignal(str, float, str)  # type, value, atomsJson

    def __init__(self, parent=None):
        super().__init__(parent)
        self._conformers: list[tuple[str, float]] = []  # (sdf_block, energy)
        self._current_idx: int = 0
        self._worker: Optional[_ConformerWorker] = None
        self._page_ready = False
        self._pending_js: list[str] = []

        # Feature data (set externally after analysis)
        self._scaffold_atoms: list[int] = []
        self._hbd_indices: list[int] = []
        self._hba_indices: list[int] = []
        self._nmr_label_data: list[dict] = []
        self._surface_charges: dict[int, float] = {}
        self._current_smiles: str = ""

        if _HAS_WEBENGINE:
            self._build_ui()
        else:
            self._build_fallback_ui()

    # ── Fallback (no PyQtWebEngine) ───────────────────────────────────────────

    def _build_fallback_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(
            "3D Viewer unavailable\n\nInstall PyQtWebEngine:\n"
            "pip install PyQtWebEngine"
        )
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                border: 2px dashed {Colors.BORDER};
                border-radius: 8px;
                padding: 20px;
                font-family: '{FONT_FAMILY}';
                font-size: 13px;
            }}
        """)
        layout.addWidget(label)

    # ── Full UI (with PyQtWebEngine) ──────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_toolbar(layout)
        self._build_web_view(layout)

    def _build_toolbar(self, parent_layout):
        toolbar = QWidget()
        toolbar.setFixedHeight(36)
        toolbar.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(6, 2, 6, 2)
        tb_layout.setSpacing(4)

        btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{
                background: {Colors.BG_SECONDARY};
                border-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton[active="true"] {{
                color: {Colors.ACCENT_PINK};
                border-color: {Colors.ACCENT_PINK};
            }}
        """

        # ── Conformer carousel ────────────────────────────────────────────────
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedWidth(26)
        self._prev_btn.setToolTip("Previous conformer")
        self._prev_btn.setEnabled(False)
        self._prev_btn.clicked.connect(self._prev_conformer)
        self._prev_btn.setStyleSheet(btn_style)
        tb_layout.addWidget(self._prev_btn)

        self._conf_label = QLabel("No conformer")
        self._conf_label.setFixedWidth(100)
        self._conf_label.setAlignment(Qt.AlignCenter)
        self._conf_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;"
        )
        tb_layout.addWidget(self._conf_label)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedWidth(26)
        self._next_btn.setToolTip("Next conformer")
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._next_conformer)
        self._next_btn.setStyleSheet(btn_style)
        tb_layout.addWidget(self._next_btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {Colors.BORDER};")
        tb_layout.addWidget(sep)

        # ── Style buttons ─────────────────────────────────────────────────────
        self._style_group = QButtonGroup(self)
        self._style_group.setExclusive(True)
        for label, cmd, tooltip in [
            ("Stick", "stick", "Stick model"),
            ("Ball+Stick", "ballstick", "Ball and stick model"),
            ("Spacefill", "spacefill", "Space-filling model"),
            ("Wire", "wire", "Wireframe model"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, c=cmd, b=btn: self._set_style(c, b))
            self._style_group.addButton(btn)
            tb_layout.addWidget(btn)
            if cmd == "stick":
                btn.setChecked(True)
                btn.setProperty("active", "true")

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(f"color: {Colors.BORDER};")
        tb_layout.addWidget(sep2)

        # ── Heteroatom highlight ──────────────────────────────────────────────
        self._hetero_cb = QCheckBox("Heteroatoms")
        self._hetero_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                font-family: '{FONT_FAMILY}';
            }}
            QCheckBox::indicator:checked {{
                background: {Colors.ACCENT_CYAN};
            }}
        """)
        self._hetero_cb.stateChanged.connect(self._toggle_heteroatoms)
        tb_layout.addWidget(self._hetero_cb)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.VLine)
        sep3.setStyleSheet(f"color: {Colors.BORDER};")
        tb_layout.addWidget(sep3)

        # ── Surface button (5th style) ───────────────────────────────────────
        self._surface_btn = QPushButton("Surface")
        self._surface_btn.setCheckable(True)
        self._surface_btn.setToolTip(
            "Electrostatic potential surface\n"
            "Red = electron rich\nBlue = electron poor\n"
            "Requires 3D conformer"
        )
        self._surface_btn.setStyleSheet(btn_style)
        self._surface_btn.clicked.connect(self._toggle_surface)
        self._style_group.addButton(self._surface_btn)
        tb_layout.addWidget(self._surface_btn)

        sep_s2 = QFrame()
        sep_s2.setFrameShape(QFrame.VLine)
        sep_s2.setStyleSheet(f"color: {Colors.BORDER};")
        tb_layout.addWidget(sep_s2)

        # ── H toggle button ──────────────────────────────────────────────
        self._h_btn = QPushButton("H")
        self._h_btn.setCheckable(True)
        self._h_btn.setToolTip("Toggle hydrogen visibility")
        self._h_btn.setStyleSheet(btn_style)
        self._h_btn.setChecked(True)
        self._h_btn.setProperty("active", "true")
        self._h_btn.clicked.connect(self._toggle_hydrogens)
        tb_layout.addWidget(self._h_btn)

        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.VLine)
        sep_h.setStyleSheet(f"color: {Colors.BORDER};")
        tb_layout.addWidget(sep_h)

        # ── Screenshot button ─────────────────────────────────────────────
        self._screenshot_btn = QPushButton("Screenshot")
        self._screenshot_btn.setToolTip("Save 3D viewer screenshot as PNG")
        self._screenshot_btn.setStyleSheet(btn_style)
        self._screenshot_btn.clicked.connect(self._take_screenshot_dialog)
        tb_layout.addWidget(self._screenshot_btn)

        # ── Reset button ──────────────────────────────────────────────────
        reset_btn = QPushButton("Reset")
        reset_btn.setToolTip("Reset camera to default view")
        reset_btn.setStyleSheet(btn_style)
        reset_btn.clicked.connect(lambda: self._run_js("resetView()"))
        tb_layout.addWidget(reset_btn)

        tb_layout.addStretch()
        parent_layout.addWidget(toolbar)

        # ── Secondary toolbar: Labels + Measurement ───────────────────────────
        tb2 = QWidget()
        tb2.setFixedHeight(30)
        tb2.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)
        tb2_layout = QHBoxLayout(tb2)
        tb2_layout.setContentsMargins(8, 1, 8, 1)
        tb2_layout.setSpacing(8)

        cb_style = f"""
            QCheckBox {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                font-family: '{FONT_FAMILY}';
            }}
            QCheckBox:hover {{ color: {Colors.TEXT_PRIMARY}; }}
            QCheckBox::indicator {{
                width: 13px; height: 13px;
                border: 1px solid {Colors.BORDER};
                border-radius: 2px;
                background: {Colors.BG_ELEVATED};
            }}
            QCheckBox::indicator:checked {{
                background: {Colors.ACCENT_BLUE};
                border-color: {Colors.ACCENT_BLUE};
            }}
        """

        self._labels_cb = QCheckBox("Atom Labels")
        self._labels_cb.setToolTip("Show element symbol on each heavy atom")
        self._labels_cb.setStyleSheet(cb_style)
        self._labels_cb.stateChanged.connect(
            lambda s: self._run_js("toggleLabels(true)" if s == Qt.Checked else "toggleLabels(false)")
        )
        tb2_layout.addWidget(self._labels_cb)

        sep_tb2 = QFrame()
        sep_tb2.setFrameShape(QFrame.VLine)
        sep_tb2.setStyleSheet(f"color: {Colors.BORDER};")
        tb2_layout.addWidget(sep_tb2)

        self._measure_btn = QPushButton("Measure")
        self._measure_btn.setCheckable(True)
        self._measure_btn.setToolTip(
            "Measure mode:\n"
            "  2 atoms = distance\n"
            "  3 atoms = bond angle\n"
            "  4 atoms = dihedral angle"
        )
        self._measure_btn.setStyleSheet(btn_style)
        self._measure_btn.clicked.connect(self._toggle_measure)
        tb2_layout.addWidget(self._measure_btn)

        sep_coord = QFrame()
        sep_coord.setFrameShape(QFrame.VLine)
        sep_coord.setStyleSheet(f"color: {Colors.BORDER};")
        tb2_layout.addWidget(sep_coord)

        self._coord_btn = QPushButton("📍  Coord Origin")
        self._coord_btn.setCheckable(True)
        self._coord_btn.setToolTip(
            "Coord Origin mode:\n"
            "  1st click → set atom as XYZ origin, draws 3D axes\n"
            "  Next clicks → show relative (x, y, z) coords and distance\n"
            "  Click origin atom again → clear axes"
        )
        self._coord_btn.setStyleSheet(btn_style)
        self._coord_btn.clicked.connect(self._toggle_coord_mode)
        tb2_layout.addWidget(self._coord_btn)

        tb2_layout.addStretch()
        parent_layout.addWidget(tb2)

        # ── Third toolbar row: Highlights + Background ────────────────────
        tb3 = QWidget()
        tb3.setFixedHeight(28)
        tb3.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)
        tb3_layout = QHBoxLayout(tb3)
        tb3_layout.setContentsMargins(8, 1, 8, 1)
        tb3_layout.setSpacing(8)

        self._scaffold_cb = QCheckBox("Scaffold")
        self._scaffold_cb.setToolTip("Highlight Murcko scaffold core")
        self._scaffold_cb.setStyleSheet(cb_style)
        self._scaffold_cb.setEnabled(False)
        self._scaffold_cb.stateChanged.connect(self._toggle_scaffold)
        tb3_layout.addWidget(self._scaffold_cb)

        self._hbd_hba_cb = QCheckBox("HBD/HBA")
        self._hbd_hba_cb.setToolTip("Highlight H-bond donors (blue) and acceptors (red)")
        self._hbd_hba_cb.setStyleSheet(cb_style)
        self._hbd_hba_cb.setEnabled(False)
        self._hbd_hba_cb.stateChanged.connect(self._toggle_hbd_hba)
        tb3_layout.addWidget(self._hbd_hba_cb)

        self._nmr_labels_cb = QCheckBox("NMR Labels")
        self._nmr_labels_cb.setToolTip("Show NMR chemical shift labels on atoms")
        self._nmr_labels_cb.setStyleSheet(cb_style)
        self._nmr_labels_cb.setEnabled(False)
        self._nmr_labels_cb.stateChanged.connect(self._toggle_nmr_labels)
        tb3_layout.addWidget(self._nmr_labels_cb)

        sep_bg = QFrame()
        sep_bg.setFrameShape(QFrame.VLine)
        sep_bg.setStyleSheet(f"color: {Colors.BORDER};")
        tb3_layout.addWidget(sep_bg)

        # Background radio buttons
        bg_label = QLabel("BG:")
        bg_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        tb3_layout.addWidget(bg_label)

        rb_style = f"""
            QRadioButton {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 11px;
                font-family: '{FONT_FAMILY}';
            }}
            QRadioButton::indicator {{
                width: 11px; height: 11px;
            }}
        """
        self._bg_black = QRadioButton("Black")
        self._bg_black.setStyleSheet(rb_style)
        self._bg_black.clicked.connect(lambda: self._set_background("#000000"))
        tb3_layout.addWidget(self._bg_black)

        self._bg_dark = QRadioButton("Dark")
        self._bg_dark.setStyleSheet(rb_style)
        self._bg_dark.setChecked(True)
        self._bg_dark.clicked.connect(lambda: self._set_background("#080D1A"))
        tb3_layout.addWidget(self._bg_dark)

        self._bg_white = QRadioButton("White")
        self._bg_white.setStyleSheet(rb_style)
        self._bg_white.clicked.connect(lambda: self._set_background("#FFFFFF"))
        tb3_layout.addWidget(self._bg_white)

        tb3_layout.addStretch()
        parent_layout.addWidget(tb3)

    def _build_web_view(self, parent_layout):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings

        use_local = _3DMOL_LOCAL.exists()
        html = _build_viewer_html(use_local)

        self._web = QWebEngineView()
        self._web.setMinimumSize(100, 80)
        self._web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Allow file:// pages to load remote (CDN) scripts
        settings = self._web.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

        # Set up QWebChannel
        self._bridge = AtomClickBridge()
        self._bridge.atom_clicked_signal.connect(self.atom_clicked)
        self._bridge.viewer_ready_signal.connect(self._on_viewer_js_ready)
        self._bridge.screenshot_ready_signal.connect(self._on_screenshot_ready)
        self._bridge.measurement_ready_signal.connect(self._on_measurement_ready)

        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._bridge)
        self._web.page().setWebChannel(self._channel)

        self._web.page().loadFinished.connect(self._on_page_load_finished)

        # Base URL = viewer package directory so relative "3dmol-min.js" resolves
        base_url = QUrl.fromLocalFile(str(_VIEWER_DIR) + "/")
        self._web.setHtml(html, base_url)

        parent_layout.addWidget(self._web)

        # Trigger background download of 3dmol-min.js if missing
        if not use_local:
            QTimer.singleShot(2000, self._try_download_3dmol)

    # ── JS communication ──────────────────────────────────────────────────────

    def _run_js(self, js: str):
        """Run JavaScript, queuing if the viewer isn't ready yet."""
        if not _HAS_WEBENGINE:
            return
        if self._page_ready:
            self._web.page().runJavaScript(js)
        else:
            self._pending_js.append(js)

    def _on_page_load_finished(self, ok: bool):
        """HTML page loaded — start polling as fallback in case bridge never fires."""
        if ok:
            self._poll_count = 0
            QTimer.singleShot(800, self._poll_viewer_ready)

    def _poll_viewer_ready(self):
        """Poll JS until _viewer exists, then mark page ready (bridge-independent fallback)."""
        if self._page_ready:
            return
        self._web.page().runJavaScript(
            "typeof _viewer !== 'undefined' && _viewer !== null",
            self._on_poll_result,
        )

    def _on_poll_result(self, is_ready):
        if is_ready:
            self._on_viewer_js_ready()
        else:
            self._poll_count += 1
            if self._poll_count < 30:   # give up after ~15 s
                QTimer.singleShot(500, self._poll_viewer_ready)

    def _on_viewer_js_ready(self):
        """Called by JS bridge.viewerReady() OR polling fallback — safe to run JS now."""
        if self._page_ready:
            return  # already initialised (bridge + poll may both fire)
        self._page_ready = True
        for js in self._pending_js:
            self._web.page().runJavaScript(js)
        self._pending_js.clear()
        # Force multiple resize passes — the WebGL framebuffer needs valid
        # dimensions and the QSplitter may still be laying out.
        resize_js = "if (_viewer) { _viewer.resize(); _viewer.render(); }"
        for delay in (100, 500, 1500):
            QTimer.singleShot(delay, lambda: self._run_js(resize_js))

    # ── Public API ────────────────────────────────────────────────────────────

    def load_smiles(self, smiles: str):
        """
        Start async conformer generation for *smiles*.

        Emits conformer_loading() immediately.
        Emits conformer_ready() when the first conformer is displayed.
        """
        if not smiles or not smiles.strip():
            return

        self._current_smiles = smiles.strip()

        # Cancel any previous worker
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(500)

        self._conformers = []
        self._current_idx = 0
        self._update_conformer_controls()
        self.conformer_loading.emit()

        self._worker = _ConformerWorker(self._current_smiles)
        self._worker.finished.connect(self._on_conformers_ready)
        self._worker.start()

    def clear(self):
        """Clear the 3D viewer and reset state."""
        if _HAS_WEBENGINE:
            self._run_js("clearViewer()")
        self._conformers = []
        self._current_idx = 0
        self._scaffold_atoms = []
        self._hbd_indices = []
        self._hba_indices = []
        self._nmr_label_data = []
        self._surface_charges = {}
        self._current_smiles = ""
        self._update_conformer_controls()
        # Disable highlight checkboxes
        if hasattr(self, "_scaffold_cb"):
            self._scaffold_cb.setEnabled(False)
            self._scaffold_cb.setChecked(False)
            self._hbd_hba_cb.setEnabled(False)
            self._hbd_hba_cb.setChecked(False)
            self._nmr_labels_cb.setEnabled(False)
            self._nmr_labels_cb.setChecked(False)

    def highlight_atoms(self, indices: list[int], color: str = "#EC4899",
                        label: str = ""):
        """Highlight atoms by index in the 3D viewer."""
        if not _HAS_WEBENGINE or not indices:
            return
        import json as _json
        arr = _json.dumps(indices)
        lbl = label.replace("'", "\\'").replace('"', '\\"')
        self._run_js(f"highlightAtoms({arr}, '{color}', '{lbl}')")

    def clear_highlight(self):
        """Remove all correlation highlights."""
        if _HAS_WEBENGINE:
            self._run_js("clearHighlight()")

    def rotate_to_atom(self, idx: int):
        """Smoothly rotate the view to center on an atom."""
        if _HAS_WEBENGINE:
            self._run_js(f"rotateToAtom({idx})")

    def highlight_bonds(self, bond_pairs: list[tuple[int, int]],
                        color: str = "#F59E0B"):
        """Highlight bonds between atom pairs (for IR correlation)."""
        if not _HAS_WEBENGINE or not bond_pairs:
            return
        import json as _json
        pairs = _json.dumps([[a, b] for a, b in bond_pairs])
        self._run_js(f"highlightBonds({pairs}, '{color}')")

    def take_screenshot(self) -> Optional[QPixmap]:
        """Return a screenshot of the viewer as a QPixmap, or None."""
        if not _HAS_WEBENGINE:
            return None
        return self._web.grab()

    # ── Feature data setters (called from main_window after analysis) ─────

    def set_scaffold_atoms(self, indices: list[int]):
        """Set scaffold atom indices, enabling the Scaffold checkbox."""
        self._scaffold_atoms = indices
        if hasattr(self, "_scaffold_cb"):
            self._scaffold_cb.setEnabled(bool(indices))

    def set_hbd_hba(self, hbd: list[int], hba: list[int]):
        """Set H-bond donor/acceptor indices, enabling the HBD/HBA checkbox."""
        self._hbd_indices = hbd
        self._hba_indices = hba
        if hasattr(self, "_hbd_hba_cb"):
            self._hbd_hba_cb.setEnabled(bool(hbd or hba))

    def set_nmr_label_data(self, data: list[dict]):
        """Set NMR label data for 3D annotation, enabling the NMR Labels checkbox."""
        self._nmr_label_data = data
        if hasattr(self, "_nmr_labels_cb"):
            self._nmr_labels_cb.setEnabled(bool(data))

    def set_surface_charges(self, charges: dict[int, float]):
        """Pre-store Gasteiger charges for Surface mode."""
        self._surface_charges = charges

    def resizeEvent(self, event):
        """Resize 3Dmol canvas when the Python widget is resized."""
        super().resizeEvent(event)
        if self._page_ready:
            self._run_js("if (_viewer) _viewer.resize();")

    def keyPressEvent(self, event):
        """Keyboard navigation for conformer carousel."""
        key = event.key()
        if key == Qt.Key_Left:
            self._prev_conformer()
        elif key == Qt.Key_Right:
            self._next_conformer()
        elif key == Qt.Key_Home:
            if self._conformers:
                self._current_idx = 0
                self._display_conformer(0)
                self._update_conformer_controls()
        elif key == Qt.Key_End:
            if self._conformers:
                self._current_idx = len(self._conformers) - 1
                self._display_conformer(self._current_idx)
                self._update_conformer_controls()
        else:
            super().keyPressEvent(event)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _on_conformers_ready(self, results: list):
        """Called from _ConformerWorker.finished — back on the main thread."""
        self._conformers = results
        self._current_idx = 0
        self._update_conformer_controls()

        if results:
            self._display_conformer(0)
            self.conformer_ready.emit()

    def _display_conformer(self, idx: int):
        if 0 <= idx < len(self._conformers):
            sdf, _energy = self._conformers[idx]
            escaped = sdf.replace("\\", "\\\\").replace("`", "\\`")
            self._run_js(f"loadMolecule(`{escaped}`)")

    def _prev_conformer(self):
        if self._current_idx > 0:
            self._current_idx -= 1
            self._display_conformer(self._current_idx)
            self._update_conformer_controls()

    def _next_conformer(self):
        if self._current_idx < len(self._conformers) - 1:
            self._current_idx += 1
            self._display_conformer(self._current_idx)
            self._update_conformer_controls()

    def _update_conformer_controls(self):
        if not hasattr(self, "_conf_label"):
            return
        total = len(self._conformers)
        if total == 0:
            self._conf_label.setText("No conformer")
            self._conf_label.setFixedWidth(100)
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
        else:
            idx = self._current_idx
            sdf, energy = self._conformers[idx]
            # ΔE relative to lowest-energy conformer
            min_e = self._conformers[0][1] if self._conformers else 0.0
            delta_e = energy - min_e

            # Color-code ΔE
            if delta_e <= 2.0:
                e_color = Colors.ACCENT_GREEN
            elif delta_e <= 5.0:
                e_color = Colors.ACCENT_AMBER
            else:
                e_color = Colors.ACCENT_RED

            label_text = f"Conf {idx + 1}/{total}"
            if energy > 0:
                label_text += f"  |  ΔE={delta_e:.1f}"

            self._conf_label.setText(label_text)
            self._conf_label.setFixedWidth(180)
            self._conf_label.setStyleSheet(
                f"color: {e_color}; font-size: 11px;"
            )
            self._prev_btn.setEnabled(idx > 0)
            self._next_btn.setEnabled(idx < total - 1)

    def _set_style(self, style_cmd: str, active_btn: QPushButton):
        for btn in self._style_group.buttons():
            btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        active_btn.setProperty("active", "true")
        active_btn.style().unpolish(active_btn)
        active_btn.style().polish(active_btn)
        # If surface button was active, clear surface first
        if hasattr(self, "_surface_btn") and active_btn != self._surface_btn:
            self._run_js("clearSurface()")
        self._run_js(f"applyStyle('{style_cmd}')")

    def _toggle_surface(self, checked: bool):
        """Toggle electrostatic surface mode."""
        if not checked:
            # Revert to stick
            self._run_js("clearSurface()")
            for btn in self._style_group.buttons():
                if btn.text() == "Stick":
                    btn.setChecked(True)
                    self._set_style("stick", btn)
                    break
            return

        if not self._conformers:
            QMessageBox.warning(
                self, "No Conformer",
                "Load a molecule first to use Surface mode."
            )
            self._surface_btn.setChecked(False)
            return

        # Load surface with current conformer
        sdf, _energy = self._conformers[self._current_idx]
        charges_json = json.dumps({str(k): v for k, v in self._surface_charges.items()})
        escaped = sdf.replace("\\", "\\\\").replace("`", "\\`")
        self._run_js(f"loadSurface(`{escaped}`, '{charges_json}')")

        # Activate button styling
        for btn in self._style_group.buttons():
            btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._surface_btn.setProperty("active", "true")
        self._surface_btn.style().unpolish(self._surface_btn)
        self._surface_btn.style().polish(self._surface_btn)

    def _toggle_hydrogens(self, checked: bool):
        """Toggle hydrogen visibility."""
        self._run_js(f"toggleHydrogens({'true' if checked else 'false'})")
        self._h_btn.setProperty("active", "true" if checked else "false")
        self._h_btn.style().unpolish(self._h_btn)
        self._h_btn.style().polish(self._h_btn)

    def _toggle_heteroatoms(self, state: int):
        if state == Qt.Checked:
            self._run_js("highlightHeteroatoms()")
        else:
            self._run_js("unhighlightAll()")

    def _toggle_scaffold(self, state: int):
        """Toggle scaffold core highlight."""
        if not _HAS_WEBENGINE:
            return
        on = state == Qt.Checked
        arr = json.dumps(self._scaffold_atoms)
        self._run_js(f"highlightScaffold({arr}, {'true' if on else 'false'})")

    def _toggle_hbd_hba(self, state: int):
        """Toggle HBD/HBA highlights."""
        if not _HAS_WEBENGINE:
            return
        on = state == Qt.Checked
        hbd = json.dumps(self._hbd_indices)
        hba = json.dumps(self._hba_indices)
        self._run_js(f"highlightHBonds({hbd}, {hba}, {'true' if on else 'false'})")

    def _toggle_nmr_labels(self, state: int):
        """Toggle NMR assignment labels on 3D viewer."""
        if not _HAS_WEBENGINE:
            return
        on = state == Qt.Checked
        data = json.dumps(self._nmr_label_data)
        self._run_js(f"showNMRLabels({data}, {'true' if on else 'false'})")

    def _set_background(self, hex_color: str):
        """Set the 3D viewer background color."""
        self._run_js(f'setBackground("{hex_color}")')
        settings = QSettings("SpectraAI", "SpectraAI")
        settings.setValue("viewer/background", hex_color)

    def _take_screenshot_dialog(self):
        """Request a screenshot from 3Dmol.js via bridge."""
        if not _HAS_WEBENGINE or not self._page_ready:
            return
        self._run_js("takeScreenshot()")

    def _on_screenshot_ready(self, base64_png: str):
        """Handle screenshot data from JS bridge."""
        import base64
        try:
            png_data = base64.b64decode(base64_png)
        except Exception:
            return

        pixmap = QPixmap()
        pixmap.loadFromData(png_data, "PNG")
        if pixmap.isNull():
            return

        # Ask user: save or copy
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot",
            "spectra_ai_3d.png",
            "PNG Files (*.png);;All Files (*)",
        )
        if filepath:
            pixmap.save(filepath, "PNG")
        else:
            # Copy to clipboard
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setPixmap(pixmap)

    def _on_measurement_ready(self, mtype: str, value: float, atoms_json: str):
        """Forward measurement data from JS bridge."""
        self.measurement_signal.emit(mtype, value, atoms_json)

    def _toggle_measure(self, checked: bool):
        self._run_js("setMeasureMode(true)" if checked else "setMeasureMode(false)")
        if checked and hasattr(self, '_coord_btn') and self._coord_btn.isChecked():
            self._coord_btn.setChecked(False)
            self._coord_btn.setProperty("active", "false")
            self._coord_btn.style().unpolish(self._coord_btn)
            self._coord_btn.style().polish(self._coord_btn)
            self._coord_btn.update()
        self._measure_btn.setProperty("active", "true" if checked else "false")
        self._measure_btn.style().unpolish(self._measure_btn)
        self._measure_btn.style().polish(self._measure_btn)
        self._measure_btn.update()

    def _toggle_coord_mode(self, checked: bool):
        self._run_js("setCoordMode(true)" if checked else "setCoordMode(false)")
        if checked and self._measure_btn.isChecked():
            self._measure_btn.setChecked(False)
            self._measure_btn.setProperty("active", "false")
            self._measure_btn.style().unpolish(self._measure_btn)
            self._measure_btn.style().polish(self._measure_btn)
            self._measure_btn.update()
        self._coord_btn.setProperty("active", "true" if checked else "false")
        self._coord_btn.style().unpolish(self._coord_btn)
        self._coord_btn.style().polish(self._coord_btn)
        self._coord_btn.update()

    def _try_download_3dmol(self):
        """Best-effort background download of 3dmol-min.js."""
        try:
            import requests  # type: ignore[import]
            resp = requests.get(_3DMOL_CDN, timeout=30)
            if resp.status_code == 200:
                _3DMOL_LOCAL.write_bytes(resp.content)
        except Exception:
            pass  # Non-critical — CDN fallback still works
