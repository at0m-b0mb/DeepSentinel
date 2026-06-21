"""Rich report generation — self-contained HTML + PDF forensic reports.

Produces a shareable report embedding the verdict, every method score,
forensic visualizations (as inline base64 images), EXIF metadata, optional
temporal/heatmap results, and the educational disclaimer.

HTML is fully self-contained (no external assets). PDF is rendered through
Qt's QTextDocument → QPrinter, so the layout uses the rich-text CSS subset.
"""

import os
import base64
import datetime
import cv2
import numpy as np


# ── Colours (match the app theme) ──────────────────────────────────────────────
_VERDICT_COLORS = {
    "REAL":       "#10b981",
    "SUSPICIOUS": "#f59e0b",
    "DEEPFAKE":   "#f43f5e",
}


def _img_to_data_uri(bgr: np.ndarray, max_w: int = 360) -> str:
    """Encode a BGR image as a base64 PNG data URI."""
    if bgr is None:
        return ""
    h, w = bgr.shape[:2]
    if w > max_w:
        scale = max_w / w
        bgr = cv2.resize(bgr, (max_w, int(h * scale)))
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        return ""
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _bar(label: str, score: float) -> str:
    """One score row as an HTML table for the rich-text engine."""
    if score < 0:
        pct_txt, color, width = "N/A", "#505070", 0
    else:
        pct = int(score * 100)
        color = ("#f43f5e" if score >= 0.65 else
                 "#f59e0b" if score >= 0.40 else "#10b981")
        pct_txt, width = f"{pct}%", pct
    return f"""
      <tr>
        <td style="color:#9090b8; font-size:12px; padding:4px 8px; width:140px;">{label}</td>
        <td style="padding:4px 8px;">
          <table cellpadding="0" cellspacing="0" style="width:100%; background:#10101e; border-radius:4px;">
            <tr><td style="background:{color}; height:9px; width:{width}%; border-radius:4px;"></td>
                <td style="width:{100-width}%;"></td></tr>
          </table>
        </td>
        <td style="color:{color}; font-family:monospace; font-size:12px; font-weight:bold;
                   text-align:right; padding:4px 8px; width:48px;">{pct_txt}</td>
      </tr>"""


