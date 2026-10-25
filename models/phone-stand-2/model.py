"""A compact second-generation stand with large engraved labels. Units: mm."""

from math import cos, hypot, isfinite, radians, sin
from pathlib import Path

import cadquery as cq

BASE_WIDTH = 84.0
BASE_DEPTH = 92.0
BASE_THICKNESS = 7.0
BASE_CORNER_RADIUS = 4.0
BACK_WIDTH = 64.0
BACK_LENGTH = 78.0
BACK_THICKNESS = 4.0
BACK_ANGLE = 65.0  # Degrees above the desk; the phone leans toward the rear.
SEAT_BACK_Y = -16.0
SEAT_RISE = 2.5
PHONE_CLEARANCE = 16.0  # Space for the phone and case, perpendicular to the backrest.
LIP_HEIGHT = 12.0
LIP_THICKNESS = 5.0
EDGE_RADIUS = 1.0
BRACE_THICKNESS = 4.0
REAR_MARGIN = 8.0
BACK_WINDOW_WIDTH = 42.0
BACK_WINDOW_BOTTOM = 15.0
BACK_WINDOW_TOP = 68.0
MIN_FRAME_RAIL = 8.0
MAX_HALF_BRIDGE = 20.0
BASE_WINDOW_WIDTH = 29.0
BASE_WINDOW_DEPTH = 43.0
BASE_WINDOW_Y = 12.0
BASE_WINDOW_OFFSET = 20.0
BASE_WINDOW_RADIUS = 3.0
LABEL = "MADE BY WYA"
LABEL_SIZE = 6.0
LABEL_DEPTH = 0.7
BANNER = "刘妈肉蛋堡"
BANNER_SIZE = 11.2
BANNER_DEPTH = 0.7
BANNER_CENTER_FRACTION = 0.60
TEXT_EDGE_MARGIN = 1.5
BASE_LABEL_MARGIN = 0.65
MIN_TEXT_BACKING = 1.6
FONT_PATH = Path(__file__).resolve().parents[2] / "assets/fonts/VibePrintingLabels-Bold.otf"
FONT_CHARACTERS = frozenset("刘妈肉蛋堡MADE BY WYA ")


