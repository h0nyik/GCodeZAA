#!/usr/bin/env python3
"""
GCodeZAA GUI — Dark Mode 2.0 + Liquid Glass — 2026
Features: i18n (CS/EN/DE), file logging, verbose mode, bug reporting
"""
from __future__ import annotations

import sys, os, io, queue, threading, json, logging, locale, webbrowser
import urllib.request, urllib.parse
from pathlib import Path
from logging.handlers import RotatingFileHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


# ── Version ────────────────────────────────────────────────────────────────────
APP_VERSION = "0.2.0"
ISSUES_URL  = "https://github.com/h0nyik/GCodeZAA-GUI/issues/new"
GIST_API    = "https://api.github.com/gists"


# ── Platform paths ─────────────────────────────────────────────────────────────
def _app_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "GCodeZAA"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "GCodeZAA"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "GCodeZAA"

def _log_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "GCodeZAA"
    return _app_data_dir() / "logs"

CONFIG_FILE = _app_data_dir() / "config.json"
LOG_FILE    = _log_dir() / "gcodezaa.log"


# ── Config ─────────────────────────────────────────────────────────────────────
def _load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_config(cfg: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

_config = _load_config()


# ── File logging ───────────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
_fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))
logger = logging.getLogger("gcodezaa")
logger.setLevel(logging.DEBUG)
logger.addHandler(_fh)
logger.info(f"=== GCodeZAA GUI {APP_VERSION} — Python {sys.version.split()[0]} — {sys.platform} ===")


