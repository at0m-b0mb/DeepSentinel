"""Custom painted widgets for DeepSentinel — arc gauges, history graphs, stat cards."""

import math
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QLinearGradient, QPainterPath,
    QRadialGradient, QConicalGradient, QBrush,
)

from .theme import (
    CYAN, CYAN_MID, CYAN_DIM, GREEN, GREEN_LO, RED, RED_DIM,
    AMBER, PURPLE, BG_CARD, BG_CARD2, BG_HOVER, BG_DEEP, BG_VOID,
    BORDER_MID, BORDER_HI, TEXT_HI, TEXT_MID, TEXT_LO, TEXT_DIM,
    FONT_MONO, FONT_UI,
)


def _score_qcolor(score: float) -> QColor:
    if score >= 0.65:
        return QColor(RED)
    elif score >= 0.40:
        return QColor(AMBER)
    return QColor(GREEN)


def glow_effect(widget: QWidget, color: str = CYAN, radius: int = 20):
    fx = QGraphicsDropShadowEffect(widget)
    fx.setBlurRadius(radius)
    fx.setColor(QColor(color + "50"))
    fx.setOffset(0, 0)
    widget.setGraphicsEffect(fx)
    return fx


# ── Confidence Arc Dial ────────────────────────────────────────────────────────

