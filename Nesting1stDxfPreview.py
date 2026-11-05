"""Fast DXF preview for the offcut library (no FreeCAD import, a few ms).

Reads LINE, ARC, CIRCLE, LWPOLYLINE (with bulges) and POLYLINE/VERTEX from
the ENTITIES section, joins the segments into closed loops and draws them
filled (holes stay empty) with the overall size.
"""
import math
import os

from PySide import QtCore, QtGui

_cache = {}


def _pairs(path):
    with open(path, "r", errors="replace") as handle:
        lines = handle.read().splitlines()
    for k in range(0, len(lines) - 1, 2):
        yield lines[k].strip(), lines[k + 1].strip()


def _arc_points(cx, cy, r, a0, a1, step_deg=6.0):
    if a1 < a0:
        a1 += 360.0
    n = max(2, int(math.ceil((a1 - a0) / step_deg)) + 1)
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]


def _bulge_points(p, q, bulge):
    if abs(bulge) < 1e-9:
        return [p, q]
    ang = 4.0 * math.atan(bulge)
    dx, dy = q[0] - p[0], q[1] - p[1]
    chord = math.hypot(dx, dy)
    if chord < 1e-9:
        return [p, q]
    r = chord / (2.0 * math.sin(abs(ang) / 2.0))
    mx, my = (p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0
    h = math.sqrt(max(0.0, r * r - (chord / 2.0) ** 2))
    sign = 1.0 if bulge > 0 else -1.0
    if abs(ang) > math.pi:
        h = -h
    cx, cy = mx - sign * h * dy / chord, my + sign * h * dx / chord
    a0 = math.atan2(p[1] - cy, p[0] - cx)
    n = max(2, int(abs(ang) / math.radians(6.0)) + 1)
    return [(cx + r * math.cos(a0 + ang * i / (n - 1)), cy + r * math.sin(a0 + ang * i / (n - 1))) for i in range(n)]


def _entities(path):
    """[(type, [(code, value), ...]), ...] of the ENTITIES section."""
    ents, cur, inside, expect_name = [], None, False, False
    for code, value in _pairs(path):
        if code == "0":
            if cur is not None:
                ents.append(cur)
                cur = None
            if value == "SECTION":
                expect_name = True
                continue
            if value == "ENDSEC":
                inside = False
                continue
            if inside:
                cur = (value, [])
            continue
        if expect_name and code == "2":
            inside = (value == "ENTITIES")
            expect_name = False
            continue
        if cur is not None:
            cur[1].append((code, value))
    if cur is not None:
        ents.append(cur)
    return ents


def _get(items, code, default=None):
    for c, v in items:
        if c == code:
            return float(v)
    return default


def _vertices(items):
    """LWPOLYLINE vertices as [x, y, bulge]."""
    out = []
    for c, v in items:
        if c == "10":
            out.append([float(v), 0.0, 0.0])
        elif c == "20" and out:
            out[-1][1] = float(v)
        elif c == "42" and out:
            out[-1][2] = float(v)
    return out


def _poly_points(v, closed):
    pts = []
    n = len(v) if closed else len(v) - 1
    for i in range(n):
        a, b = v[i], v[(i + 1) % len(v)]
        seg = _bulge_points((a[0], a[1]), (b[0], b[1]), a[2])
        pts.extend(seg if not pts else seg[1:])
    return pts


def read_polylines(path):
    """Open/closed polylines of the drawing, as lists of (x, y)."""
    out = []
    ents = _entities(path)
    k = 0
    while k < len(ents):
        kind, items = ents[k]
        k += 1
        try:
            if kind == "LINE":
                out.append([(_get(items, "10"), _get(items, "20")), (_get(items, "11"), _get(items, "21"))])
            elif kind == "ARC":
                out.append(_arc_points(_get(items, "10"), _get(items, "20"), _get(items, "40"),
                                       _get(items, "50"), _get(items, "51")))
            elif kind == "CIRCLE":
                out.append(_arc_points(_get(items, "10"), _get(items, "20"), _get(items, "40"), 0.0, 360.0))
            elif kind == "LWPOLYLINE":
                v = _vertices(items)
                if len(v) >= 2:
                    out.append(_poly_points(v, bool(int(_get(items, "70", 0)) & 1)))
            elif kind == "POLYLINE":
                closed = bool(int(_get(items, "70", 0)) & 1)
                v = []
                while k < len(ents) and ents[k][0] == "VERTEX":
                    it = ents[k][1]
                    v.append([_get(it, "10", 0.0), _get(it, "20", 0.0), _get(it, "42", 0.0)])
                    k += 1
                if k < len(ents) and ents[k][0] == "SEQEND":
                    k += 1
                if len(v) >= 2:
                    out.append(_poly_points(v, closed))
        except (TypeError, ValueError):
            continue
    return out


def join_loops(polylines, tol=0.05):
    """Join loose segments end to end into loops."""
    def key(p):
        return (round(p[0] / tol), round(p[1] / tol))
    loops, open_ = [], []
    for pl in polylines:
        if len(pl) > 2 and math.dist(pl[0], pl[-1]) <= tol:
            loops.append(pl)
        else:
            open_.append(list(pl))
    ends = {}
    for i, pl in enumerate(open_):
        ends.setdefault(key(pl[0]), []).append((i, 0))
        ends.setdefault(key(pl[-1]), []).append((i, 1))
    used = [False] * len(open_)
    for i in range(len(open_)):
        if used[i]:
            continue
        used[i] = True
        chain = list(open_[i])
        while True:
            k = key(chain[-1])
            nxt = None
            for j, side in ends.get(k, []):
                if not used[j]:
                    nxt = (j, side)
                    break
            if nxt is None:
                break
            j, side = nxt
            used[j] = True
            seg = open_[j] if side == 0 else list(reversed(open_[j]))
            chain.extend(seg[1:])
            if math.dist(chain[0], chain[-1]) <= tol:
                break
        loops.append(chain)
    return loops


def load(path):
    """(loops, bbox) of a DXF, remembered while the file is unchanged."""
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return [], None
    hit = _cache.get(path)
    if hit and hit[0] == stamp:
        return hit[1], hit[2]
    try:
        loops = join_loops(read_polylines(path))
    except Exception:
        loops = []
    pts = [p for loop in loops for p in loop]
    box = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) if pts else None
    if len(_cache) > 60:
        _cache.clear()
    _cache[path] = (stamp, loops, box)
    return loops, box