# ── i18n ───────────────────────────────────────────────────────────────────────
_STRINGS: dict[str, dict[str, str]] = {
    "cs": {
        "waiting":        "Čeká na soubor",
        "input_title":    "VSTUPNÍ SOUBOR",
        "drop_hint":      "Přetáhni .gcode soubor",
        "drop_or":        "nebo",
        "browse":         "Vybrat soubor",
        "models_title":   "Složka modelů (STL)",
        "models_hint":    "/cesta/ke/stl/složce",
        "models_desc":    "STL modely pro raycasting (OrcaSlicer / Klipper)",
        "info_title":     "Info",
        "info_slicer":    "Slicer",
        "info_layers":    "Vrstvy",
        "info_objects":   "Objekty",
        "info_height":    "Výška vrstvy",
        "output_title":   "VÝSTUP",
        "out_overwrite":  "Přepsat vstupní soubor",
        "out_saveas":     "Uložit jako nový soubor",
        "out_hint":       "Výstupní cesta…",
        "adv_title":      "Rozšířené — Bambu / Jednoobjektový",
        "adv_desc":       "Pro Bambu Studio nebo single-object mód bez Klipper",
        "pos_x":          "Pozice X",
        "pos_y":          "Pozice Y",
        "stl_name":       "Název STL",
        "run_btn":        "▶   ZPRACOVAT GCODE",
        "running_btn":    "⏳   ZPRACOVÁVÁM…",
        "log_title":      "LOG",
        "log_clear":      "Vymazat",
        "log_verbose":    "Podrobný",
        "log_report":     "Nahlásit chybu",
        "ready":          "Připraven",
        "processing":     "Zpracovávám…",
        "done_status":    "✓ Hotovo",
        "err_status":     "✗ Chyba",
        "unknown":        "Neznámý",
        "dlg_gcode":      "Vybrat G-code soubor",
        "dlg_models":     "Vybrat složku STL modelů",
        "dlg_save":       "Uložit výstup jako",
        "warn_no_input":  "⚠ Nejprve vyberte vstupní .gcode soubor.",
        "warn_pos":       "⚠ Pozice X/Y musí být čísla (např. 125.5).",
        "log_loading":    "Načítám informace o souboru…",
        "log_detected":   "Detekováno: {slicer} | Vrstvy: {layers} | Objekty: {objects} | Výška: {height}",
        "log_start":      "▶ Spouštím: {name}",
        "log_lines":      "Celkem {n:,} řádků G-code",
        "log_loading_f":  "Načítám {name}…",
        "log_done":       "Hotovo → {name}",
        "log_err":        "✗ Chyba: {msg}",
        "report_ok":      "Report otevřen v prohlížeči — přidej popis a odešli.",
        "report_fail":    "Log zkopírován do schránky — vlož do issue ručně.",
        "log_path":       "Log: {path}",
    },
    "en": {
        "waiting":        "Waiting for file",
        "input_title":    "INPUT FILE",
        "drop_hint":      "Drop .gcode file here",
        "drop_or":        "or",
        "browse":         "Browse",
        "models_title":   "Models folder (STL)",
        "models_hint":    "/path/to/stl/folder",
        "models_desc":    "STL models for raycasting (OrcaSlicer / Klipper)",
        "info_title":     "Info",
        "info_slicer":    "Slicer",
        "info_layers":    "Layers",
        "info_objects":   "Objects",
        "info_height":    "Layer height",
        "output_title":   "OUTPUT",
        "out_overwrite":  "Overwrite input file",
        "out_saveas":     "Save as new file",
        "out_hint":       "Output path…",
        "adv_title":      "Advanced — Bambu / Single object",
        "adv_desc":       "For Bambu Studio or single-object mode without Klipper",
        "pos_x":          "Position X",
        "pos_y":          "Position Y",
        "stl_name":       "STL name",
        "run_btn":        "▶   PROCESS GCODE",
        "running_btn":    "⏳   PROCESSING…",
        "log_title":      "LOG",
        "log_clear":      "Clear",
        "log_verbose":    "Verbose",
        "log_report":     "Report bug",
        "ready":          "Ready",
        "processing":     "Processing…",
        "done_status":    "✓ Done",
        "err_status":     "✗ Error",
        "unknown":        "Unknown",
        "dlg_gcode":      "Select G-code file",
        "dlg_models":     "Select STL models folder",
        "dlg_save":       "Save output as",
        "warn_no_input":  "⚠ Please select an input .gcode file first.",
        "warn_pos":       "⚠ X/Y position must be numbers (e.g. 125.5).",
        "log_loading":    "Loading file info…",
        "log_detected":   "Detected: {slicer} | Layers: {layers} | Objects: {objects} | Height: {height}",
        "log_start":      "▶ Starting: {name}",
        "log_lines":      "Total {n:,} lines of G-code",
        "log_loading_f":  "Loading {name}…",
        "log_done":       "Done → {name}",
        "log_err":        "✗ Error: {msg}",
        "report_ok":      "Report opened in browser — add description and submit.",
        "report_fail":    "Log copied to clipboard — paste it into the issue manually.",
        "log_path":       "Log: {path}",
    },
    "de": {
        "waiting":        "Warte auf Datei",
        "input_title":    "EINGABEDATEI",
        "drop_hint":      "G-code-Datei hier ablegen",
        "drop_or":        "oder",
        "browse":         "Durchsuchen",
        "models_title":   "Modellordner (STL)",
        "models_hint":    "/Pfad/zum/STL-Ordner",
        "models_desc":    "STL-Modelle für Raycasting (OrcaSlicer / Klipper)",
        "info_title":     "Info",
        "info_slicer":    "Slicer",
        "info_layers":    "Schichten",
        "info_objects":   "Objekte",
        "info_height":    "Schichthöhe",
        "output_title":   "AUSGABE",
        "out_overwrite":  "Eingabedatei überschreiben",
        "out_saveas":     "Als neue Datei speichern",
        "out_hint":       "Ausgabepfad…",
        "adv_title":      "Erweitert — Bambu / Einzelobjekt",
        "adv_desc":       "Für Bambu Studio oder Einzelobjekt-Modus ohne Klipper",
        "pos_x":          "Position X",
        "pos_y":          "Position Y",
        "stl_name":       "STL-Name",
        "run_btn":        "▶   GCODE VERARBEITEN",
        "running_btn":    "⏳   VERARBEITE…",
        "log_title":      "LOG",
        "log_clear":      "Löschen",
        "log_verbose":    "Ausführlich",
        "log_report":     "Fehler melden",
        "ready":          "Bereit",
        "processing":     "Verarbeite…",
        "done_status":    "✓ Fertig",
        "err_status":     "✗ Fehler",
        "unknown":        "Unbekannt",
        "dlg_gcode":      "G-code-Datei auswählen",
        "dlg_models":     "STL-Modellordner auswählen",
        "dlg_save":       "Ausgabe speichern als",
        "warn_no_input":  "⚠ Bitte zuerst eine G-code-Datei auswählen.",
        "warn_pos":       "⚠ X/Y-Position müssen Zahlen sein (z.B. 125.5).",
        "log_loading":    "Dateiinfo wird geladen…",
        "log_detected":   "Erkannt: {slicer} | Schichten: {layers} | Objekte: {objects} | Höhe: {height}",
        "log_start":      "▶ Starte: {name}",
        "log_lines":      "{n:,} G-code-Zeilen gesamt",
        "log_loading_f":  "Lade {name}…",
        "log_done":       "Fertig → {name}",
        "log_err":        "✗ Fehler: {msg}",
        "report_ok":      "Bericht im Browser geöffnet — Beschreibung hinzufügen und absenden.",
        "report_fail":    "Log in Zwischenablage — manuell in das Issue einfügen.",
        "log_path":       "Log: {path}",
    },
}

def _detect_lang() -> str:
    try:
        loc = locale.getdefaultlocale()[0] or ""
    except Exception:
        loc = ""
    if loc.startswith("de"):
        return "de"
    if loc.startswith("cs") or loc.startswith("sk"):
        return "cs"
    return "en"

_LANG: str = _config.get("language", _detect_lang())

def t(key: str, **kwargs) -> str:
    s = _STRINGS.get(_LANG, _STRINGS["en"]).get(key, _STRINGS["en"].get(key, key))
    return s.format(**kwargs) if kwargs else s