class ConfidenceDial(QWidget):
    """
    Animated semicircular arc gauge.
    Fills left → right with animated ease-out; color tracks risk level.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._target = 0.0
        self._label = "AWAITING INPUT"
        self._pct_text = "—%"
        self._color = QColor(TEXT_LO)

        self._timer = QTimer(self)
        self._timer.setInterval(14)
        self._timer.timeout.connect(self._step)

        self.setMinimumSize(240, 155)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_value(self, value: float, label: str = ""):
        self._target = max(0.0, min(1.0, value))
        if label:
            self._label = label.upper()
        self._pct_text = f"{int(self._target * 100)}%"
        self._color = _score_qcolor(self._target)
        if not self._timer.isActive():
            self._timer.start()

    def reset(self):
        self._target = 0.0
        self._label = "AWAITING INPUT"
        self._pct_text = "—%"
        self._color = QColor(TEXT_LO)
        if not self._timer.isActive():
            self._timer.start()

    def _step(self):
        diff = self._target - self._value
        if abs(diff) < 0.003:
            self._value = self._target
            self._timer.stop()
        else:
            self._value += diff * 0.11
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        pad = 22
        r = min(w / 2 - pad, h - 38)
        cx = w / 2
        cy = h - 14

        rect = QRectF(cx - r, cy - r, r * 2, r * 2)

        # Track shadow
        shadow_pen = QPen(QColor("#05050c"), 22)
        shadow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(shadow_pen)
        p.drawArc(rect.adjusted(-2, -2, 2, 2), 180 * 16, -180 * 16)

        # Background track
        track_pen = QPen(QColor("#12122a"), 16)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(track_pen)
        p.drawArc(rect, 180 * 16, -180 * 16)

        v = self._value
        if v > 0.005:
            span = int(-v * 180) * 16

            # Glow pass (wider, transparent)
            glow_color = QColor(self._color)
            glow_color.setAlpha(50)
            glow_pen = QPen(glow_color, 26)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(glow_pen)
            p.drawArc(rect, 180 * 16, span)

            # Main arc with gradient
            c = self._color
            grad = QConicalGradient(cx, cy, 0)
            grad.setColorAt(0.0, c)
            grad.setColorAt(0.25, c.lighter(120))
            grad.setColorAt(1.0, c.darker(130))
            arc_pen = QPen(QBrush(grad), 14)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(arc_pen)
            p.drawArc(rect, 180 * 16, span)

            # Endpoint dot (bright tip)
            end_angle = math.radians(180.0 - v * 180.0)
            ex = cx + r * math.cos(end_angle)
            ey = cy - r * math.sin(end_angle)
            tip_color = QColor(self._color)
            tip_color.setAlpha(255)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(TEXT_HI))
            p.drawEllipse(QPointF(ex, ey), 5, 5)
            p.setBrush(tip_color)
            p.drawEllipse(QPointF(ex, ey), 3, 3)

        # Tick marks
        p.setPen(QPen(QColor(BORDER_MID), 1))
        for deg in range(0, 181, 18):
            angle = math.radians(180 - deg)
            ix = cx + (r - 10) * math.cos(angle)
            iy = cy - (r - 10) * math.sin(angle)
            ox = cx + (r + 4) * math.cos(angle)
            oy = cy - (r + 4) * math.sin(angle)
            p.drawLine(QPointF(ix, iy), QPointF(ox, oy))

        # Percentage text
        p.setPen(self._color)
        f_pct = QFont()
        f_pct.setFamily("JetBrains Mono, Menlo, monospace")
        f_pct.setPointSize(28)
        f_pct.setBold(True)
        p.setFont(f_pct)
        p.drawText(QRectF(0, cy - r * 0.72, w, r * 0.55),
                   Qt.AlignmentFlag.AlignCenter, self._pct_text)

        # Label text
        p.setPen(QColor(TEXT_LO))
        f_lbl = QFont()
        f_lbl.setFamily("SF Pro Display, Helvetica, sans-serif")
        f_lbl.setPointSize(8)
        f_lbl.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
        f_lbl.setBold(True)
        p.setFont(f_lbl)
        p.drawText(QRectF(0, cy - r * 0.2, w, 18),
                   Qt.AlignmentFlag.AlignCenter, self._label)


# ── Real-Time History Graph ────────────────────────────────────────────────────

class HistoryGraph(QWidget):
    """Painted real-time line chart for confidence history."""

    MAX_POINTS = 90

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[float] = []
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._threshold = 0.65

    def push(self, value: float):
        self._data.append(max(0.0, min(1.0, value)))
        if len(self._data) > self.MAX_POINTS:
            self._data.pop(0)
        self.update()

    def clear(self):
        self._data.clear()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        pl, pr, pt, pb = 10, 10, 8, 6
        gh = h - pt - pb

        # Background
        p.setBrush(QColor("#0a0a15"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), 8, 8)

        # Grid
        grid_pen = QPen(QColor("#14142a"), 1, Qt.PenStyle.DotLine)
        p.setPen(grid_pen)
        for frac in [0.25, 0.5, 0.75]:
            y = pt + (1 - frac) * gh
            p.drawLine(QPointF(pl, y), QPointF(w - pr, y))

        # Threshold line
        thr_y = pt + (1 - self._threshold) * gh
        thr_pen = QPen(QColor("#f43f5e44"), 1, Qt.PenStyle.DashLine)
        p.setPen(thr_pen)
        p.drawLine(QPointF(pl, thr_y), QPointF(w - pr, thr_y))

        n = len(self._data)
        if n < 2:
            p.setPen(QColor(TEXT_DIM))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Confidence history will appear here…")
            return

        def pt_from_idx(i: int) -> QPointF:
            x = pl + (i / (self.MAX_POINTS - 1)) * (w - pl - pr)
            y = pt + (1.0 - self._data[i]) * gh
            return QPointF(x, y)

        # Gradient fill
        path = QPainterPath()
        p0 = pt_from_idx(0)
        path.moveTo(p0.x(), h - pb)
        for i in range(n):
            path.lineTo(pt_from_idx(i))
        last = pt_from_idx(n - 1)
        path.lineTo(last.x(), h - pb)
        path.closeSubpath()

        v_last = self._data[-1]
        if v_last >= 0.65:
            top_c = QColor(244, 63, 94, 80)
        elif v_last >= 0.40:
            top_c = QColor(245, 158, 11, 80)
        else:
            top_c = QColor(16, 185, 129, 80)

        grad = QLinearGradient(0, pt, 0, h - pb)
        grad.setColorAt(0, top_c)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillPath(path, QBrush(grad))

        # Line
        line_color = _score_qcolor(v_last)
        line_pen = QPen(line_color, 2, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(line_pen)
        for i in range(n - 1):
            p.drawLine(pt_from_idx(i), pt_from_idx(i + 1))

        # Current-value dot
        lp = pt_from_idx(n - 1)
        p.setBrush(line_color)
        p.setPen(QPen(QColor(BG_CARD), 2))
        p.drawEllipse(lp, 5, 5)


# ── Gradient Score Bar ─────────────────────────────────────────────────────────

class GlowScoreBar(QWidget):
    """Score bar with gradient fill, glow, label, and percentage."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._value = -1.0
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_score(self, score: float):
        self._value = score
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        label_w = 140
        pct_w = 42
        bar_x = label_w + 6
        bar_w = w - label_w - pct_w - 12
        bar_h = 8
        bar_y = (h - bar_h) / 2

        # Label
        p.setPen(QColor(TEXT_MID))
        f = QFont()
        f.setFamily("SF Pro Display, Helvetica, sans-serif")
        f.setPointSize(11)
        p.setFont(f)
        p.drawText(QRectF(0, 0, label_w, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)

        # Track
        track_rect = QRectF(bar_x, bar_y, bar_w, bar_h)
        p.setBrush(QColor("#10101e"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(track_rect, bar_h / 2, bar_h / 2)

        if self._value < 0:
            # N/A
            p.setPen(QColor(TEXT_DIM))
            f2 = QFont(); f2.setFamily("JetBrains Mono, monospace"); f2.setPointSize(10)
            p.setFont(f2)
            p.drawText(QRectF(w - pct_w, 0, pct_w, h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "N/A")
            return

        # Fill
        fill_w = max(bar_h, self._value * bar_w)
        fill_rect = QRectF(bar_x, bar_y, fill_w, bar_h)

        c = _score_qcolor(self._value)
        c2 = c.lighter(140)
        grad = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
        grad.setColorAt(0, c.darker(120))
        grad.setColorAt(1, c2)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(fill_rect, bar_h / 2, bar_h / 2)

        # Glow overlay
        glow_c = QColor(c)
        glow_c.setAlpha(40)
        glow_rect = QRectF(bar_x, bar_y - 2, fill_w, bar_h + 4)
        p.setBrush(QBrush(glow_c))
        p.drawRoundedRect(glow_rect, (bar_h + 4) / 2, (bar_h + 4) / 2)

        # Percentage
        pct = int(self._value * 100)
        p.setPen(c if self._value > 0.1 else QColor(TEXT_LO))
        f3 = QFont(); f3.setFamily("JetBrains Mono, monospace"); f3.setPointSize(10); f3.setBold(True)
        p.setFont(f3)
        p.drawText(QRectF(w - pct_w, 0, pct_w, h),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{pct}%")


# ── Stat Card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """Dashboard stat card: icon + big value + label."""

    def __init__(self, icon: str, value: str, label: str, accent: str = CYAN, parent=None):
        super().__init__(parent)
        self._accent = accent
        self.setObjectName("card")
        self.setMinimumSize(140, 100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 22px; color: {accent};")
        layout.addWidget(icon_lbl)
        layout.addStretch()

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"color: {accent}; font-size: 28px; font-weight: 900; "
            f"font-family: 'JetBrains Mono', monospace; letter-spacing: -1px;"
        )
        layout.addWidget(self.value_lbl)

        self.label_lbl = QLabel(label.upper())
        self.label_lbl.setStyleSheet(
            f"color: {TEXT_LO}; font-size: 9px; font-weight: 800; letter-spacing: 2px;"
        )
        layout.addWidget(self.label_lbl)

    def set_value(self, v: str):
        self.value_lbl.setText(v)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Left accent stripe
        c = QColor(self._accent)
        c.setAlpha(180)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 16, 3, self.height() - 32), 2, 2)


# ── Pulsing Live Indicator ─────────────────────────────────────────────────────

class PulsingDot(QWidget):
    """Animated pulsing circle for LIVE indicator."""

    def __init__(self, color: str = GREEN, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._pulse = 0.0
        self._growing = True
        self._active = False

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._step)

        self.setFixedSize(16, 16)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def start(self):
        self._active = True
        self._timer.start()

    def stop(self):
        self._active = False
        self._timer.stop()
        self._pulse = 0.0
        self.update()

    def _step(self):
        step = 0.04
        if self._growing:
            self._pulse += step
            if self._pulse >= 1.0:
                self._pulse = 1.0
                self._growing = False
        else:
            self._pulse -= step
            if self._pulse <= 0.0:
                self._pulse = 0.0
                self._growing = True
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        r_inner = 4.0

        if self._active:
            # Outer pulse ring
            outer_r = r_inner + self._pulse * 5
            ring = QColor(self._color)
            ring.setAlpha(int((1.0 - self._pulse) * 140))
            p.setBrush(QBrush(ring))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), outer_r, outer_r)

            # Inner solid dot
            p.setBrush(self._color)
            p.drawEllipse(QPointF(cx, cy), r_inner, r_inner)
        else:
            # Dim static dot
            dim = QColor(self._color)
            dim.setAlpha(80)
            p.setBrush(dim)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), r_inner - 1, r_inner - 1)


