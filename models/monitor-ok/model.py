"""Rounded, connected OK lettering with integral monitor hooks. Units: mm.

The letter face lies on XY at Z=0. When installed, +Y points upward and
+Z points toward the rear of the monitor. Use yellow filament for the finish.
The hooks are rigid hangers, not spring clips; measure the monitor first.
"""

from math import isfinite

import cadquery as cq

LETTER_DEPTH = 8.0
O_CENTER_X = -32.0
O_OUTER_X = 26.0
O_OUTER_Y = 28.0
O_INNER_X = 9.5
O_INNER_Y = 12.0
K_STEM_X = 11.0
K_STROKE = 20.0
K_HEIGHT = 70.0
EDGE_RADIUS = 2.0
REAR_BRIDGE_HEIGHT = 7.0
MONITOR_THICKNESS = 20.0
FIT_CLEARANCE = 1.0
MONITOR_TOP_Y = -18.0
HOOK_WALL = 4.0
HOOK_WIDTH = 10.0
HOOK_DROP = 18.0
HOOK_RADIUS = 0.8
HOOK_X = (-48.0, K_STEM_X)
PREVIEW_COLOR = "#FFD51C"


def build_model() -> cq.Workplane:
    dimensions = (
        LETTER_DEPTH, O_OUTER_X, O_OUTER_Y, O_INNER_X, O_INNER_Y,
        K_STROKE, K_HEIGHT,
        EDGE_RADIUS, REAR_BRIDGE_HEIGHT, MONITOR_THICKNESS, FIT_CLEARANCE,
        HOOK_WALL, HOOK_WIDTH, HOOK_DROP, HOOK_RADIUS,
    )
    if not all(isfinite(v) and v > 0 for v in dimensions):
        raise ValueError("Dimensions must be finite and positive")
    if not all(isfinite(v) for v in (O_CENTER_X, K_STEM_X, MONITOR_TOP_Y, *HOOK_X)):
        raise ValueError("Positions must be finite")
    if not (
        O_OUTER_X - O_INNER_X >= 8
        and O_OUTER_Y - O_INNER_Y >= 8
        and 2 * EDGE_RADIUS < min(LETTER_DEPTH, K_STROKE)
        and 2 * HOOK_RADIUS < min(HOOK_WALL, HOOK_WIDTH)
        and HOOK_DROP >= 10
        and HOOK_WIDTH >= 8 and HOOK_WALL >= 3
    ):
        raise ValueError("Keep substantial letter strokes, hook walls, and safe edge radii")

    # Trace a plump, slightly tilted O with a small off-center counter.
    letter_o = (
        cq.Workplane("XY").ellipse(O_OUTER_X, O_OUTER_Y)
        .center(-0.8, 0.8).ellipse(O_INNER_X, O_INNER_Y)
        .extrude(LETTER_DEPTH).edges().fillet(EDGE_RADIUS)
        .rotate((0, 0, 0), (0, 0, 1), 12)
        .translate((O_CENTER_X, 0, 0))
    )

    # Manually trace the supplied cropped reference in its image coordinates.
    # This is an outline reconstruction from one photograph, not a font glyph
    # or an exact recovery of the original CAD geometry.
    reference_outline = [
        (210, 79), (213, 67), (235, 56), (250, 57), (268, 67),
        (272, 82), (272, 110), (272, 139), (276, 160), (285, 153),
        (299, 133), (319, 125), (339, 128), (348, 137),
        (347, 155), (337, 174), (320, 188), (312, 197),
        (323, 210), (340, 232), (354, 259), (362, 281),
        (360, 294), (344, 301), (319, 301), (304, 295),
        (297, 277), (287, 248), (278, 226), (272, 218),
        (273, 271), (269, 296), (254, 301), (233, 301),
        (218, 295), (212, 278), (211, 240), (210, 200),
        (210, 160), (210, 120),
    ]
    points = [
        (K_STEM_X + (x - 240) * K_STROKE / 64,
         (180 - y) * K_HEIGHT / 250)
        for x, y in reference_outline
    ]
    # A single periodic spline keeps the traced perimeter smooth through
    # every landmark and avoids seams between separately rounded segments.
    outline = cq.Workplane("XY").spline(points, periodic=True).close()
    letter_k = outline.extrude(LETTER_DEPTH).edges("not |Z").fillet(EDGE_RADIUS)
    # Align the actual outer minima after rounding, rather than font metrics.
    baseline = letter_o.val().BoundingBox().ymin
    letter_k = letter_k.translate((0, baseline - letter_k.val().BoundingBox().ymin, 0))
    if abs(letter_k.val().BoundingBox().ymin - baseline) > 1e-5:
        raise ValueError("The letter bottoms must share one horizontal baseline")
    body = letter_o.union(letter_k)

    # Two open-bottom U hangers straddle the monitor top without clamping it.
    gap = MONITOR_THICKNESS + FIT_CLEARANCE
    rear_inner = LETTER_DEPTH + gap
    roof_y = MONITOR_TOP_Y + HOOK_WALL
    for x in HOOK_X:
        profile = [
            (MONITOR_TOP_Y, LETTER_DEPTH - 2),
            (roof_y, LETTER_DEPTH - 2),
            (roof_y, rear_inner + HOOK_WALL),
            (MONITOR_TOP_Y - HOOK_DROP, rear_inner + HOOK_WALL),
            (MONITOR_TOP_Y - HOOK_DROP, rear_inner),
            (MONITOR_TOP_Y, rear_inner),
        ]
        hook = (
            cq.Workplane("YZ", origin=(x - HOOK_WIDTH / 2, 0, 0))
            .polyline(profile).close().extrude(HOOK_WIDTH)
            .edges().fillet(HOOK_RADIUS)
        )
        # Require a real attachment volume, rather than touching faces.
        attachment = body.val().intersect(hook.val()).Volume()
        if attachment < HOOK_WIDTH * HOOK_WALL * 0.5:
            raise ValueError("Each hook must overlap a substantial letter stroke")
        body = body.union(hook)

    # Join the hooks only behind the monitor. There is no front letter tie.
    left, right = min(HOOK_X), max(HOOK_X)
    rear_bridge = (
        cq.Workplane("XY", origin=((left + right) / 2,
                     roof_y - REAR_BRIDGE_HEIGHT / 2, rear_inner))
        .box(right - left + HOOK_WIDTH, REAR_BRIDGE_HEIGHT, HOOK_WALL,
             centered=(True, True, False))
        .edges().fillet(HOOK_RADIUS)
    )
    body = body.union(rear_bridge)

    solid = body.val()
    if not solid.isValid() or len(body.solids().vals()) != 1:
        raise ValueError("The finished hanger must be one valid connected solid")
    # The visible face points toward -Z; mirror X so OK reads correctly from
    # the front when the hooks extend behind the monitor toward +Z.
    return body.mirror("YZ").translate((0, 0, -solid.BoundingBox().zmin))