# ── Design tokens ──────────────────────────────────────────────────────────────
BG      = "#0a0e1a"
CARD    = "#111827"
CARD_ALT= "#0c1423"
BORDER  = "#1c2b45"
BDR_HL  = "#2a4070"
ACCENT  = "#00d4ff"
ACC_BTN = "#0099bb"
ACC_DIM = "#005f75"
TEXT    = "#e2e8f0"
MUTED   = "#4a6080"
DIM     = "#2a3d55"
SUCCESS = "#22c55e"
ERROR   = "#ef4444"
WARN    = "#f59e0b"
INPUT   = "#080c18"

SLICER_COLORS = {"OrcaSlicer": "#22c55e", "BambuStudio": "#3b82f6", "PrusaSlicer": "#f59e0b"}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
_IS_MAC = sys.platform == "darwin"

def fui(size=12, weight="normal"):
    return ("SF Pro Text" if _IS_MAC else "Segoe UI", size, weight)

def fmono(size=11):
    return ("SF Pro Mono" if _IS_MAC else "Consolas", size)

def fdisplay(size=14, weight="bold"):
    return ("SF Pro Display" if _IS_MAC else "Segoe UI", size, weight)


# ── G-code analyzer ────────────────────────────────────────────────────────────
def analyze_gcode(path: str) -> dict:
    info = {"slicer": t("unknown"), "layers": 0, "objects": 0, "layer_height": "?"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[:10]:
            if "OrcaSlicer"  in line: info["slicer"] = "OrcaSlicer";  break
            if "BambuStudio" in line: info["slicer"] = "BambuStudio"; break
            if "PrusaSlicer" in line: info["slicer"] = "PrusaSlicer"; break
        in_cfg = False
        for line in lines:
            if "; CONFIG_BLOCK_START" in line: in_cfg = True;  continue
            if "; CONFIG_BLOCK_END"   in line: in_cfg = False; continue
            if in_cfg and line.startswith("; layer_height"):
                try:
                    info["layer_height"] = line.split("=")[1].strip() + " mm"
                except Exception:
                    pass
            if ";LAYER_CHANGE" in line or "; CHANGE_LAYER" in line:
                info["layers"] += 1
            if "EXCLUDE_OBJECT_DEFINE" in line:
                info["objects"] += 1
    except Exception:
        pass
    return info


# ── Bug reporting ──────────────────────────────────────────────────────────────
def _read_log_tail(n_lines: int = 300) -> str:
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n_lines:])
    except Exception:
        return "(log unavailable)"