# ── History Log Row ───────────────────────────────────────────────────────────

class HistoryRow(QWidget):
    """Single row in the session history list."""

    def __init__(self, timestamp: str, filename: str, verdict: str,
                 score: float, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        colors = {"REAL": GREEN, "SUSPICIOUS": AMBER, "DEEPFAKE": RED}
        color = colors.get(verdict, TEXT_MID)

        time_lbl = QLabel(timestamp)
        time_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-family: monospace; min-width: 52px;")
        layout.addWidget(time_lbl)

        name_lbl = QLabel(filename[:38] + "…" if len(filename) > 38 else filename)
        name_lbl.setStyleSheet(f"color: {TEXT_MID}; font-size: 12px;")
        name_lbl.setToolTip(filename)
        layout.addWidget(name_lbl, 1)

        verdict_lbl = QLabel(verdict)
        verdict_lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 800; letter-spacing: 1.5px; "
            f"background: {color}20; border-radius: 4px; padding: 2px 6px;"
        )
        verdict_lbl.setFixedWidth(90)
        verdict_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(verdict_lbl)

        score_lbl = QLabel(f"{score * 100:.0f}%")
        score_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-family: monospace; font-weight: 700; min-width: 36px;")
        score_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(score_lbl)

        self.setStyleSheet(
            f"background: transparent; border-bottom: 1px solid {BORDER_MID};"
        )


