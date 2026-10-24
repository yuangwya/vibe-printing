"""An inclined phone stand for portrait and landscape use. All dimensions are mm."""

from math import cos, isfinite, radians, sin

import cadquery as cq

BASE_WIDTH = 90.0
BASE_DEPTH = 100.0
BASE_THICKNESS = 4.5
BASE_CORNER_RADIUS = 4.0
BACK_WIDTH = 70.0
BACK_LENGTH = 85.0
BACK_THICKNESS = 4.0
BACK_ANGLE = 65.0  # Degrees above the desk; the phone leans toward the rear.
SEAT_BACK_Y = -18.0
SEAT_RISE = 3.0
PHONE_CLEARANCE = 16.0  # Space for the phone and case, perpendicular to the backrest.
LIP_HEIGHT = 8.0
LIP_THICKNESS = 3.2
EDGE_RADIUS = 1.0
BRACE_THICKNESS = 4.0
REAR_MARGIN = 8.0
BACK_WINDOW_WIDTH = 48.0
BACK_WINDOW_BOTTOM = 18.0
BACK_WINDOW_SHOULDER = 42.0
BACK_WINDOW_TOP = 75.0
BASE_WINDOW_WIDTH = 33.0
BASE_WINDOW_DEPTH = 50.0
BASE_WINDOW_Y = 14.0
BASE_WINDOW_OFFSET = 22.5
BASE_WINDOW_RADIUS = 3.0
LABEL = "Made by WYA"
LABEL_SIZE = 3.0
LABEL_RAISE = 0.6
LABEL_EMBED = 0.1


def build_model() -> cq.Workplane:
    dimensions = (
        BASE_WIDTH, BASE_DEPTH, BASE_THICKNESS, BASE_CORNER_RADIUS,
        BACK_WIDTH, BACK_LENGTH, BACK_THICKNESS, SEAT_RISE,
        PHONE_CLEARANCE, LIP_HEIGHT, LIP_THICKNESS, EDGE_RADIUS,
        BRACE_THICKNESS, REAR_MARGIN,
        LABEL_SIZE, LABEL_RAISE, LABEL_EMBED,
        BACK_WINDOW_WIDTH, BACK_WINDOW_BOTTOM, BACK_WINDOW_SHOULDER,
        BACK_WINDOW_TOP, BASE_WINDOW_WIDTH, BASE_WINDOW_DEPTH,
        BASE_WINDOW_Y, BASE_WINDOW_OFFSET, BASE_WINDOW_RADIUS,
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
        and LABEL_EMBED < BASE_THICKNESS / 2
    ):
        raise ValueError("Check widths, brace thickness, edge radii, and label dimensions")

    if not (
        BACK_WINDOW_WIDTH + 2 * BRACE_THICKNESS < BACK_WIDTH
        and 0 < BACK_WINDOW_BOTTOM < BACK_WINDOW_SHOULDER < BACK_WINDOW_TOP < BACK_LENGTH - 2 * EDGE_RADIUS
        and (BACK_WINDOW_TOP - BACK_WINDOW_SHOULDER) * sin(radians(BACK_ANGLE)) >= BACK_WINDOW_WIDTH / 2
        and BASE_WINDOW_OFFSET - BASE_WINDOW_WIDTH / 2 > BRACE_THICKNESS / 2 + EDGE_RADIUS
        and BASE_WINDOW_OFFSET + BASE_WINDOW_WIDTH / 2 < BASE_WIDTH / 2 - BASE_CORNER_RADIUS
        and 2 * BASE_WINDOW_RADIUS < min(BASE_WINDOW_WIDTH, BASE_WINDOW_DEPTH)
    ):
        raise ValueError("Windows must preserve the side rails, center spine, and a sloping roof")

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
    # A pointed window avoids a long horizontal bridge at the top of the opening.
    window_origin = point(0, 2)
    window_plane = cq.Plane(
        origin=(0, *window_origin), xDir=(1, 0, 0), normal=(0, -along_z, along_y)
    )
    half_window = BACK_WINDOW_WIDTH / 2
    opening = (
        cq.Workplane(window_plane).polyline([
            (-half_window, BACK_WINDOW_BOTTOM), (half_window, BACK_WINDOW_BOTTOM),
            (half_window, BACK_WINDOW_SHOULDER), (0, BACK_WINDOW_TOP),
            (-half_window, BACK_WINDOW_SHOULDER),
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

    return (
        model.faces("<Y").workplane(centerOption="CenterOfMass", offset=-LABEL_EMBED)
        .text(
            LABEL, LABEL_SIZE, LABEL_RAISE + LABEL_EMBED,
            font="Helvetica", kind="bold", combine="a",
            halign="center", valign="center",
        )
    )
