# Statcast Utilities

The old pandas utility helpers were removed in `polars-baseball` v2. Derived calculations should now be performed directly with Polars expressions or normal Python math.

## Spray Angle

The legacy `add_spray_angle` helper calculated spray angle from Statcast hit coordinates. The core formula is:

```python
from math import atan2, pi

spray_angle = atan2(hc_x - 125.42, 198.27 - hc_y) * 180 / pi
```

For left-handed batters, adjusted spray angle flips the sign so push and pull contact can be compared consistently.

## Sample Distribution

![Spray angle histograms](images/spray_angle_hists.png)