class OffcutPreview(QtGui.QWidget):
    """Filled drawing of the selected offcut with its size."""

    def __init__(self, parent=None):
        super(OffcutPreview, self).__init__(parent)
        self.setMinimumSize(300, 260)
        self.loops, self.box, self.text = [], None, ""

    def set_path(self, path, info=""):
        self.loops, self.box = load(path) if path else ([], None)
        size = ""
        if self.box:
            size = "%s x %s mm" % (("%.0f" % (self.box[2] - self.box[0])), ("%.0f" % (self.box[3] - self.box[1])))
        self.text = "  ·  ".join(x for x in (size, info) if x)
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = self.rect()
        p.fillRect(r, QtGui.QColor(245, 246, 248))
        fm = p.fontMetrics()
        text_h = fm.height() + 8
        if not self.loops or not self.box:
            p.setPen(QtGui.QColor(120, 120, 120))
            p.drawText(r, QtCore.Qt.AlignCenter, "Sin vista previa")
            p.end()
            return
        x0, y0, x1, y1 = self.box
        w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        area = QtCore.QRectF(r.adjusted(12, 12, -12, -12 - text_h))
        s = min(area.width() / w, area.height() / h)
        ox = area.left() + (area.width() - w * s) / 2.0
        oy = area.top() + (area.height() - h * s) / 2.0
        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.OddEvenFill)
        for loop in self.loops:
            if len(loop) < 2:
                continue
            path.moveTo(ox + (loop[0][0] - x0) * s, oy + (y1 - loop[0][1]) * s)
            for q in loop[1:]:
                path.lineTo(ox + (q[0] - x0) * s, oy + (y1 - q[1]) * s)
            path.closeSubpath()
        p.setPen(QtGui.QPen(QtGui.QColor(27, 110, 60), 1.4))
        p.setBrush(QtGui.QColor(76, 175, 80, 150))
        p.drawPath(path)
        p.setPen(QtGui.QColor(60, 60, 60))
        p.drawText(QtCore.QRectF(r.left(), r.bottom() - text_h, r.width(), text_h), QtCore.Qt.AlignCenter, self.text)
        p.end()