def build_model() -> cq.Workplane:
    if set(LABEL + BANNER) - FONT_CHARACTERS:
        raise ValueError("The bundled font subset must be extended for the new label characters")
    dimensions = (
        BASE_WIDTH, BASE_DEPTH, BASE_THICKNESS, BASE_CORNER_RADIUS,
        BACK_WIDTH, BACK_LENGTH, BACK_THICKNESS, SEAT_RISE,
        PHONE_CLEARANCE, LIP_HEIGHT, LIP_THICKNESS, EDGE_RADIUS,
        BRACE_THICKNESS, REAR_MARGIN,
        LABEL_SIZE, LABEL_DEPTH, BANNER_SIZE, BANNER_DEPTH,
        TEXT_EDGE_MARGIN, BASE_LABEL_MARGIN, MIN_TEXT_BACKING,
        BACK_WINDOW_WIDTH, BACK_WINDOW_BOTTOM,
        BACK_WINDOW_TOP, BASE_WINDOW_WIDTH, BASE_WINDOW_DEPTH,
        BASE_WINDOW_Y, BASE_WINDOW_OFFSET, BASE_WINDOW_RADIUS,
        MIN_FRAME_RAIL, MAX_HALF_BRIDGE,
    )
    if not all(isfinite(value) and value > 0 for value in dimensions):
        raise ValueError("All dimensions must be finite and positive")
    if not (isfinite(BACK_ANGLE) and 55 <= BACK_ANGLE <= 75 and isfinite(SEAT_BACK_Y)):
        raise ValueError("Backrest angle must be between 55 and 75 degrees")
    if not (
        BACK_WIDTH < BASE_WIDTH
        and BRACE_THICKNESS < BACK_WIDTH
        and 2 * EDGE_RADIUS < min(BACK_THICKNESS, LIP_THICKNESS, LIP_HEIGHT)
        and BASE_CORNER_RADIUS < min(BASE_WIDTH, BASE_DEPTH) / 2
        and LABEL_SIZE < BASE_THICKNESS
        and max(LABEL_DEPTH, BANNER_DEPTH) < LIP_THICKNESS - MIN_TEXT_BACKING
        and isfinite(BANNER_CENTER_FRACTION) and 0 < BANNER_CENTER_FRACTION < 1
    ):
        raise ValueError("Check widths, brace thickness, edge radii, and label dimensions")

    if not (
        BACK_WINDOW_WIDTH + 2 * BRACE_THICKNESS < BACK_WIDTH
        and 0 < BACK_WINDOW_BOTTOM < BACK_WINDOW_TOP < BACK_LENGTH - 2 * EDGE_RADIUS
        and (BACK_WIDTH - BACK_WINDOW_WIDTH) / 2 >= MIN_FRAME_RAIL
        and BACK_LENGTH - BACK_WINDOW_TOP >= MIN_FRAME_RAIL
        and (BACK_WINDOW_WIDTH - BRACE_THICKNESS) / 2 <= MAX_HALF_BRIDGE
        and BASE_WINDOW_OFFSET - BASE_WINDOW_WIDTH / 2 > BRACE_THICKNESS / 2 + EDGE_RADIUS
        and BASE_WINDOW_OFFSET + BASE_WINDOW_WIDTH / 2 < BASE_WIDTH / 2 - BASE_CORNER_RADIUS
        and 2 * BASE_WINDOW_RADIUS < min(BASE_WINDOW_WIDTH, BASE_WINDOW_DEPTH)
    ):
        raise ValueError("Windows must preserve the side rails, top rail, and center spine")

    angle = radians(BACK_ANGLE)
    along_y, along_z = cos(angle), sin(angle)
    seat_z = BASE_THICKNESS + SEAT_RISE

    def point(along: float, outward: float) -> tuple[float, float]:
        # Local coordinates: along the backrest, and out toward the screen.
        return (
            SEAT_BACK_Y + along * along_y - outward * along_z,
            seat_z + along * along_z + outward * along_y,
        )

    def prism(profile, width: float) -> cq.Workplane:
        return (
            cq.Workplane("YZ", origin=(-width / 2, 0, 0))
            .polyline(profile).close().extrude(width)
        )

    # Extend the backrest below the seat so it intersects the base.
    bottom = -(SEAT_RISE + 1) / along_z
    back_profile = [
        point(bottom, 0), point(BACK_LENGTH, 0),
        point(BACK_LENGTH, -BACK_THICKNESS), point(bottom, -BACK_THICKNESS),
    ]
    front_foot_y = point(-2, PHONE_CLEARANCE + LIP_THICKNESS)[0]
    rear_seat = point(0, -BACK_THICKNESS)
    top_rear = point(BACK_LENGTH - 2, -BACK_THICKNESS / 2)
    rear_foot = BASE_DEPTH / 2 - REAR_MARGIN
    if not (
        front_foot_y > -BASE_DEPTH / 2 + BASE_CORNER_RADIUS
        and max(y for y, _ in back_profile) < rear_foot
        and min(z for _, z in back_profile) >= 0
        and BASE_WINDOW_Y - BASE_WINDOW_DEPTH / 2 > rear_seat[0] + EDGE_RADIUS
        and BASE_WINDOW_Y + BASE_WINDOW_DEPTH / 2 < rear_foot - EDGE_RADIUS
    ):
        raise ValueError("The seat and backrest must fit inside the base footprint")

    base = (
        cq.Workplane("XY")
        .box(BASE_WIDTH, BASE_DEPTH, BASE_THICKNESS, centered=(True, True, False))
        .edges("|Z").fillet(BASE_CORNER_RADIUS)
        .faces(">Z").edges().fillet(EDGE_RADIUS)
    )
    # Through-windows preserve the outer footprint and the central brace spine.
    for center_x in (-BASE_WINDOW_OFFSET, BASE_WINDOW_OFFSET):
        window = (
            cq.Workplane("XY", origin=(center_x, BASE_WINDOW_Y, -1))
            .box(BASE_WINDOW_WIDTH, BASE_WINDOW_DEPTH, BASE_THICKNESS + 2,
                 centered=(True, True, False))
            .edges("|Z").fillet(BASE_WINDOW_RADIUS)
        )
        base = base.cut(window)
    # Round the whole backrest, including its upper rim and side corners.
    back = prism(back_profile, BACK_WIDTH).edges().fillet(EDGE_RADIUS)
    # Retain 11 mm side rails and a 10 mm top rail at the default dimensions.
    # The center brace divides the rectangular opening into two 19 mm spans.
    window_origin = point(0, 2)
    window_plane = cq.Plane(
        origin=(0, *window_origin), xDir=(1, 0, 0), normal=(0, -along_z, along_y)
    )
    half_window = BACK_WINDOW_WIDTH / 2
    opening = (
        cq.Workplane(window_plane).polyline([
            (-half_window, BACK_WINDOW_BOTTOM), (half_window, BACK_WINDOW_BOTTOM),
            (half_window, BACK_WINDOW_TOP), (-half_window, BACK_WINDOW_TOP),
        ]).close().extrude(-(BACK_THICKNESS + 4))
        .edges().fillet(EDGE_RADIUS)
    )
    back = back.cut(opening)
    # Make the seat and lip as one profile, with the front wall reaching the base.
    # This removes the separate lip's projecting lower edge and rounded seam.
    cradle = prism([
        (front_foot_y, BASE_THICKNESS - 2),
        (rear_seat[0], BASE_THICKNESS - 2), rear_seat,
        point(0, PHONE_CLEARANCE), point(LIP_HEIGHT, PHONE_CLEARANCE),
        point(LIP_HEIGHT, PHONE_CLEARANCE + LIP_THICKNESS),
    ], BACK_WIDTH).faces(">Z").edges().fillet(EDGE_RADIUS)

    model = base.union(back).union(cradle)
    # One central rear brace supports the backrest with less material.
    brace_profile = [
        (SEAT_BACK_Y, BASE_THICKNESS - 2),
        (rear_foot, BASE_THICKNESS - 2), top_rear,
    ]
    brace = prism(brace_profile, BRACE_THICKNESS).edges().fillet(EDGE_RADIUS)
    model = model.union(brace)

    if not FONT_PATH.is_file():
        raise ValueError(f"Bundled label font is missing: {FONT_PATH}")

    def engrave(body, plane, text, size, depth, available_width, available_height,
                margin=TEXT_EDGE_MARGIN):
        # Use one bundled bold font so labels never depend on font fallback.
        letters = (
            cq.Workplane(plane).text(
                text, size, -depth, fontPath=str(FONT_PATH),
                kind="bold", combine=False, halign="center", valign="center",
            )
        )
        local = letters.val().transformShape(plane.fG)
        bounds = local.BoundingBox()
        if (bounds.xlen + 2 * margin > available_width
                or bounds.ylen + 2 * margin > available_height):
            raise ValueError(f"Label {text!r} does not fit its panel")
        # Center the actual outline rather than the font's baseline metrics.
        delta = plane.xDir.multiply(-(bounds.xmin + bounds.xmax) / 2).add(
            plane.yDir.multiply(-(bounds.ymin + bounds.ymax) / 2)
        )
        letters = letters.translate(delta.toTuple())
        cutter = letters.val()
        # Check each recess retains solid backing below its full engraved depth.
        backing = (
            cq.Workplane(plane).text(
                text, size, -(depth + MIN_TEXT_BACKING), fontPath=str(FONT_PATH),
                kind="bold", combine=False, halign="center", valign="center",
            ).translate(delta.toTuple()).val()
        )
        embedded = body.val().intersect(backing).Volume()
        if not cutter.isValid() or abs(embedded - backing.Volume()) > 1e-4:
            raise ValueError(f"Label {text!r} lacks sufficient solid backing")
        return body.cut(letters)

    # Large bold recessed capitals replace the tiny raised v1 lettering.
    base_plane = cq.Plane(
        origin=(0, -BASE_DEPTH / 2, (BASE_THICKNESS - EDGE_RADIUS) / 2),
        xDir=(1, 0, 0), normal=(0, -1, 0),
    )
    model = engrave(model, base_plane, LABEL, LABEL_SIZE, LABEL_DEPTH,
                    BASE_WIDTH - 2 * BASE_CORNER_RADIUS, BASE_THICKNESS - EDGE_RADIUS,
                    margin=BASE_LABEL_MARGIN)

    # Put the large Chinese inscription on the outside of the continuous lip wall.
    low_y, low_z = front_foot_y, BASE_THICKNESS - 2
    high_y, high_z = point(LIP_HEIGHT, PHONE_CLEARANCE + LIP_THICKNESS)
    dy, dz = high_y - low_y, high_z - low_z
    wall_length = hypot(dy, dz)
    center = BANNER_CENTER_FRACTION
    banner_plane = cq.Plane(
        origin=(0, low_y + center * dy, low_z + center * dz),
        xDir=(1, 0, 0), normal=(0, -dz / wall_length, dy / wall_length),
    )
    model = engrave(model, banner_plane, BANNER, BANNER_SIZE, BANNER_DEPTH,
                    BACK_WIDTH - 2 * EDGE_RADIUS,
                    2 * min(center, 1 - center) * wall_length - 2 * EDGE_RADIUS)
    return model