def _create_gist(content: str) -> str | None:
    """Create anonymous GitHub Gist, return URL or None on failure."""
    try:
        payload = json.dumps({
            "description": f"GCodeZAA {APP_VERSION} bug report",
            "public": False,
            "files": {"gcodezaa.log": {"content": content or "(empty)"}},
        }).encode()
        req = urllib.request.Request(
            GIST_API, data=payload,
            headers={"Content-Type": "application/json",
                     "User-Agent": f"GCodeZAA-GUI/{APP_VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["html_url"]
    except Exception as e:
        logger.warning(f"Gist creation failed: {e}")
        return None

def open_bug_report(error_msg: str, slicer: str, app_root):
    log_tail = _read_log_tail()
    gist_url = _create_gist(log_tail)

    body = (
        f"**Version:** {APP_VERSION}\n"
        f"**OS:** {sys.platform} — Python {sys.version.split()[0]}\n"
        f"**Slicer:** {slicer}\n\n"
        f"**Error:**\n```\n{error_msg}\n```\n\n"
        + (f"**Full log (Gist):** {gist_url}\n" if gist_url else
           f"**Log:** *(attach manually — see {LOG_FILE})*\n")
        + "\n**Steps to reproduce:**\n1. \n2. \n\n"
          "---\n*Auto-generated by GCodeZAA GUI*"
    )
    title = f"[BUG] {error_msg[:80]}" if error_msg else "[BUG] <popis problému>"
    params = urllib.parse.urlencode({
        "title": title,
        "body":  body,
        "labels": "bug",
    })
    webbrowser.open(f"{ISSUES_URL}?{params}")

    if gist_url:
        _log_gui(app_root, t("report_ok"), "success")
    else:
        try:
            app_root.clipboard_clear()
            app_root.clipboard_append(log_tail)
        except Exception:
            pass
        _log_gui(app_root, t("report_fail"), "warn")

def _log_gui(app_root, msg: str, tag: str = "muted"):
    """Helper: log to GUI textbox from any thread via after()."""
    def _do():
        try:
            tb = app_root._logbox._textbox
            tb.configure(state="normal")
            tb.insert("end", msg + "\n", tag)
            tb.configure(state="disabled")
            tb.see("end")
        except Exception:
            pass
    app_root.after(0, _do)


# ── Background worker ──────────────────────────────────────────────────────────
def run_worker(input_path: str, models_dir, output_path, plate_model,
               log_q: queue.Queue, verbose: bool):

    class QueueWriter(io.TextIOBase):
        def __init__(self, is_verbose: bool = False):
            self._verbose = is_verbose
        def write(self, s):
            if s.strip():
                log_q.put(("log", s.rstrip(), self._verbose))
                logger.debug(s.rstrip()) if self._verbose else logger.info(s.rstrip())
            return len(s)
        def flush(self): pass

    import time

    def vlog(msg: str):
        """Emit a verbose-only log line."""
        if verbose:
            log_q.put(("log", msg, True))
            logger.debug(msg)

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = QueueWriter(is_verbose=False)
    sys.stderr = QueueWriter(is_verbose=True)   # open3d warnings → verbose only
    try:
        from gcodezaa.process import process_gcode
        name = Path(input_path).name
        log_q.put(("log", t("log_loading_f", name=name), False))

        with open(input_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        log_q.put(("log", t("log_lines", n=len(lines)), False))

        vlog(f"  Modely: {models_dir or '—'}")
        vlog(f"  Plate model: {plate_model or '—'}")

        t0 = time.perf_counter()
        result = process_gcode(lines, models_dir, plate_model)
        elapsed = time.perf_counter() - t0

        # ── Verbose stats: scan result for contour markers ─────────────────
        if verbose:
            contour_counts: dict[str, int] = {}
            reset_z = 0
            max_layer = 0
            for line in result:
                if line.startswith(";") and "_CONTOUR " in line:
                    key = line[1:line.index(" ")].replace("_CONTOUR", "")
                    contour_counts[key] = contour_counts.get(key, 0) + 1
                elif line.startswith(";RESET_Z"):
                    reset_z += 1
                elif line.startswith(";LAYER_CHANGE") or "layer_num" in line.lower():
                    max_layer += 1
            total = sum(contour_counts.values())
            vlog(f"  ── ZAA statistiky ──────────────────────────────")
            vlog(f"  Zpracovací čas:      {elapsed:.2f} s")
            vlog(f"  Celkem segmentů:     {len(result)} řádků výsledku")
            vlog(f"  Konturované seg.:    {total}")
            for kind, cnt in sorted(contour_counts.items()):
                vlog(f"    {kind:<20} {cnt:>6}×")
            vlog(f"  Reset Z (po kontuře): {reset_z}×")
            vlog(f"  ────────────────────────────────────────────────")

        out = output_path or input_path
        with open(out, "w", encoding="utf-8") as f:
            f.writelines(result)

        size_kb = Path(out).stat().st_size // 1024
        vlog(f"  Zapsáno: {Path(out).name} ({size_kb} KB)")
        log_q.put(("done", t("log_done", name=Path(out).name)))
        logger.info(f"Processing done → {out}")
    except Exception as exc:
        log_q.put(("error", str(exc)))
        logger.error(f"Processing error: {exc}", exc_info=True)
    finally:
        sys.stdout, sys.stderr = old_out, old_err


# ── Main application ───────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        global HAS_DND
        if HAS_DND:
            try:
                TkinterDnD._require(self)
            except Exception:
                HAS_DND = False

        self.input_path  = tk.StringVar()
        self.models_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.out_mode    = tk.StringVar(value="overwrite")
        self.pos_x       = tk.StringVar()
        self.pos_y       = tk.StringVar()
        self.stl_name    = tk.StringVar()
        self._log_q      = queue.Queue()
        self._processing = False
        self._prog_dir   = 1
        self._gcode_info = {}
        self._verbose    = tk.BooleanVar(value=False)
        self._last_error = ""

        self.title("GCodeZAA")
        self.geometry("1300x800")
        self.minsize(960, 620)
        self.configure(fg_color=BG)

        self._build()
        self._poll()

        logger.info(f"UI ready — lang={_LANG}")
        self._log(t("log_path", path=str(LOG_FILE)), "muted")

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=30)
        content.grid_columnconfigure(1, weight=30)
        content.grid_columnconfigure(2, weight=40)

        self._build_col_left(content)
        self._build_col_mid(content)
        self._build_col_right(content)

    def _build_header(self):
        h = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=54)
        h.grid(row=0, column=0, sticky="ew")
        h.grid_columnconfigure(1, weight=1)
        h.grid_propagate(False)

        logo = ctk.CTkFrame(h, fg_color="transparent")
        logo.grid(row=0, column=0, padx=18, sticky="ns")
        ctk.CTkLabel(logo, text="⬡", font=fdisplay(20), text_color=ACCENT).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo, text="GCodeZAA", font=fdisplay(15, "bold"), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(logo, text="Z Anti-Aliasing", font=fui(11), text_color=MUTED).pack(side="left", padx=(10, 0))

        self._slicer_badge = ctk.CTkLabel(
            h, text=f"  {t('waiting')}  ", font=fui(11),
            text_color=MUTED, fg_color=CARD_ALT, corner_radius=4,
        )
        self._slicer_badge.grid(row=0, column=1, sticky="e", padx=(0, 12))

        # Language switcher
        lang_f = ctk.CTkFrame(h, fg_color="transparent")
        lang_f.grid(row=0, column=2, padx=(0, 8), sticky="ns")
        for code, label in [("cs", "CS"), ("en", "EN"), ("de", "DE")]:
            is_active = code == _LANG
            ctk.CTkButton(
                lang_f, text=label, width=32, height=26,
                font=fui(10, "bold"),
                fg_color=ACC_DIM if is_active else "transparent",
                hover_color=BDR_HL, text_color=ACCENT if is_active else MUTED,
                corner_radius=4,
                command=lambda c=code: self._set_lang(c),
            ).pack(side="left", padx=2)

        ctk.CTkLabel(h, text=f"v{APP_VERSION}", font=fmono(11), text_color=DIM).grid(
            row=0, column=3, padx=14)

    def _set_lang(self, lang: str):
        global _LANG
        _LANG = lang
        _config["language"] = lang
        _save_config(_config)
        logger.info(f"Language changed to {lang}, relaunching")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def _card(self, parent, title=None, col=0, row=0, rowspan=1,
              padx=(0, 0), pady=(0, 8), sticky="nsew"):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                         border_width=1, border_color=BORDER)
        f.grid(row=row, column=col, rowspan=rowspan, sticky=sticky,
               padx=padx, pady=pady)
        if title:
            ctk.CTkLabel(f, text=title.upper(), font=fui(9, "bold"),
                         text_color=MUTED).pack(anchor="w", padx=16, pady=(13, 5))
            ctk.CTkFrame(f, fg_color=BORDER, height=1, corner_radius=0).pack(
                fill="x", padx=16, pady=(0, 10))
        return f

    # ── Left column ────────────────────────────────────────────────────────────

    def _build_col_left(self, parent):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        col.grid_columnconfigure(0, weight=1)
        col.grid_rowconfigure(2, weight=1)

        drop = ctk.CTkFrame(col, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        drop.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ctk.CTkLabel(drop, text=t("input_title"), font=fui(9, "bold"),
                     text_color=MUTED).pack(anchor="w", padx=16, pady=(13, 5))
        ctk.CTkFrame(drop, fg_color=BORDER, height=1, corner_radius=0).pack(
            fill="x", padx=16, pady=(0, 10))

        self._dz = ctk.CTkFrame(drop, fg_color=INPUT, corner_radius=8,
                                border_width=1, border_color=BORDER)
        self._dz.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(self._dz, text="🗂", font=(fmono(30)[0], 30)).pack(pady=(18, 3))
        self._dz_label = ctk.CTkLabel(self._dz, text=t("drop_hint"),
                                      font=fui(13, "bold"), text_color=TEXT)
        self._dz_label.pack()
        ctk.CTkLabel(self._dz, text=t("drop_or"), font=fui(11), text_color=MUTED).pack(pady=2)
        ctk.CTkButton(
            self._dz, text=t("browse"), font=fui(12),
            fg_color=ACC_DIM, hover_color=ACC_BTN, text_color=TEXT,
            corner_radius=6, height=30, command=self._pick_gcode,
        ).pack(pady=(2, 16))

        self._fname_label = ctk.CTkLabel(drop, text="", font=fmono(10),
                                         text_color=MUTED, wraplength=260)
        self._fname_label.pack(padx=14, pady=(0, 12))

        if HAS_DND:
            self._dz.drop_target_register(DND_FILES)
            self._dz.dnd_bind("<<Drop>>",      self._on_drop)
            self._dz.dnd_bind("<<DragEnter>>", lambda e: self._dz.configure(border_color=ACCENT))
            self._dz.dnd_bind("<<DragLeave>>", lambda e: self._dz.configure(border_color=BORDER))

        mc = self._card(col, t("models_title"), row=1, pady=(0, 7))
        mr = ctk.CTkFrame(mc, fg_color="transparent")
        mr.pack(fill="x", padx=14, pady=(0, 6))
        mr.grid_columnconfigure(0, weight=1)

        self._models_entry = ctk.CTkEntry(
            mr, textvariable=self.models_path,
            placeholder_text=t("models_hint"),
            font=fmono(10), fg_color=INPUT, border_color=BORDER,
            text_color=TEXT, height=32, corner_radius=6,
        )
        self._models_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(mr, text="📁", width=36, height=32, fg_color=BORDER,
                      hover_color=BDR_HL, corner_radius=6,
                      command=self._pick_models_dir).grid(row=0, column=1)

        ctk.CTkLabel(mc, text=t("models_desc"),
                     font=fui(10), text_color=MUTED).pack(anchor="w", padx=14, pady=(0, 12))

        ic = self._card(col, t("info_title"), row=2, sticky="new", pady=(0, 0))
        self._i_slicer  = self._irow(ic, t("info_slicer"),  "—")
        self._i_layers  = self._irow(ic, t("info_layers"),  "—")
        self._i_objects = self._irow(ic, t("info_objects"), "—")
        self._i_height  = self._irow(ic, t("info_height"),  "—", last=True)

    def _irow(self, parent, label: str, val: str, last=False):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(r, text=label, font=fui(11), text_color=MUTED,
                     anchor="w", width=110).pack(side="left")
        lbl = ctk.CTkLabel(r, text=val, font=fmono(11), text_color=ACCENT, anchor="e")
        lbl.pack(side="right")
        if last:
            ctk.CTkFrame(parent, fg_color="transparent", height=10).pack()
        return lbl

    # ── Middle column ──────────────────────────────────────────────────────────

    def _build_col_mid(self, parent):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=1, sticky="nsew", padx=7)
        col.grid_columnconfigure(0, weight=1)
        col.grid_rowconfigure(2, weight=1)

        oc = self._card(col, t("output_title"), row=0, pady=(0, 7))
        ctk.CTkRadioButton(
            oc, text=t("out_overwrite"),
            variable=self.out_mode, value="overwrite",
            font=fui(12), text_color=TEXT, fg_color=ACCENT, hover_color=ACC_BTN,
            command=self._toggle_out,
        ).pack(anchor="w", padx=16, pady=(0, 6))
        ctk.CTkRadioButton(
            oc, text=t("out_saveas"),
            variable=self.out_mode, value="saveas",
            font=fui(12), text_color=TEXT, fg_color=ACCENT, hover_color=ACC_BTN,
            command=self._toggle_out,
        ).pack(anchor="w", padx=16, pady=(0, 10))

        outr = ctk.CTkFrame(oc, fg_color="transparent")
        outr.pack(fill="x", padx=14, pady=(0, 14))
        outr.grid_columnconfigure(0, weight=1)

        self._out_entry = ctk.CTkEntry(
            outr, textvariable=self.output_path,
            placeholder_text=t("out_hint"),
            font=fmono(10), fg_color=INPUT, border_color=BORDER,
            text_color=TEXT, height=32, corner_radius=6, state="disabled",
        )
        self._out_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._out_btn = ctk.CTkButton(
            outr, text="💾", width=36, height=32,
            fg_color=BORDER, hover_color=BDR_HL, corner_radius=6,
            state="disabled", command=self._pick_output,
        )
        self._out_btn.grid(row=0, column=1)

        adv = self._card(col, t("adv_title"), row=1, pady=(0, 7))
        ctk.CTkLabel(adv, text=t("adv_desc"),
                     font=fui(10), text_color=MUTED, wraplength=280,
                     ).pack(anchor="w", padx=16, pady=(0, 10))

        pf = ctk.CTkFrame(adv, fg_color="transparent")
        pf.pack(fill="x", padx=14)
        pf.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(pf, text=t("pos_x"), font=fui(10), text_color=MUTED).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(pf, text=t("pos_y"), font=fui(10), text_color=MUTED).grid(row=0, column=1, sticky="w", padx=(6, 0))
        ctk.CTkEntry(pf, textvariable=self.pos_x, placeholder_text="125.5",
                     font=fmono(11), fg_color=INPUT, border_color=BORDER,
                     text_color=TEXT, height=32, corner_radius=6,
                     ).grid(row=1, column=0, sticky="ew", padx=(0, 3))
        ctk.CTkEntry(pf, textvariable=self.pos_y, placeholder_text="110.2",
                     font=fmono(11), fg_color=INPUT, border_color=BORDER,
                     text_color=TEXT, height=32, corner_radius=6,
                     ).grid(row=1, column=1, sticky="ew", padx=(3, 0))

        ctk.CTkLabel(adv, text=t("stl_name"), font=fui(10), text_color=MUTED).pack(
            anchor="w", padx=16, pady=(10, 2))
        ctk.CTkEntry(adv, textvariable=self.stl_name, placeholder_text="model.stl",
                     font=fmono(11), fg_color=INPUT, border_color=BORDER,
                     text_color=TEXT, height=32, corner_radius=6,
                     ).pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkFrame(col, fg_color="transparent").grid(row=2, column=0, sticky="nsew")

        self._run_btn = ctk.CTkButton(
            col, text=t("run_btn"), font=fdisplay(14, "bold"),
            fg_color=ACC_DIM, hover_color=ACC_BTN,
            text_color=TEXT, corner_radius=10, height=52,
            command=self._run,
        )
        self._run_btn.grid(row=3, column=0, sticky="ew", pady=(8, 0))

    # ── Right column (log) ─────────────────────────────────────────────────────

    def _build_col_right(self, parent):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=2, sticky="nsew", padx=(7, 0))
        col.grid_rowconfigure(0, weight=1)
        col.grid_columnconfigure(0, weight=1)

        log = ctk.CTkFrame(col, fg_color=CARD, corner_radius=12,
                           border_width=1, border_color=BORDER)
        log.grid(row=0, column=0, sticky="nsew")
        log.grid_rowconfigure(1, weight=1)
        log.grid_columnconfigure(0, weight=1)

        # Log header
        lh = ctk.CTkFrame(log, fg_color="transparent")
        lh.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 0))
        lh.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(lh, text=t("log_title"), font=fui(9, "bold"), text_color=MUTED).grid(
            row=0, column=0, sticky="w")

        # Right-side log controls
        ctrl = ctk.CTkFrame(lh, fg_color="transparent")
        ctrl.grid(row=0, column=1, sticky="e")

        self._verbose_btn = ctk.CTkButton(
            ctrl, text=t("log_verbose"), font=fui(10),
            text_color=MUTED, fg_color="transparent", hover_color=BORDER,
            width=70, height=22, corner_radius=4,
            command=self._toggle_verbose,
        )
        self._verbose_btn.pack(side="left", padx=(0, 4))

        self._report_btn = ctk.CTkButton(
            ctrl, text=t("log_report"), font=fui(10),
            text_color=ERROR, fg_color="transparent", hover_color=BORDER,
            width=90, height=22, corner_radius=4,
            command=self._report_bug,
        )
        self._report_btn.pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            ctrl, text=t("log_clear"), font=fui(10), text_color=MUTED,
            fg_color="transparent", hover_color=BORDER,
            width=60, height=22, corner_radius=4, command=self._clear_log,
        ).pack(side="left")

        ctk.CTkFrame(log, fg_color=BORDER, height=1, corner_radius=0).grid(
            row=0, column=0, sticky="ews", padx=16)

        self._logbox = ctk.CTkTextbox(
            log, font=fmono(11), fg_color="transparent", text_color=MUTED,
            wrap="word", corner_radius=0, activate_scrollbars=True,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=BDR_HL,
        )
        self._logbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        tb = self._logbox._textbox
        tb.tag_configure("accent",  foreground=ACCENT)
        tb.tag_configure("success", foreground=SUCCESS)
        tb.tag_configure("error",   foreground=ERROR)
        tb.tag_configure("warn",    foreground=WARN)
        tb.tag_configure("muted",   foreground=MUTED)
        tb.tag_configure("verbose", foreground=DIM)

        # Progress area
        pf = ctk.CTkFrame(log, fg_color=CARD_ALT, corner_radius=8)
        pf.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        pf.grid_columnconfigure(0, weight=1)

        ph = ctk.CTkFrame(pf, fg_color="transparent")
        ph.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ph.grid_columnconfigure(0, weight=1)

        self._prog_label = ctk.CTkLabel(ph, text=t("ready"), font=fui(11), text_color=MUTED)
        self._prog_label.grid(row=0, column=0, sticky="w")
        self._prog_pct = ctk.CTkLabel(ph, text="", font=fmono(11), text_color=ACCENT)
        self._prog_pct.grid(row=0, column=1, sticky="e")

        self._pbar = ctk.CTkProgressBar(pf, fg_color=BORDER, progress_color=ACCENT,
                                         corner_radius=4, height=5)
        self._pbar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self._pbar.set(0)

    # ── Verbose toggle ─────────────────────────────────────────────────────────

    def _toggle_verbose(self):
        self._verbose.set(not self._verbose.get())
        active = self._verbose.get()
        self._verbose_btn.configure(
            fg_color=ACC_DIM if active else "transparent",
            text_color=ACCENT if active else MUTED,
        )

    # ── File actions ───────────────────────────────────────────────────────────

    def _pick_gcode(self):
        path = filedialog.askopenfilename(
            title=t("dlg_gcode"),
            filetypes=[("G-code", "*.gcode *.gc *.g"), ("All", "*.*")],
        )
        if path:
            self._set_gcode(path)

    def _on_drop(self, event):
        path = event.data.strip().strip("{}")
        if path.lower().endswith((".gcode", ".gc", ".g")):
            self._set_gcode(path)
        self._dz.configure(border_color=BORDER)

    def _set_gcode(self, path: str):
        self.input_path.set(path)
        name = Path(path).name
        self._fname_label.configure(text=f"📄 {name}", text_color=TEXT)
        self._dz_label.configure(text=name, text_color=ACCENT)

        if self.out_mode.get() == "saveas" and not self.output_path.get():
            p = Path(path)
            self.output_path.set(str(p.parent / f"{p.stem}_upr.gcode"))

        self._log(t("log_loading"), "muted")
        logger.info(f"G-code selected: {path}")
        threading.Thread(target=self._do_analyze, args=(path,), daemon=True).start()
        self._update_run_btn()

    def _do_analyze(self, path: str):
        info = analyze_gcode(path)
        self._gcode_info = info
        self.after(0, self._update_info_labels)

    def _update_info_labels(self):
        i = self._gcode_info
        slicer  = i.get("slicer",       "—")
        layers  = i.get("layers",        0)
        objects = i.get("objects",       0)
        height  = i.get("layer_height", "—")

        self._i_slicer.configure(text=slicer)
        self._i_layers.configure(text=str(layers)  if layers  else "—")
        self._i_objects.configure(text=str(objects) if objects else "—")
        self._i_height.configure(text=height)

        color = SLICER_COLORS.get(slicer, MUTED)
        self._slicer_badge.configure(text=f"  {slicer}  ", text_color=color)
        self._log(t("log_detected", slicer=slicer, layers=layers,
                    objects=objects, height=height), "accent")

    def _pick_models_dir(self):
        path = filedialog.askdirectory(title=t("dlg_models"))
        if path:
            self.models_path.set(path)
            self._update_run_btn()

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title=t("dlg_save"), defaultextension=".gcode",
            filetypes=[("G-code", "*.gcode"), ("All", "*.*")],
        )
        if path:
            self.output_path.set(path)

    def _toggle_out(self):
        is_saveas = self.out_mode.get() == "saveas"
        state = "normal" if is_saveas else "disabled"
        self._out_entry.configure(state=state)
        self._out_btn.configure(state=state)
        if is_saveas and self.input_path.get() and not self.output_path.get():
            p = Path(self.input_path.get())
            self.output_path.set(str(p.parent / f"{p.stem}_upr.gcode"))

    def _update_run_btn(self):
        if self._processing:
            return
        if self.input_path.get():
            self._run_btn.configure(fg_color=ACC_BTN, hover_color=ACCENT, text_color="#000000")
        else:
            self._run_btn.configure(fg_color=ACC_DIM, hover_color=ACC_BTN, text_color=TEXT)

    # ── Run ────────────────────────────────────────────────────────────────────

    def _run(self):
        if self._processing:
            return
        inp = self.input_path.get()
        if not inp:
            self._log(t("warn_no_input"), "warn"); return

        models = self.models_path.get() or None
        out    = self.output_path.get() if self.out_mode.get() == "saveas" else None

        plate_model = None
        if self.pos_x.get() and self.pos_y.get() and self.stl_name.get():
            try:
                plate_model = (self.stl_name.get(),
                               float(self.pos_x.get()), float(self.pos_y.get()))
            except ValueError:
                self._log(t("warn_pos"), "warn"); return

        self._processing = True
        self._last_error = ""
        self._report_btn.configure(state="disabled")
        self._run_btn.configure(text=t("running_btn"), fg_color=BORDER,
                                hover_color=BORDER, text_color=MUTED, state="disabled")
        self._prog_label.configure(text=t("processing"), text_color=MUTED)
        self._pbar.set(0.05)
        self._animate_progress()

        self._log(f"\n{t('log_start', name=Path(inp).name)}", "accent")
        logger.info(f"Run: input={inp} models={models} out={out}")

        threading.Thread(
            target=run_worker,
            args=(inp, models, out, plate_model, self._log_q, self._verbose.get()),
            daemon=True,
        ).start()

    def _animate_progress(self):
        if not self._processing:
            return
        val = self._pbar.get()
        val += 0.018 * self._prog_dir
        if val >= 0.92: self._prog_dir = -1
        elif val <= 0.05: self._prog_dir = 1
        self._pbar.set(val)
        self.after(60, self._animate_progress)

    # ── Bug report ─────────────────────────────────────────────────────────────

    def _report_bug(self):
        slicer = self._gcode_info.get("slicer", t("unknown"))
        threading.Thread(
            target=open_bug_report,
            args=(self._last_error, slicer, self),
            daemon=True,
        ).start()

    # ── Log helpers ────────────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = "muted"):
        tb = self._logbox._textbox
        tb.configure(state="normal")
        tb.insert("end", msg + "\n", tag)
        tb.configure(state="disabled")
        tb.see("end")

    def _clear_log(self):
        tb = self._logbox._textbox
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.configure(state="disabled")

    # ── Queue poller ───────────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                item = self._log_q.get_nowait()
                kind = item[0]

                if kind == "log":
                    _, msg, is_verbose = item
                    if is_verbose and not self._verbose.get():
                        pass  # suppress in compact mode
                    else:
                        tag = "verbose" if is_verbose else "muted"
                        self._log(f"  {msg}", tag)

                elif kind == "done":
                    _, msg = item
                    self._processing = False
                    self._prog_dir = 1
                    self._pbar.set(1.0)
                    self._prog_label.configure(text=t("done_status"), text_color=SUCCESS)
                    self._log(f"\n✓ {msg}\n", "success")
                    self._run_btn.configure(text=t("run_btn"), state="normal")
                    self._update_run_btn()

                elif kind == "error":
                    _, msg = item
                    self._processing = False
                    self._last_error = msg
                    self._prog_dir = 1
                    self._pbar.set(0)
                    self._prog_label.configure(text=t("err_status"), text_color=ERROR)
                    self._log(f"\n{t('log_err', msg=msg)}\n", "error")
                    self._run_btn.configure(text=t("run_btn"), state="normal")
                    self._update_run_btn()

        except queue.Empty:
            pass
        self.after(100, self._poll)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