# ── Temporal Timeline Graph ────────────────────────────────────────────────────

class TimelineGraph(QWidget):
    """Static painted timeline of (timestamp, score) points for video analysis.

    Unlike HistoryGraph (which scrolls live), this renders a full series at once
    with a time axis, threshold bands, and verdict-coloured fill.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: list[tuple[float, float]] = []
        self._duration = 0.0
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_series(self, series: list[tuple[float, float]], duration: float = 0.0):
        self._series = series or []
        self._duration = duration or (series[-1][0] if series else 0.0)
        self.update()

    def clear(self):
        self._series = []
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pl, pr, pt, pb = 36, 12, 14, 22
        gw = w - pl - pr
        gh = h - pt - pb

        # Background
        p.setBrush(QColor("#0a0a15"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), 8, 8)

        # Threshold bands (REAL / SUSPICIOUS / DEEPFAKE)
        for lo, hi, col in [(0.0, 0.40, QColor(16, 185, 129, 16)),
                            (0.40, 0.65, QColor(245, 158, 11, 16)),
                            (0.65, 1.0, QColor(244, 63, 94, 18))]:
            y_top = pt + (1 - hi) * gh
            band_h = (hi - lo) * gh
            p.fillRect(QRectF(pl, y_top, gw, band_h), col)

        # Y grid + labels
        f_axis = QFont(); f_axis.setFamily("JetBrains Mono, monospace"); f_axis.setPointSize(7)
        p.setFont(f_axis)
        for frac in [0.0, 0.40, 0.65, 1.0]:
            y = pt + (1 - frac) * gh
            p.setPen(QPen(QColor("#18182c"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(pl, y), QPointF(w - pr, y))
            p.setPen(QColor(TEXT_DIM))
            p.drawText(QRectF(0, y - 7, pl - 5, 14),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f"{int(frac*100)}")

        if len(self._series) < 2:
            p.setPen(QColor(TEXT_DIM))
            p.setFont(QFont())
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Load a video and analyze to see the per-frame timeline")
            return

        dur = self._duration or self._series[-1][0] or 1.0

        def to_pt(ts: float, score: float) -> QPointF:
            x = pl + (ts / dur) * gw
            y = pt + (1.0 - max(0.0, min(1.0, score))) * gh
            return QPointF(x, y)

        # Area fill
        path = QPainterPath()
        path.moveTo(to_pt(self._series[0][0], 0).x(), pt + gh)
        for ts, sc in self._series:
            path.lineTo(to_pt(ts, sc))
        path.lineTo(to_pt(self._series[-1][0], 0).x(), pt + gh)
        path.closeSubpath()
        grad = QLinearGradient(0, pt, 0, pt + gh)
        grad.setColorAt(0, QColor(0, 212, 255, 70))
        grad.setColorAt(1, QColor(0, 212, 255, 0))
        p.fillPath(path, QBrush(grad))

        # Line with per-segment colour
        for i in range(len(self._series) - 1):
            ts0, sc0 = self._series[i]
            ts1, sc1 = self._series[i + 1]
            seg_c = _score_qcolor((sc0 + sc1) / 2)
            p.setPen(QPen(seg_c, 2, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawLine(to_pt(ts0, sc0), to_pt(ts1, sc1))

        # Point dots
        for ts, sc in self._series:
            p.setBrush(_score_qcolor(sc))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(to_pt(ts, sc), 2.5, 2.5)

        # X axis time labels
        p.setPen(QColor(TEXT_DIM))
        p.setFont(f_axis)
        for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
            x = pl + frac * gw
            t = frac * dur
            p.drawText(QRectF(x - 20, h - pb + 3, 40, 14),
                       Qt.AlignmentFlag.AlignCenter, f"{t:.1f}s")