def build_html_report(
    result,
    file_path: str | None = None,
    viz_frames: dict | None = None,
    exif: dict | None = None,
    exif_flags: list | None = None,
    temporal=None,
    heatmap_bgr: np.ndarray | None = None,
    preview_bgr: np.ndarray | None = None,
) -> str:
    """Build a complete self-contained HTML report string."""
    vc = _VERDICT_COLORS.get(result.label, "#9090b8")
    fname = os.path.basename(file_path) if file_path else "Live Snapshot"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Score rows ──
    score_rows = (
        _bar("FFT Artifacts", result.fft_score) +
        _bar("ELA Forensics", result.ela_score) +
        _bar("Face Geometry", result.face_score) +
        _bar("Noise Pattern", result.noise_score) +
        _bar("MesoNet (NN)", result.mesonet_score)
    )

    # ── Preview + heatmap ──
    media_cells = ""
    if preview_bgr is not None:
        media_cells += f"""
          <td align="center" style="padding:6px;">
            <div style="color:#00d4ff; font-size:10px; font-weight:bold; padding-bottom:4px;">SOURCE</div>
            <img src="{_img_to_data_uri(preview_bgr, 300)}" style="border-radius:8px; border:1px solid #20203a;"/>
          </td>"""
    if heatmap_bgr is not None:
        media_cells += f"""
          <td align="center" style="padding:6px;">
            <div style="color:#f43f5e; font-size:10px; font-weight:bold; padding-bottom:4px;">SUSPICION HEATMAP</div>
            <img src="{_img_to_data_uri(heatmap_bgr, 300)}" style="border-radius:8px; border:1px solid #20203a;"/>
          </td>"""
    media_block = f'<table cellspacing="0" cellpadding="0"><tr>{media_cells}</tr></table>' if media_cells else ""

    # ── Forensic viz strip ──
    viz_block = ""
    if viz_frames:
        cells = ""
        for title, frame in viz_frames.items():
            uri = _img_to_data_uri(frame, 220)
            if uri:
                cells += f"""
                  <td align="center" valign="top" style="padding:6px;">
                    <div style="color:#0099cc; font-size:9px; font-weight:bold; padding-bottom:3px;">{title.upper()}</div>
                    <img src="{uri}" width="200" style="border-radius:6px; border:1px solid #20203a;"/>
                  </td>"""
        viz_block = f"""
        <h3 style="color:#00d4ff; font-size:13px; letter-spacing:2px; border-bottom:1px solid #20203a; padding-bottom:6px;">FORENSIC VISUALIZATIONS</h3>
        <table cellspacing="0" cellpadding="0"><tr>{cells}</tr></table>"""

    # ── EXIF block ──
    exif_block = ""
    if exif:
        rows = ""
        for k, v in exif.items():
            if k.startswith("_"):
                continue
            rows += f"""<tr>
                <td style="color:#505070; font-size:11px; padding:2px 10px 2px 0; width:140px;">{k}</td>
                <td style="color:#9090b8; font-size:11px; font-family:monospace;">{v}</td></tr>"""
        flag_html = ""
        if exif_flags:
            flag_items = "".join(f'<div style="color:#f59e0b; font-size:11px;">{f}</div>' for f in exif_flags)
            flag_html = f'<div style="margin-bottom:8px;">{flag_items}</div>'
        exif_block = f"""
        <h3 style="color:#00d4ff; font-size:13px; letter-spacing:2px; border-bottom:1px solid #20203a; padding-bottom:6px;">METADATA</h3>
        {flag_html}
        <table cellspacing="0" cellpadding="0">{rows}</table>"""

    # ── Temporal block ──
    temporal_block = ""
    if temporal is not None and temporal.frames_analyzed > 0:
        tc = _VERDICT_COLORS.get(temporal.label, "#9090b8")
        notes = "".join(f'<li style="color:#9090b8; font-size:11px;">{n}</li>' for n in temporal.notes)
        temporal_block = f"""
        <h3 style="color:#00d4ff; font-size:13px; letter-spacing:2px; border-bottom:1px solid #20203a; padding-bottom:6px;">TEMPORAL VIDEO ANALYSIS</h3>
        <table cellspacing="0" cellpadding="6" style="font-size:12px;">
          <tr>
            <td style="color:#505070;">Temporal Verdict</td>
            <td style="color:{tc}; font-weight:bold;">{temporal.label} ({temporal.temporal_score*100:.0f}%)</td>
            <td style="color:#505070; padding-left:24px;">Frames Analyzed</td>
            <td style="color:#9090b8; font-family:monospace;">{temporal.frames_analyzed}</td>
          </tr>
          <tr>
            <td style="color:#505070;">Mean / Peak Score</td>
            <td style="color:#9090b8; font-family:monospace;">{temporal.mean_score:.2f} / {temporal.peak_score:.2f}</td>
            <td style="color:#505070; padding-left:24px;">Duration</td>
            <td style="color:#9090b8; font-family:monospace;">{temporal.duration_s:.1f}s</td>
          </tr>
          <tr>
            <td style="color:#505070;">Blink Rate</td>
            <td style="color:{'#f43f5e' if temporal.blink_flag else '#9090b8'}; font-family:monospace;">
                {temporal.blink_rate:.1f}/min ({temporal.blink_count} blinks)</td>
            <td style="color:#505070; padding-left:24px;">Flicker</td>
            <td style="color:#9090b8; font-family:monospace;">{temporal.flicker_score:.2f}</td>
          </tr>
        </table>
        <ul style="margin-top:4px;">{notes}</ul>"""

    # ── Assemble ──
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>DeepSentinel Report — {fname}</title></head>
<body style="background:#06060f; color:#f0f0ff; font-family:'Helvetica Neue',Arial,sans-serif; margin:0; padding:28px;">
  <table cellspacing="0" cellpadding="0" style="width:100%; max-width:760px; margin:0 auto;">
    <!-- Header -->
    <tr><td>
      <table cellspacing="0" cellpadding="0" style="width:100%; border-bottom:2px solid #00d4ff; padding-bottom:12px;">
        <tr>
          <td><span style="color:#00d4ff; font-size:26px; font-weight:900; letter-spacing:4px;">DEEP</span><span style="color:#e8e8ff; font-size:26px; font-weight:300; letter-spacing:4px;">SENTINEL</span>
              <div style="color:#505070; font-size:11px; letter-spacing:1px;">Deepfake Forensic Analysis Report</div></td>
          <td align="right" style="color:#505070; font-size:11px; font-family:monospace;">
              {now}<br/>{fname}</td>
        </tr>
      </table>
    </td></tr>

    <!-- Verdict banner -->
    <tr><td style="padding-top:18px;">
      <table cellspacing="0" cellpadding="0" style="width:100%; background:#0d0d1b; border:1px solid {vc}; border-radius:12px;">
        <tr>
          <td style="padding:18px 24px;">
            <div style="color:#505070; font-size:11px; letter-spacing:2px;">VERDICT</div>
            <div style="color:{vc}; font-size:34px; font-weight:900; letter-spacing:3px;">{result.label}</div>
          </td>
          <td align="right" style="padding:18px 24px;">
            <div style="color:#505070; font-size:11px; letter-spacing:2px;">DEEPFAKE SCORE</div>
            <div style="color:{vc}; font-size:34px; font-weight:900; font-family:monospace;">{result.overall_score*100:.0f}%</div>
          </td>
        </tr>
      </table>
    </td></tr>

    {f'<tr><td style="padding-top:18px;">{media_block}</td></tr>' if media_block else ''}

    <!-- Scores -->
    <tr><td style="padding-top:20px;">
      <h3 style="color:#00d4ff; font-size:13px; letter-spacing:2px; border-bottom:1px solid #20203a; padding-bottom:6px;">METHOD SCORES</h3>
      <table cellspacing="0" cellpadding="0" style="width:100%;">{score_rows}</table>
      <div style="color:#505070; font-size:11px; padding-top:6px;">
        Faces detected: {result.faces_found} &nbsp;·&nbsp; Methods used: {result.methods_used}
      </div>
    </td></tr>

    {f'<tr><td style="padding-top:20px;">{temporal_block}</td></tr>' if temporal_block else ''}
    {f'<tr><td style="padding-top:20px;">{viz_block}</td></tr>' if viz_block else ''}
    {f'<tr><td style="padding-top:20px;">{exif_block}</td></tr>' if exif_block else ''}

    <!-- Disclaimer -->
    <tr><td style="padding-top:24px;">
      <table cellspacing="0" cellpadding="0" style="width:100%; background:#1a1206; border:1px solid #f59e0b44; border-radius:8px;">
        <tr><td style="padding:12px 16px;">
          <span style="color:#f59e0b; font-size:12px; font-weight:bold;">⚠ FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY</span>
          <div style="color:#9090b8; font-size:11px; padding-top:4px;">
            Heuristic detection is not 100% reliable and can produce false positives and
            false negatives. State-of-the-art synthetic media may evade all methods shown
            here. Never treat this report as definitive proof. Always corroborate with
            additional tools and expert human judgment.
          </div>
        </td></tr>
      </table>
    </td></tr>

    <tr><td align="center" style="padding-top:18px; color:#2a2a45; font-size:10px; font-family:monospace;">
      DeepSentinel v1.0 · github.com/at0m-b0mb/DeepSentinel · "See through the synthetic."
    </td></tr>
  </table>
</body></html>"""
    return html


def export_html(html: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def export_pdf(html: str, path: str) -> bool:
    """Render the HTML report to PDF via Qt's rich-text engine."""
    try:
        from PyQt6.QtGui import QTextDocument, QPageSize
        from PyQt6.QtPrintSupport import QPrinter
        from PyQt6.QtCore import QSizeF, QMarginsF
        from PyQt6.QtGui import QPageLayout

        doc = QTextDocument()
        doc.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))

        doc.setPageSize(QSizeF(printer.pageRect(QPrinter.Unit.DevicePixel).size()))
        doc.print(printer)
        return True
    except Exception as e:
        print(f"PDF export failed: {e}")
        return False
