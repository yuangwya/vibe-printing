# Monitor OK

A rounded Ok ornament with custom curved letter outlines and two integral
monitor hangers joined by a rear crossbar. The letter faces have no connecting tie.
The complete model is one solid and needs no assembly. Use yellow filament.

- Overall envelope: approximately 108 × 77 × 33 mm.
- Letter depth: 8 mm; visible edges have 2 mm fillets.
- Default monitor thickness: 20 mm, plus 1 mm fit clearance (21 mm clear gap).
- Two 10 mm wide hooks have 4 mm walls and 18 mm rear drops.
- Both letters share one horizontal bottom baseline. The k uses a smooth
  periodic outline traced from the supplied photograph, with rounded face
  edges and a slightly wider horizontal proportion. This reconstruction
  does not recover the exact original CAD geometry from the photograph.

Measure the monitor at the mounting location and edit `MONITOR_THICKNESS`
and `FIT_CLEARANCE` in `model.py`. The default assumes a flat, parallel top
edge. A tapered or curved housing needs an adjusted hook profile. Keep the
hooks clear of vents and check that the letter overlap fits the top bezel.

```bash
python scripts/preview.py monitor-ok --watch --color '#FFD51C'
```

The visible letter face is at Z=0; the hooks extend toward +Z behind the
monitor. View from -Z with +Y upward to see the installed front correctly.
The model rests face down on XY. Integral hooks have overhangs, so printing
may require support and orientation review during the slicing stage.
Single-solid and rectangular monitor-clearance checks have passed; this
revision has not been sliced or physically fit tested.
