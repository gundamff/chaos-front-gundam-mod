---
name: chaos-front-portrait
description: >-
  Composes Chaos Front pilot portraits to 200x160 with ~72x88 art for the ~48
  UI mask and formation strip, including PortraitData Shift pitfalls. Use when
  processing pilot faces, 立绘, portrait PNGs, Amuro/Genesis portraits, or when
  portraits show only an eye, black strip, or float too high/low.
---

# Chaos Front 驾驶员立绘（200×160）

## 目标尺寸

| 项 | 值 | 说明 |
|----|-----|------|
| 画布 | **200×160** RGB/黑底 | 作者与 vanilla `portrait*` 一致 |
| 艺术区（Genesis 类特写） | **约 72×88** | 头肩，不是铺满 |
| top_pad | **约 32** | 头盔勿贴顶；再往下就加大 pad |
| 默认 Shift | **(4, -15)** | 对齐 portrait1；仅 `Show(..., replace:true)` 时写入 |

权威实现：`tools/process_genesis_oyw.py` → `compose_portrait_200x160`；运行时回退常数在 `TextureCache`（预烘焙 200×160 则直通不缩放）。

## 为什么不能「按原版铺满」

Vanilla 立绘看起来铺满，是因为**画师画的就是适遮罩的胸像**。

Genesis / 现代高清脸模是**头盔特写**：

| 错误做法 | 任命 48 格 | 编队条 |
|----------|------------|--------|
| 艺术区 ≥140px 铺满 | 只剩半只眼 | 只剩盔顶一条 |
| 艺术区过小且偏上 | 头贴顶、底下大块黑 | 可能全黑或一条边 |
| **~72×88 + pad≈32** | 完整头脸 | 可辨认 |

用户反馈口令：

- 「太大了 / 半只眼」→ 缩小 `max_w/max_h`
- 「再往下」→ 增大 `top_pad`（或 ShiftY 往 0 调，优先改图）
- 「全黑」→ 艺术区落在遮罩窗外，或 Shift 过大（曾试过 52,-40 直接黑）

## 合成步骤

1. `trim_alpha` 去透明边。
2. `scale = min(72/w, 88/h)`，LANCZOS 缩放。
3. 水平居中，可 `nudge_x≈2`；`dy = top_pad`。
4. 贴到 200×160 黑底 RGB（CF 侧按不透明底处理更稳）。
5. 存 `portrait-<name>.png`，部署到 `BepInEx/plugins/CfGundamMod/`。

```python
# 与 tools/process_genesis_oyw.py 保持一致
compose_portrait_200x160(src, top_pad=32, max_w=72, max_h=88, nudge_x=2)
```

## 运行时规则（Harmony）

- 只换 `Image.sprite`，**不要** `ForceRect` 立绘（各面板自己管 48 遮罩 / 长条）。
- `replace==true` → `anchoredPosition = PortraitShift`；`replace==false` → 保留预制体位置。
- 新 portrait id 必须 `EnsurePortraitShift`（扩展 `portraitShiftTable`），vanilla 表只到 169。
- 预烘焙已是 200×160：**禁止**再在 `BuildPortraitSprite` 里二次缩放。

## 调参顺序

1. 先改 PNG 构图（大小 / pad / 水平 `nudge_x`）。
2. 重启游戏看任命格 + 编队条。
3. 仍整体偏位再改 catalog `shiftX/Y`（小步 ±4～8）。

夏亚类侧面盔：`nudge_x` 勿一次拉太大（-16 会整脸贴左）；先 0，再 ±4。

## 批量

每驾驶员：独立 portrait id + 独立 PNG + 可选独立 Shift。  
全局单例 `_portraitSprite` 不够用时，先改 `TextureCache` 为按 id 字典，再灌清单（见 batch-import skill）。
