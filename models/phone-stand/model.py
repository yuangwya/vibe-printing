"""An inclined phone stand for portrait and landscape use. All dimensions are mm."""

from math import cos, isfinite, radians, sin

import cadquery as cq

BASE_WIDTH = 100.0
BASE_DEPTH = 110.0
BASE_THICKNESS = 8.0
BASE_CORNER_RADIUS = 4.0
BACK_WIDTH = 76.0
BACK_LENGTH = 100.0
BACK_THICKNESS = 6.0
BACK_ANGLE = 65.0  # Degrees above the desk; the phone leans toward the rear.
SEAT_BACK_Y = -18.0
SEAT_RISE = 4.0
PHONE_CLEARANCE = 16.0  # Space for the phone and case, perpendicular to the backrest.
LIP_HEIGHT = 10.0
LIP_THICKNESS = 4.0
EDGE_RADIUS = 1.2
BRACE_THICKNESS = 6.0
BRACE_SPACING = 56.0
REAR_MARGIN = 8.0
LABEL = "Made by WYA"
LABEL_SIZE = 4.5
LABEL_RAISE = 0.6
LABEL_EMBED = 0.1


def build_model() -> cq.Workplane:
    dimensions = (
        BASE_WIDTH, BASE_DEPTH, BASE_THICKNESS, BASE_CORNER_RADIUS,
        BACK_WIDTH, BACK_LENGTH, BACK_THICKNESS, SEAT_RISE,
        PHONE_CLEARANCE, LIP_HEIGHT, LIP_THICKNESS, EDGE_RADIUS,
        BRACE_THICKNESS, BRACE_SPACING, REAR_MARGIN,
        LABEL_SIZE, LABEL_RAISE, LABEL_EMBED,
    )
    if not all(isfinite(value) and value > 0 for value in dimensions):
        raise ValueError("All dimensions must be finite and positive")
    if not (isfinite(BACK_ANGLE) and 55 <= BACK_ANGLE <= 75 and isfinite(SEAT_BACK_Y)):
        raise ValueError("Backrest angle must be between 55 and 75 degrees")
    if not (
        BACK_WIDTH < BASE_WIDTH
        and BRACE_SPACING + BRACE_THICKNESS < BACK_WIDTH
        and 2 * EDGE_RADIUS < min(BACK_THICKNESS, LIP_THICKNESS, LIP_HEIGHT)
        and BASE_CORNER_RADIUS < min(BASE_WIDTH, BASE_DEPTH) / 2
        and LABEL_SIZE < BASE_THICKNESS
        and LABEL_EMBED < BASE_THICKNESS / 2
    ):
        raise ValueError("Check widths, brace spacing, edge radii, and label dimensions")

    angle = radians(BACK_ANGLE)
    along_y, along_z = cos(angle), sin(angle)
    seat_z = BASE_THICKNESS + SEAT_RISE

    def point(along: float, outward: float) -> tuple[float, float]:
        # Local coordinates: along the backrest, and out toward the screen.
        return (
            SEAT_BACK_Y + along * along_y - outward * along_z,
            seat_z + along * along_z + outward * along_y,
        )

    def prism(profile, width: float, center_x: float = 0) -> cq.Workplane:
        return (
            cq.Workplane("YZ", origin=(center_x - width / 2, 0, 0))
            .polyline(profile).close().extrude(width)
        )

    # Extend the backrest below the seat so it intersects the base.
    bottom = -(SEAT_RISE + BACK_THICKNESS * along_y + 2) / along_z
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
    ):
        raise ValueError("The seat and backrest must fit inside the base footprint")

    base = (
        cq.Workplane("XY")
        .box(BASE_WIDTH, BASE_DEPTH, BASE_THICKNESS, centered=(True, True, False))
        .edges("|Z").fillet(BASE_CORNER_RADIUS)
        .faces(">Z").edges().fillet(EDGE_RADIUS)
    )
    # Round the whole backrest, including its upper rim and side corners.
    back = prism(back_profile, BACK_WIDTH).edges().fillet(EDGE_RADIUS)
    # Make the seat and lip as one profile, with the front wall reaching the base.
    # This removes the separate lip's projecting lower edge and rounded seam.
    cradle = prism([
        (front_foot_y, BASE_THICKNESS - 2),
        (rear_seat[0], BASE_THICKNESS - 2), rear_seat,
        point(0, PHONE_CLEARANCE), point(LIP_HEIGHT, PHONE_CLEARANCE),
        point(LIP_HEIGHT, PHONE_CLEARANCE + LIP_THICKNESS),
    ], BACK_WIDTH).faces(">Z").edges().fillet(EDGE_RADIUS)

    model = base.union(back).union(cradle)
    # Two triangular rear braces transfer the backrest load into the deep base.
    brace_profile = [
        (SEAT_BACK_Y, BASE_THICKNESS - 2),
        (rear_foot, BASE_THICKNESS - 2), top_rear,
    ]
    for center_x in (-BRACE_SPACING / 2, BRACE_SPACING / 2):
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
