#!/usr/bin/env python3
"""
Hand-laid SVG diagrams for bar_ros2_docs.

Each diagram is a small function that returns an SVG string. Run this file
to regenerate every diagram into ../static/img/diagrams/. The output
filenames match what the markdown references.

The primitive helpers (box, arrow, lane, etc.) are intentionally simple —
they give consistent stroke widths, rounded corners, and a Berkeley
palette across every diagram. The point is not to be a graphing library;
it's to keep the diagrams visually a family.

Palette:
    BLUE     "#003262"    Berkeley blue          structural / control
    GOLD     "#FDB515"    Berkeley gold          policy / external input
    GREEN    "#3B7A57"                           hardware / sim
    RED      "#A00000"                           real hardware / fault
    GREY     "#888888"    neutral                static / inert
    BG       "#FAFAFA"    page background
    TEXT     "#111111"
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "img" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

# Palette ----------------------------------------------------------------------
BLUE = "#003262"
GOLD = "#FDB515"
GREEN = "#3B7A57"
RED = "#A00000"
GREY = "#888888"
LIGHT = "#EEEEEE"
TEXT = "#111111"

# A subdued fill for each accent (use as box background; stroke = the
# strong color). Eyeballed for legibility on a white page.
BLUE_FILL = "#E7F0FF"
GOLD_FILL = "#FFF6DF"
GREEN_FILL = "#E7FFE7"
RED_FILL = "#FFE7E7"
GREY_FILL = "#F4F4F4"

# Font stack uses only space-free family names so we don't need internal
# quoting inside the SVG `font-family` attribute. Anything that has a
# space (e.g. "JetBrains Mono") would need &apos;/&quot; escaping in XML —
# avoided entirely here by sticking to single-token names + the generic
# monospace fallback.
FONT = "ui-monospace, Menlo, Consolas, Courier, monospace"

# --- Primitives --------------------------------------------------------------

def header(w: int, h: int) -> str:
    """SVG root + defs (one arrow-marker is enough)."""
    return dedent(f"""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"
             width="{w}" height="{h}" font-family="{FONT}"
             font-size="13" fill="{TEXT}" text-rendering="geometricPrecision">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="{TEXT}"/>
            </marker>
            <marker id="arrow-grey" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="{GREY}"/>
            </marker>
          </defs>
          <rect width="100%" height="100%" fill="white"/>
    """)

def footer() -> str:
    return "</svg>\n"


def text(x: int, y: int, s: str, *, size: int = 13, weight: int = 400,
         anchor: str = "start", fill: str = TEXT) -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" fill="{fill}" '
        f'dominant-baseline="middle">{s}</text>'
    )


def multiline_text(x: int, y: int, lines: list[str], *, size: int = 13,
                   weight: int = 400, anchor: str = "middle",
                   fill: str = TEXT, lh: float = 1.25) -> str:
    """Several centered text lines starting at (x, y)."""
    total = len(lines)
    start_y = y - (total - 1) * size * lh / 2
    out = []
    for i, line in enumerate(lines):
        out.append(text(x, int(start_y + i * size * lh), line,
                        size=size, weight=weight, anchor=anchor, fill=fill))
    return "\n".join(out)


@dataclass
class Box:
    x: int
    y: int
    w: int
    h: int
    label: str | list[str]  # multi-line allowed via list
    fill: str = "white"
    stroke: str = BLUE
    text_color: str = TEXT
    radius: int = 6
    sub: str | None = None  # optional subtitle below the main label

    @property
    def cx(self) -> int: return self.x + self.w // 2
    @property
    def cy(self) -> int: return self.y + self.h // 2
    @property
    def right(self) -> int: return self.x + self.w
    @property
    def bottom(self) -> int: return self.y + self.h
    @property
    def left(self) -> int: return self.x
    @property
    def top(self) -> int: return self.y

    def render(self) -> str:
        rect = (
            f'<rect x="{self.x}" y="{self.y}" width="{self.w}" height="{self.h}" '
            f'rx="{self.radius}" ry="{self.radius}" fill="{self.fill}" '
            f'stroke="{self.stroke}" stroke-width="1.5"/>'
        )
        if isinstance(self.label, list):
            lines = self.label
        else:
            lines = [self.label]
        # Place sub line slightly below main lines
        label_lines = list(lines)
        labels = multiline_text(
            self.cx, self.cy if not self.sub else self.cy - 8,
            label_lines, size=13, weight=600, fill=self.text_color
        )
        sub = ""
        if self.sub:
            sub_y = self.cy + 10 + (len(lines) - 1) * 8
            sub = text(self.cx, sub_y, self.sub, size=11, weight=400,
                       anchor="middle", fill=GREY)
        return f"{rect}\n{labels}\n{sub}"


def arrow(x1: int, y1: int, x2: int, y2: int, *, color: str = TEXT,
          dashed: bool = False, width: float = 1.4,
          label: str | None = None, label_pos: float = 0.5,
          label_offset: int = -8) -> str:
    marker = "url(#arrow)" if color == TEXT else "url(#arrow-grey)"
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    line = (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
        f'stroke-width="{width}"{dash} marker-end="{marker}"/>'
    )
    if label is None:
        return line
    mx = int(x1 + (x2 - x1) * label_pos)
    my = int(y1 + (y2 - y1) * label_pos) + label_offset
    label_node = text(
        mx, my, label, size=11, anchor="middle", fill=GREY,
    )
    # tiny rounded background pill so the label reads over arrow line
    pad = 4
    approx_w = max(20, int(len(label) * 6) + pad * 2)
    bg = (
        f'<rect x="{mx - approx_w // 2}" y="{my - 8}" width="{approx_w}" '
        f'height="16" rx="3" ry="3" fill="white" stroke="none"/>'
    )
    return f"{line}\n{bg}\n{label_node}"


def polyline(points: list[tuple[int, int]], *, color: str = TEXT,
             dashed: bool = False, width: float = 1.4,
             arrow_end: bool = True) -> str:
    """Multi-segment line; arrow at the end if requested."""
    if not points or len(points) < 2:
        return ""
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    marker = ' marker-end="url(#arrow)"' if arrow_end else ""
    pts = " ".join(f"{x},{y}" for x, y in points)
    return (
        f'<polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="{width}"{dash}{marker}/>'
    )


def label_pill(x: int, y: int, s: str, *, fill: str = "white",
               stroke: str = GREY) -> str:
    """Small label with rounded background — for arrow annotations."""
    pad = 6
    w = max(20, len(s) * 6 + pad * 2)
    rect = (
        f'<rect x="{x - w // 2}" y="{y - 9}" width="{w}" height="18" '
        f'rx="4" ry="4" fill="{fill}" stroke="{stroke}" stroke-width="0.8"/>'
    )
    txt = text(x, y, s, size=11, anchor="middle")
    return f"{rect}\n{txt}"


def title(x: int, y: int, s: str, *, sub: str | None = None) -> str:
    """Diagram title (top-left)."""
    out = [text(x, y, s, size=15, weight=700, anchor="start")]
    if sub:
        out.append(text(x, y + 18, sub, size=11, weight=400,
                        anchor="start", fill=GREY))
    return "\n".join(out)


def group_box(x: int, y: int, w: int, h: int, title_: str, *,
              fill: str = LIGHT, stroke: str = GREY) -> str:
    """A grouping box with a small title at top-left."""
    body = (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" ry="8" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1" stroke-dasharray="5 3"/>'
    )
    label = text(x + 12, y + 16, title_, size=11, weight=600,
                 anchor="start", fill=GREY)
    return f"{body}\n{label}"


def write_svg(name: str, content: str) -> None:
    path = OUT / name
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# --- Diagrams ---------------------------------------------------------------

def d_intro_01_system() -> None:
    """Homepage / intro: 3 vertical lanes (dev / onboard / robot)."""
    W, H = 920, 460
    s = [header(W, H)]
    s.append(title(20, 30, "System at a glance",
                   sub="Developer workstation -> onboard PREEMPT_RT PC -> robot"))

    s.append(group_box(20, 60, 270, 360, "Developer workstation"))
    s.append(group_box(310, 60, 280, 360, "Onboard PC (PREEMPT_RT)"))
    s.append(group_box(610, 60, 290, 360, "Robot (Lite shown)"))

    # Developer
    s.append(Box(50, 100, 210, 50, "IDE / editor",
                 fill=GOLD_FILL, stroke=GOLD).render())
    s.append(Box(50, 170, 210, 70,
                 ["MuJoCo viewer", "(bar_bringup_lite/mujoco)"],
                 fill=GOLD_FILL, stroke=GOLD).render())
    s.append(text(155, 300, "Edits, sim runs, debug",
                  size=11, fill=GREY, anchor="middle"))

    # Onboard
    s.append(Box(340, 100, 220, 50, "bar_bringup_lite / launch",
                 fill=BLUE_FILL, stroke=BLUE).render())
    s.append(Box(340, 170, 220, 60, "controller_manager (50 Hz)",
                 fill=BLUE_FILL, stroke=BLUE).render())
    s.append(Box(340, 250, 100, 50, "mode_manager",
                 fill=BLUE_FILL, stroke=BLUE).render())
    s.append(Box(460, 250, 100, 50, "bar_policy",
                 fill=GOLD_FILL, stroke=GOLD).render())
    s.append(Box(340, 320, 220, 60,
                 ["bar_hw_robstride", "(SocketCAN)"],
                 fill=GREEN_FILL, stroke=GREEN).render())

    # Robot
    s.append(Box(635, 100, 240, 50, "IMU (serial / USB)",
                 fill=GREY_FILL, stroke=GREY).render())
    s.append(Box(635, 170, 110, 90, ["can0", "(left arm)"],
                 fill=RED_FILL, stroke=RED).render())
    s.append(Box(765, 170, 110, 90, ["can1", "(right arm)"],
                 fill=RED_FILL, stroke=RED).render())
    s.append(Box(635, 280, 110, 100,
                 ["Robstride x7", "left arm", "+ neck x3"],
                 fill=RED_FILL, stroke=RED).render())
    s.append(Box(765, 280, 110, 100,
                 ["Robstride x7", "right arm"],
                 fill=RED_FILL, stroke=RED).render())

    # Arrows: dev -> onboard
    s.append(arrow(260, 125, 340, 125, label="code", dashed=True,
                   label_offset=-12, color=GREY))
    s.append(arrow(260, 205, 340, 205, label="sim mode", dashed=True,
                   label_offset=-12, color=GREY))
    # Onboard internal
    s.append(arrow(450, 150, 450, 170))  # bringup -> CM
    s.append(arrow(390, 230, 390, 250))  # CM -> mode_manager
    s.append(arrow(510, 230, 510, 250))  # CM -> policy
    s.append(arrow(390, 300, 390, 320))  # mode_manager -> hw plugin (vertically aligned)
    s.append(arrow(510, 300, 510, 320))  # policy -> hw plugin
    # mode_manager -> CM (loop back)
    s.append(polyline([(345, 275), (320, 275), (320, 200), (340, 200)]))
    # Onboard -> robot (CAN)
    s.append(arrow(560, 350, 690, 350, label="MIT-mode CAN",
                   label_offset=-12))
    s.append(arrow(560, 130, 635, 130, label="/imu/data",
                   color=GREY, label_offset=-12))
    # CAN -> motors
    s.append(arrow(690, 260, 690, 280))
    s.append(arrow(820, 260, 820, 280))

    s.append(footer())
    write_svg("overview__intro__01.svg", "".join(s))


def d_intro_02_packages() -> None:
    """Three columns: shared, Lite-only, Prime-only — with arrows."""
    W, H = 920, 440
    s = [header(W, H)]
    s.append(title(20, 30, "Package organization",
                   sub="Shared core + per-robot leaves"))

    # Lanes
    s.append(group_box(20, 60, 290, 360, "Shared (Lite + Prime)"))
    s.append(group_box(330, 60, 280, 360, "Lite-only"))
    s.append(group_box(630, 60, 270, 360, "Prime-only"))

    def pkg(x, y, name, sub=None, fill=BLUE_FILL, stroke=BLUE):
        s.append(Box(x, y, 250, 44, name, sub=sub,
                     fill=fill, stroke=stroke).render())

    # Shared column
    pkg(40, 90, "bar_common", "RT helpers, MITState POD")
    pkg(40, 144, "bar_msgs", "MITAction, ControlMode, ...")
    pkg(40, 198, "bar_controllers", "5 mode-FSM + mode_manager")
    pkg(40, 252, "bar_policy", "ONNX runner + LeRobot ref")
    pkg(40, 306, "bar_hw_socketcan", "SocketCAN bus library")

    # Lite column
    pkg(345, 110, "bar_description_lite", "URDF + xacro + meshes",
        fill=GREEN_FILL, stroke=GREEN)
    pkg(345, 180, "bar_hw_robstride", "Robstride SystemInterface",
        fill=GREEN_FILL, stroke=GREEN)
    pkg(345, 250, "bar_bringup_lite", "launch + controllers YAML",
        fill=GREEN_FILL, stroke=GREEN)

    # Prime column
    pkg(645, 110, "bar_description_prime", "URDF + EtherCAT PDO",
        fill=RED_FILL, stroke=RED)
    pkg(645, 180, "bar_hw_sito", "Sito SystemInterface",
        fill=RED_FILL, stroke=RED)
    pkg(645, 250, "bar_bringup_prime", "+ ethercat.yaml",
        fill=RED_FILL, stroke=RED)

    # Arrows: bar_hw_robstride -> bar_hw_socketcan
    s.append(arrow(345, 202, 290, 320, color=GREY))
    s.append(arrow(645, 202, 290, 320, color=GREY))
    # bringup_lite -> description_lite + hw_robstride + controllers + policy
    s.append(polyline([(345, 272), (310, 272), (310, 220), (290, 220)],
                      color=GREY))
    # legend
    s.append(text(640, 405, "Arrows = depends on", size=11,
                  anchor="end", fill=GREY))

    s.append(footer())
    write_svg("overview__intro__02.svg", "".join(s))


def d_hw_kinematic_tree() -> None:
    """Lite kinematic tree — chest at top, 3 sub-trees."""
    W, H = 1000, 540
    s = [header(W, H)]
    s.append(title(20, 30, "Lite kinematic tree",
                   sub="17 actuated joints (per-joint effort limit shown)"))

    # base_link / chest
    s.append(Box(420, 70, 160, 40, "base_link", fill=LIGHT, stroke=GREY).render())
    s.append(Box(420, 120, 160, 40, "chest", fill=LIGHT, stroke=GREY).render())
    s.append(arrow(500, 110, 500, 120, color=GREY))

    def joint(x, y, label, effort, side):
        color = BLUE
        fill = BLUE_FILL
        if side == "neck":
            color = GOLD
            fill = GOLD_FILL
        s.append(Box(x, y, 170, 36, label, sub=f"{effort} Nm",
                     fill=fill, stroke=color).render())

    # left arm (column 1)
    left = [
        ("left_shoulder_pitch", 17),
        ("left_shoulder_roll", 14),
        ("left_shoulder_yaw", 14),
        ("left_elbow_pitch", 14),
        ("left_wrist_yaw", 5.5),
        ("left_wrist_roll", 5.5),
        ("left_wrist_pitch", 5.5),
    ]
    for i, (n, e) in enumerate(left):
        joint(20, 180 + i * 48, n, e, "arm")
    # neck (column 2)
    neck = [("neck_yaw", 10), ("neck_roll", 10), ("neck_pitch", 10)]
    for i, (n, e) in enumerate(neck):
        joint(415, 220 + i * 60, n, e, "neck")
    # right arm (column 3)
    right = [
        ("right_shoulder_pitch", 17),
        ("right_shoulder_roll", 14),
        ("right_shoulder_yaw", 14),
        ("right_elbow_pitch", 14),
        ("right_wrist_yaw", 5.5),
        ("right_wrist_roll", 5.5),
        ("right_wrist_pitch", 5.5),
    ]
    for i, (n, e) in enumerate(right):
        joint(810, 180 + i * 48, n, e, "arm")

    # connect: chest -> first of each column
    s.append(polyline([(440, 160), (105, 175), (105, 180)], color=GREY))
    s.append(polyline([(500, 160), (500, 215), (500, 220)], color=GREY))
    s.append(polyline([(560, 160), (895, 175), (895, 180)], color=GREY))

    # chain arrows within each column
    for i in range(len(left) - 1):
        s.append(arrow(105, 180 + i * 48 + 36, 105, 180 + (i + 1) * 48,
                       color=GREY))
    for i in range(len(neck) - 1):
        s.append(arrow(500, 220 + i * 60 + 36, 500, 220 + (i + 1) * 60,
                       color=GREY))
    for i in range(len(right) - 1):
        s.append(arrow(895, 180 + i * 48 + 36, 895, 180 + (i + 1) * 48,
                       color=GREY))

    # legend
    s.append(Box(20, 480, 20, 16, "", fill=BLUE_FILL, stroke=BLUE,
                 radius=3).render())
    s.append(text(46, 488, "arm joint", size=11, anchor="start"))
    s.append(Box(140, 480, 20, 16, "", fill=GOLD_FILL, stroke=GOLD,
                 radius=3).render())
    s.append(text(166, 488, "neck joint", size=11, anchor="start"))

    s.append(footer())
    write_svg("overview__hardware_specifications__01.svg", "".join(s))


def d_hw_can_layout() -> None:
    """Lite CAN-USB topology."""
    W, H = 900, 380
    s = [header(W, H)]
    s.append(title(20, 30, "Lite CAN topology",
                   sub="2 CAN-USB adapters, one per arm; neck shares can0"))

    s.append(Box(40, 80, 200, 60, "Onboard PC", sub="PREEMPT_RT",
                 fill=BLUE_FILL, stroke=BLUE).render())
    s.append(Box(300, 50, 140, 50, "CAN-USB #0",
                 fill=GREY_FILL, stroke=GREY).render())
    s.append(Box(300, 130, 140, 50, "CAN-USB #1",
                 fill=GREY_FILL, stroke=GREY).render())
    s.append(Box(490, 50, 100, 50, "can0",
                 fill=RED_FILL, stroke=RED).render())
    s.append(Box(490, 130, 100, 50, "can1",
                 fill=RED_FILL, stroke=RED).render())
    s.append(Box(640, 30, 240, 90,
                 ["7x Robstride", "left arm + 3x neck"],
                 fill=RED_FILL, stroke=RED).render())
    s.append(Box(640, 150, 240, 90,
                 ["7x Robstride", "right arm"],
                 fill=RED_FILL, stroke=RED).render())

    # USB lines (top)
    s.append(arrow(240, 100, 300, 75, color=GREY, label="USB",
                   label_offset=-10))
    s.append(arrow(240, 120, 300, 155, color=GREY, label="USB",
                   label_offset=-10))
    # CAN-USB -> can iface
    s.append(arrow(440, 75, 490, 75))
    s.append(arrow(440, 155, 490, 155))
    # can iface -> actuators
    s.append(arrow(590, 75, 640, 75, label="CAN @ 1 Mbit"))
    s.append(arrow(590, 155, 640, 155, label="CAN @ 1 Mbit"))

    s.append(text(450, 310,
                  "On real hardware the bar_hw_robstride plugin owns both buses; "
                  "from the controller's perspective the 17 joints are one flat list.",
                  size=11, anchor="middle", fill=GREY))

    s.append(footer())
    write_svg("overview__hardware_specifications__02.svg", "".join(s))


def d_hw_mit_mode() -> None:
    """MIT-mode formula visual."""
    W, H = 920, 360
    s = [header(W, H)]
    s.append(title(20, 30, "MIT-mode hybrid command",
                   sub="Same five interfaces, same torque formula across silicon, sim, mock"))

    # 5 command interfaces (left)
    cmd_x = 30
    cmd_w = 200
    s.append(group_box(cmd_x, 70, cmd_w, 270, "5 cmd interfaces / joint"))
    cmds = [
        ("position", "q_cmd"),
        ("velocity", "qd_cmd"),
        ("effort", "tau_ff"),
        ("stiffness", "K_p"),
        ("damping", "K_d"),
    ]
    for i, (n, v) in enumerate(cmds):
        s.append(Box(cmd_x + 20, 100 + i * 45, cmd_w - 40, 32, n, sub=v,
                     fill=BLUE_FILL, stroke=BLUE).render())

    # Compute box (center)
    cx0, cw = 290, 320
    s.append(Box(cx0, 130, cw, 100,
                 ["tau = K_p * (q_cmd - q)",
                  "    + K_d * (qd_cmd - qd)",
                  "    + tau_ff"],
                 fill=GOLD_FILL, stroke=GOLD).render())
    s.append(text(cx0 + cw // 2, 250, "applied via mjData->qfrc_applied (sim)",
                  size=11, fill=GREY, anchor="middle"))
    s.append(text(cx0 + cw // 2, 268, "or motor firmware (real Robstride)",
                  size=11, fill=GREY, anchor="middle"))

    # 3 state interfaces (right)
    st_x = 660
    st_w = 200
    s.append(group_box(st_x, 110, st_w, 200, "3 state interfaces / joint"))
    states = [("position", "q"), ("velocity", "qd"), ("effort", "tau (meas)")]
    for i, (n, v) in enumerate(states):
        s.append(Box(st_x + 20, 140 + i * 55, st_w - 40, 36, n, sub=v,
                     fill=GREEN_FILL, stroke=GREEN).render())

    # Arrows
    s.append(arrow(cmd_x + cmd_w, 200, cx0, 180,
                   label="controller writes", label_offset=-10))
    s.append(arrow(cx0 + cw, 180, st_x, 200,
                   label="motor reads back", label_offset=-10))

    s.append(footer())
    write_svg("overview__hardware_specifications__05.svg", "".join(s))


def d_sf_rt_cycle() -> None:
    """ros2_control RT cycle — vertical sequence with 3 phases."""
    W, H = 920, 540
    s = [header(W, H)]
    s.append(title(20, 30, "ros2_control real-time cycle (50 Hz)",
                   sub="One tick = read -> update -> write"))

    # 4 vertical lanes
    lanes = [
        ("controller_manager", 100, BLUE),
        ("Hardware plugin", 320, GREEN),
        ("Active controller", 540, GOLD),
        ("Bus (CAN / qfrc)", 770, RED),
    ]
    lane_top = 80
    lane_bot = 510
    for name, x, color in lanes:
        s.append(text(x, lane_top - 6, name, size=12, weight=600,
                      anchor="middle", fill=color))
        s.append(f'<line x1="{x}" y1="{lane_top}" x2="{x}" y2="{lane_bot}" '
                 f'stroke="{color}" stroke-width="1.4" stroke-dasharray="3 3"/>')

    # Phase backgrounds (horizontal bands)
    def phase(y, label, fill):
        s.append(f'<rect x="40" y="{y}" width="850" height="120" '
                 f'fill="{fill}" stroke="none"/>')
        s.append(text(880, y + 20, label, size=11, weight=700,
                      anchor="end", fill=GREY))

    phase(110, "read()", BLUE_FILL)
    phase(240, "update()", GOLD_FILL)
    phase(370, "write()", GREEN_FILL)

    # Arrows within each phase
    def msg(x1, y, x2, label, color=TEXT):
        s.append(arrow(x1, y, x2, y, color=color))
        mx = (x1 + x2) // 2
        s.append(label_pill(mx, y - 18, label))

    msg(100, 145, 320, "read(time, period)")
    s.append(arrow(320, 165, 770, 165, color=GREY, dashed=True))
    s.append(label_pill(550, 147, "poll cached state"))
    msg(770, 195, 320, "q, qd, tau")
    msg(320, 215, 100, "state_interfaces_")

    msg(100, 275, 540, "update(time, period)")
    s.append(text(540, 305,
                  "read state_interfaces_,",
                  size=11, fill=GREY, anchor="middle"))
    s.append(text(540, 322,
                  "compute, write command_interfaces_",
                  size=11, fill=GREY, anchor="middle"))
    msg(540, 345, 100, "return OK")

    msg(100, 405, 320, "write(time, period)")
    s.append(arrow(320, 435, 770, 435, color=GREY, dashed=True))
    s.append(label_pill(550, 417, "stage frames (lock-free)"))
    msg(770, 465, 320, "ack")
    msg(320, 485, 100, "return OK")

    s.append(footer())
    write_svg("overview__software_framework__01.svg", "".join(s))


def d_sf_fsm() -> None:
    """5-mode FSM."""
    W, H = 940, 460
    s = [header(W, H)]
    s.append(title(20, 30, "Five-mode FSM",
                   sub="Only one controller is active at a time; joint_state_broadcaster always runs"))

    # Nodes
    def state(x, y, label, color=BLUE):
        fill = BLUE_FILL if color == BLUE else (
            GREEN_FILL if color == GREEN else
            GOLD_FILL if color == GOLD else
            RED_FILL if color == RED else LIGHT)
        s.append(Box(x, y, 200, 56, label, fill=fill, stroke=color).render())

    state(60, 100, "ZERO_TORQUE", GREEN)
    state(60, 250, "DAMPING", GREEN)
    state(360, 250, "STANDBY", BLUE)
    state(660, 150, "LOCOMOTION", GOLD)
    state(660, 320, "REMOTE", GOLD)

    # Edges
    def edge(p1, p2, label, color=TEXT):
        x1, y1 = p1
        x2, y2 = p2
        s.append(arrow(x1, y1, x2, y2, color=color))
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2 - 8
        s.append(label_pill(mx, my, label))

    # ZERO_TORQUE <-> DAMPING
    edge((130, 156), (130, 250), "DAMP (X / Ctrl+C)")
    edge((180, 250), (180, 156), "manual")

    # DAMPING -> STANDBY
    edge((260, 278), (360, 278), "LOAD (L1+A|B)")
    # STANDBY -> DAMPING
    edge((360, 290), (260, 290), "DAMP", color=GREY)
    # STANDBY -> LOCOMOTION (gated on is_finished)
    edge((560, 260), (660, 178), "START_LOCOMOTION (R1+B)")
    s.append(text(610, 220, "+is_finished", size=10, fill=GREY,
                  anchor="middle"))
    # STANDBY -> REMOTE (gated on is_finished)
    edge((560, 290), (660, 348), "START_REMOTE (R1+A)")
    # LOCOMOTION / REMOTE -> DAMPING
    s.append(polyline([(660, 178), (550, 178), (550, 230), (450, 230),
                       (260, 230)], color=GREY))
    s.append(label_pill(450, 215, "DAMP / fault"))
    s.append(polyline([(660, 348), (550, 348), (550, 320), (450, 320),
                       (260, 320)], color=GREY))
    s.append(label_pill(440, 305, "DAMP / fault"))

    # Quit edges
    s.append(arrow(60, 130, 30, 130, color=GREY))
    s.append(text(30, 118, "QUIT", size=10, fill=GREY, anchor="end"))
    s.append(arrow(60, 280, 30, 280, color=GREY))
    s.append(text(30, 268, "QUIT", size=10, fill=GREY, anchor="end"))

    # Legend
    s.append(text(820, 410, "Green = safe / fail-safe", size=11,
                  anchor="end", fill=GREEN))
    s.append(text(820, 425, "Blue = transitional", size=11, anchor="end",
                  fill=BLUE))
    s.append(text(820, 440, "Gold = active policy", size=11, anchor="end",
                  fill=GOLD))

    s.append(footer())
    write_svg("overview__software_framework__02.svg", "".join(s))


def d_sf_policy_tiers() -> None:
    """In-process vs out-of-process policy tiers."""
    W, H = 920, 460
    s = [header(W, H)]
    s.append(title(20, 30, "Two parallel policy tiers",
                   sub="Same observation contract, different latency / capability"))

    # In-process tier (top half)
    s.append(group_box(40, 60, 400, 170, "In-process (low latency)",
                      fill=GREEN_FILL, stroke=GREEN))
    s.append(Box(60, 100, 170, 50, "RLPolicyController", sub="C++",
                 fill="white", stroke=GREEN).render())
    s.append(Box(250, 100, 170, 50, "ONNX runtime",
                 fill="white", stroke=GREEN).render())
    s.append(Box(60, 165, 170, 50, "ObservationManager", sub="C++",
                 fill="white", stroke=GREEN).render())
    s.append(arrow(230, 125, 250, 125, color=GREEN))
    s.append(arrow(145, 165, 145, 150, color=GREEN))

    # Out-of-process tier (middle)
    s.append(group_box(480, 60, 400, 170, "Out-of-process (heavy models)",
                      fill=GOLD_FILL, stroke=GOLD))
    s.append(Box(500, 100, 170, 50, "RemotePolicyController", sub="C++",
                 fill="white", stroke=GOLD).render())
    s.append(Box(690, 100, 170, 50, "bar_policy", sub="Python rclpy",
                 fill="white", stroke=GOLD).render())
    s.append(Box(690, 165, 170, 50, "PyTorch / VLA / HF",
                 fill="white", stroke=GOLD).render())
    s.append(arrow(670, 125, 690, 125, color=GOLD,
                   label="MITAction / DDS"))
    s.append(arrow(775, 165, 775, 150, color=GOLD))

    # MITState canonical observation (bottom)
    s.append(Box(280, 290, 360, 50,
                 ["MITState  (canonical observation)"], sub=(
                     "joint pos/vel/effort, IMU quat (w,x,y,z), gyro, accel, last_action"
                 ),
                 fill=BLUE_FILL, stroke=BLUE).render())
    s.append(arrow(280, 315, 145, 215, color=GREY))  # to in-process OM
    s.append(arrow(640, 315, 775, 215, color=GREY))  # to out-of-process OM

    # Output
    s.append(Box(360, 390, 200, 44, "5 cmd interfaces / joint",
                 fill=LIGHT, stroke=GREY).render())
    s.append(arrow(230, 150, 460, 390, color=GREY, dashed=True))
    s.append(arrow(585, 150, 460, 390, color=GREY, dashed=True))

    s.append(footer())
    write_svg("overview__software_framework__04.svg", "".join(s))


def d_lite_mock_launch() -> None:
    """Mock-hardware bringup sequence."""
    W, H = 920, 540
    s = [header(W, H)]
    s.append(title(20, 30, "MuJoCo bringup spawn sequence",
                   sub="What happens when you run `ros2 launch bar_bringup_lite mujoco.launch.py`"))

    lanes = [
        ("launch", 100, GREY),
        ("xacro", 280, GREY),
        ("mujoco_sim", 460, BLUE),
        ("controller_manager", 640, BLUE),
        ("mode_manager", 820, GOLD),
    ]
    lt, lb = 80, 510
    for name, x, color in lanes:
        s.append(text(x, lt - 6, name, size=12, weight=600,
                      anchor="middle", fill=color))
        s.append(f'<line x1="{x}" y1="{lt}" x2="{x}" y2="{lb}" '
                 f'stroke="{color}" stroke-width="1.4" stroke-dasharray="3 3"/>')

    def step(y, x1, x2, label, color=TEXT):
        s.append(arrow(x1, y, x2, y, color=color))
        mx = (x1 + x2) // 2
        s.append(label_pill(mx, y - 18, label))

    step(120, 100, 280, "expand xacro (use_sim:=true)")
    step(150, 280, 100, "URDF")
    step(180, 100, 460, "start mujoco_sim")
    step(210, 460, 640, "load MujocoRos2ControlPlugin")
    step(240, 640, 640,
         "register MujocoSystem (17 joints)", color=GREY)
    step(280, 100, 640, "spawn jsb (active)")
    step(310, 100, 640, "spawn zero_torque (active)")
    step(340, 100, 640, "spawn 4 others (inactive)")
    step(380, 100, 820, "start mode_manager")
    step(410, 820, 640, "switch_controller(zero_torque)")

    s.append(text(W // 2, 460,
                  "System is now at ZERO_TORQUE, publishing /joint_states at 50 Hz",
                  size=12, weight=600, fill=BLUE, anchor="middle"))

    s.append(footer())
    write_svg("quick_start__lite_101__02.svg", "".join(s))


def d_lite_mujoco_internals() -> None:
    """mujoco_sim process internal architecture."""
    W, H = 880, 440
    s = [header(W, H)]
    s.append(title(20, 30, "MuJoCo bringup — single mujoco_sim process",
                   sub="Physics + controller_manager + hardware plugin all live in one binary"))

    # Big outer box
    s.append(group_box(40, 80, 800, 280,
                      "mujoco_sim process (mujoco_sim_ros2)",
                      fill="white"))

    s.append(Box(60, 130, 220, 60,
                 ["MuJoCo viewer", "(GLFW window)"],
                 fill=GOLD_FILL, stroke=GOLD).render())
    s.append(Box(60, 220, 220, 60,
                 ["Physics step", "(500 Hz)"],
                 fill=GOLD_FILL, stroke=GOLD).render())
    s.append(Box(330, 130, 230, 60,
                 ["MujocoRos2ControlPlugin", "(physics plugin)"],
                 fill=BLUE_FILL, stroke=BLUE).render())
    s.append(Box(330, 220, 230, 60,
                 ["controller_manager", "(50 Hz)"],
                 fill=BLUE_FILL, stroke=BLUE).render())
    s.append(Box(610, 175, 200, 60,
                 ["MujocoSystem", "(SystemInterface)"],
                 fill=GREEN_FILL, stroke=GREEN).render())

    s.append(arrow(280, 250, 330, 250))
    s.append(arrow(330, 160, 250, 160, color=GREY, dashed=True))  # viewer feedback
    s.append(arrow(440, 280, 440, 320, color=GREY))               # NOP
    s.append(arrow(560, 250, 610, 220))
    s.append(arrow(610, 195, 280, 245, color=GREY, dashed=True))  # qfrc_applied
    s.append(label_pill(440, 198, "qfrc_applied"))
    s.append(text(440, 305, "controllers loaded as usual via pluginlib",
                  size=11, fill=GREY, anchor="middle"))

    # External nodes
    s.append(Box(80, 380, 200, 40, "robot_state_publisher",
                 fill=LIGHT, stroke=GREY).render())
    s.append(Box(310, 380, 220, 40, "controller spawners",
                 fill=LIGHT, stroke=GREY).render())
    s.append(Box(560, 380, 180, 40, "mode_manager",
                 fill=LIGHT, stroke=GREY).render())
    s.append(arrow(180, 380, 180, 290, color=GREY, dashed=True))
    s.append(label_pill(180, 340, "/robot_description"))
    s.append(arrow(420, 380, 420, 290, color=GREY, dashed=True))
    s.append(arrow(650, 380, 540, 290, color=GREY, dashed=True))
    s.append(label_pill(560, 345, "/clock from MuJoCo"))

    s.append(footer())
    write_svg("quick_start__lite_101__04.svg", "".join(s))


def d_xacro_3way() -> None:
    """xacro arg -> plugin selector decision tree."""
    W, H = 760, 400
    s = [header(W, H)]
    s.append(title(20, 30, "lite.urdf.xacro: 3-way hardware selector",
                   sub="One xacro file, three target backends"))

    s.append(Box(40, 100, 180, 60, "lite.urdf.xacro",
                 fill=BLUE_FILL, stroke=BLUE).render())

    # First branch: use_sim?
    s.append(Box(280, 70, 130, 40, "use_sim?",
                 fill=LIGHT, stroke=GREY).render())
    s.append(arrow(220, 130, 280, 90))
    s.append(label_pill(250, 110, "args"))

    # Yes -> MujocoSystem
    s.append(Box(470, 50, 250, 50, "mujoco_ros2_control/", sub="MujocoSystem",
                 fill=GOLD_FILL, stroke=GOLD).render())
    s.append(arrow(410, 80, 470, 75, label="true"))

    # No -> second branch
    s.append(Box(280, 200, 180, 40, "use_fake_hardware?",
                 fill=LIGHT, stroke=GREY).render())
    s.append(arrow(345, 110, 345, 200, label="false"))

    # Yes -> mock
    s.append(Box(490, 175, 230, 50,
                 "mock_components/GenericSystem",
                 fill=GREEN_FILL, stroke=GREEN).render())
    s.append(arrow(460, 215, 490, 200, label="true"))

    # No -> real
    s.append(Box(490, 280, 230, 60, "bar_hw_robstride/", sub="RobstrideSystem",
                 fill=RED_FILL, stroke=RED).render())
    s.append(arrow(370, 240, 490, 305, label="false"))

    s.append(text(380, 365,
                  "use_sim wins over use_fake_hardware when both are true",
                  size=11, fill=GREY, anchor="middle"))

    s.append(footer())
    write_svg("reference__packages__02.svg", "".join(s))


def d_msgs_pubsub() -> None:
    """bar_msgs pub/sub topology."""
    W, H = 920, 480
    s = [header(W, H)]
    s.append(title(20, 30, "bar_msgs pub/sub topology",
                   sub="Who publishes / who subscribes for each of the 4 active topics"))

    # 3 columns: publishers / topics / subscribers
    s.append(group_box(20, 70, 230, 380, "Publishers"))
    s.append(group_box(330, 70, 250, 380, "Topics"))
    s.append(group_box(660, 70, 240, 380, "Subscribers"))

    def pub(x, y, label, color=BLUE):
        fill = BLUE_FILL if color == BLUE else (
            GOLD_FILL if color == GOLD else
            GREEN_FILL if color == GREEN else
            RED_FILL if color == RED else LIGHT)
        s.append(Box(x, y, 200, 40, label, fill=fill, stroke=color).render())

    pub(35, 100, "StandbyController", BLUE)
    pub(35, 160, "mode_manager", GOLD)
    pub(35, 220, "Hardware plugins", RED)
    pub(35, 280, "Active policy ctrls", BLUE)
    pub(35, 340, "bar_policy (Python)", GOLD)

    pub(350, 100, "/standby_controller/state", GREEN)
    pub(350, 160, "/control_mode", GREEN)
    pub(350, 220, "/safety_status", GREEN)
    pub(350, 280, "~/command (MITAction)", GREEN)

    pub(680, 100, "mode_manager", GOLD)
    pub(680, 160, "diagnostics / log", GREY)
    pub(680, 220, "mode_manager", GOLD)
    pub(680, 280, "RemotePolicyController", BLUE)

    # Arrows
    pairs = [
        (130, 130, 350, 130),    # StandbyCtrl -> /standby_controller/state
        (130, 200, 350, 190),    # mode_manager -> /control_mode
        (130, 270, 350, 250),    # HW plugins -> /safety_status
        (130, 270, 350, 250),
        (130, 380, 350, 310),    # bar_policy -> ~/command
        # topics -> subs
        (560, 130, 680, 130),    # standby/state -> mode_manager
        (560, 190, 680, 190),    # control_mode -> log
        (560, 250, 680, 250),    # safety_status -> mode_manager
        (560, 310, 680, 310),    # ~/command -> RemotePolicy
    ]
    seen = set()
    for x1, y1, x2, y2 in pairs:
        k = (x1, y1, x2, y2)
        if k in seen: continue
        seen.add(k)
        s.append(arrow(x1, y1, x2, y2, color=GREY))

    s.append(text(W // 2, 460,
                  "/standby_controller/state uses TRANSIENT_LOCAL QoS so a late mode_manager sees the last is_finished",
                  size=11, fill=GREY, anchor="middle"))

    s.append(footer())
    write_svg("reference__messages__01.svg", "".join(s))


# --- Main --------------------------------------------------------------------

def main() -> None:
    print(f"Generating SVGs into {OUT.relative_to(ROOT)}/")
    d_intro_01_system()
    d_intro_02_packages()
    d_hw_kinematic_tree()
    d_hw_can_layout()
    d_hw_mit_mode()
    d_sf_rt_cycle()
    d_sf_fsm()
    d_sf_policy_tiers()
    d_lite_mock_launch()
    d_lite_mujoco_internals()
    d_xacro_3way()
    d_msgs_pubsub()
    print("Done.")


if __name__ == "__main__":
    main()
