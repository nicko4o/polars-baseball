# Statcast Utilities

舊版 pandas utility helpers 已在 `polars-baseball` v2 移除。衍生計算應直接使用 Polars expressions 或一般 Python math 完成。

## Spray Angle

舊版 `add_spray_angle` helper 會從 Statcast 擊球座標計算 spray angle。核心公式如下：

```python
from math import atan2, pi

spray_angle = atan2(hc_x - 125.42, 198.27 - hc_y) * 180 / pi
```

對左打者而言，adjusted spray angle 會翻轉正負號，讓推打與拉打方向能一致比較。

## 範例分布

![Spray angle histograms](../images/spray_angle_hists.png)
