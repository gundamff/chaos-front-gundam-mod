---
name: chaos-front-unit-icon
description: >-
  Composes Chaos Front unit and warship UI icons to 64x64 matching vanilla
  hex/shop scale (~40px art, mild drop). Use when making unitIcon PNGs,
  fixing icons too big/small/high/low/short-fat, or aligning with vanilla
  formation-strip units.
---

# Chaos Front 机体 / 战舰图标（64×64）

## 原版事实（已核实）

| 项 | 原版 | 说明 |
|----|------|------|
| 画布 | **64×64** | UI 六角 / `unitIcon*` prefab |
| 资源来源 | 多半复用 **`mapUnit*` 格精灵** | 不是另一套更大贴图 |
| 机甲像素（紧包围） | 约 **28～50** 一边 | 常见 MS / 舰约 **35～45** |
| 落点 | 略偏下进六角底 | 脚靠近六角下沿，头顶留空 |

我们的 `unit-*.png` 是**单独合成**的 64×64，要**视觉对齐**原版：长边约 **38～42**，bbox 中心 **cy ≈ 38～40**。

## 默认合成参数

脚本：`tools/process_genesis_oyw.py` → `compose_unit_64`

| 参数 | 默认 | 含义 |
|------|------|------|
| `art` | **40** | 长边目标 px（舰/MA 可用 42） |
| `y_off` | **7** | PIL 向下偏移（进六角底） |
| `nudge_x` | **-1** | 略左，减轻 SD 侧脸「偏右」观感 |

运行时：`TextureCache` 若 PNG 已是 64×64 → **直接用**（不再二次缩放）；否则才走 `UnitArtSize=28` / `UnitArtYOffset=-10`。

```python
compose_unit_64(src, art=40, y_off=7, nudge_x=-1)
```

## 坐标（易错）

| 环境 | y=0 | 正偏移含义 |
|------|-----|------------|
| PIL 出图 | **顶** | `y_off>0` → 图往**下** |
| Unity blit | **底** 常见 | `UnitArtYOffset<0` → 视觉往**下** |

同一「往下一点」：脚本加大正 `y_off`；C# 让 Y 更负。**不要两边同号照抄。**

调参口诀：

- 编队条里**偏上** → 增大 `y_off`
- **偏下 / 贴底** → 减小 `y_off`
- **显小** → 增大 `art`（先试 40→42；>44 易顶破六角）
- **显大 / 裁切** → 减小 `art`

## 选源帧（坑）

| 用途 | 该用 | 禁用 |
|------|------|------|
| 商店 / 编队图标 | **正面站姿**（`*-front-raw.png` 或已定稿的 `unit-*-64.png` 源） | 地图**移动 / 前倾 / 迈步**帧（如 `rx78_map_fr6`） |
| 地图 `troopSprite` 静止 | **站姿四向**（正面用 `*-front-raw`，背面用后视站姿） | 冲刺/迈步帧（`fr6` 等）— CF atlas 无独立 walk 轨，idle 也是这四格 |

CF `sprites[color*4+dir]` 只有四向；图集里塞站姿，静止就站着。要「移动才迈步」需另做双套精灵 + 运行时切帧（尚未做）。

用户能一眼看出「换了移动版」——图标姿势必须稳定站姿。

## 禁止二次压缩

**不要**对已经合成好的 `unit-*.png` / `unit-*-64.png` 再跑一遍 `compose_unit_64`（会再 `trim`+缩放 → **矮胖**）。

只改位置时：

```python
# 从定稿 64 图裁出不透明区，平移，禁止再按 art 缩放
art = trim_alpha(old_64)
canvas.paste(art, (new_x, new_y))  # 尺寸不变
```

要改大小：必须从**高分辨率源**（`*-front-raw` / Genesis 切帧）重新 `compose_unit_64`。

## 合成步骤

1. 取正面站姿源，`trim_alpha`。
2. `compose_unit_64(..., art=40, y_off=7, nudge_x=-1)`。
3. 量 bbox：`w/h` 长边 ≈ 38–42，`cy ≈ 38–40`。
4. 透明底 PNG → `plugins/CfGundamMod/content/unit-<name>.png`。
5. 复制到 `BepInEx/plugins/CfGundamMod/`，**重启游戏**验收（图标有缓存）。

## 多机体对齐

编队条并排时以已调好的基准机（如 RX-78）为准：

1. 量 `cy = (miny+maxy)/2`、长边。
2. 新机 cy 差 > ~2px → 调 `y_off`；长边差明显 → 调 `art`。
3. 切帧须含完整头顶（行高不够会「没头皮」）。

## 战舰 / MA

流程相同。舰体更扁：`art=42` 往往更接近原版舰占位；仍用 `y_off=7` 作起点。

## Harmony 注意

- `ApplyUnitIcon` **禁止**再调 `ImageController.Show` → Postfix 递归爆栈。
- `Resources.Load(.../unitIcon{id})` 与商店 `InitShop`：按 **catalog id → PNG** 查表替换。
- 商店参数是 `s/order`（不是 `size/num`）。
- 补丁按**类** `CreateClassProcessor`，避免一个 `AmbiguousMatch` 毁掉全部 Patch。

## 验收清单

- [ ] 与上方 vanilla 机体**大小接近**（不明显偏小/偏大）
- [ ] 垂直落点接近原版（不贴顶、不悬空过高、不踩穿六角底）
- [ ] 姿势是站姿，不是移动帧
- [ ] 比例正常（无矮胖 = 无二次缩放）
- [ ] 商店六角 + 编队条都正常
