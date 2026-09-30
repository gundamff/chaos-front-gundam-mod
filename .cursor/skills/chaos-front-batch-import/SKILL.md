---
name: chaos-front-batch-import
description: >-
  Orchestrates batch import of Chaos Front Gundam-mod pilots, mobile suits, and
  warships (runtime table clone + CF-sized PNGs + BepInEx deploy). Use when the
  user asks to bulk-add 驾驶员/人, 机体/MS, 战舰/舰, or to extend CfGundamMod beyond
  RX-78/Amuro.
---

# Chaos Front 批量导入（人 / 机体 / 战舰）

## 何时用本 skill

- 一次加多个驾驶员、MS、战舰
- 从 Genesis / Spriters / 其他素材批量出图并挂进模组
- 不确定先改表、先出图、还是先部署

配套专项 skill（按需 Read）：

| 类型 | Skill |
|------|--------|
| 驾驶员立绘 | [chaos-front-portrait](../chaos-front-portrait/SKILL.md) |
| 机体/战舰图标 | [chaos-front-unit-icon](../chaos-front-unit-icon/SKILL.md) |
| 运行时表与 Harmony | [chaos-front-runtime-append](../chaos-front-runtime-append/SKILL.md) |

尺寸与 Shift 常数见 [sizes.md](sizes.md)。

## 铁律（批量前先过一遍）

1. **只追加，不覆盖** vanilla id（unit 1–92、既有 character/portrait）。
2. **一名一 portrait id**；sprite 运行时替换，不是往 `resources.assets` 写 Texture2D。
3. **立绘不要铺满 200×160**（Genesis 特写铺满 → 任命格只剩眼睛）。见 portrait skill。
4. **PIL y=0 在顶；Unity Texture/UI y 常相反** — 出图脚本与 `TextureCache` 偏移符号不要混用。
5. 改 PNG 后必须部署到 `BepInEx/plugins/CfGundamMod/`，并让用户**重启游戏**（贴图有缓存）。

## 单条内容清单

每条导入物至少准备：

```text
- kind: pilot | ms | ship
- display_name / info（中文）
- clone_from: 模板 unit 或 character id
- new_ids: unit? / character? / portrait?
- source_art: 路径
- outputs:
    - portrait-*.png  (pilot only, 200x160)
    - unit-*.png      (ms/ship, 64x64)
```

## 推荐流水线

```text
Task Progress:
- [ ] 1. 分配 id（见 runtime-append + sizes.md）
- [ ] 2. 出图（portrait / unit-icon skill）
- [ ] 3. 写入 content 清单 + 扩展 GundamContent / 配置（勿只改单例硬编码就宣称可批量）
- [ ] 4. 部署 DLL + PNG 到游戏目录
- [ ] 5. 重启验收：商店六角标、任命 48 格、编队条立绘、地图单位
```

### 驾驶员（人）

1. `character` 克隆自 Type=1 飞行员模板（现用 `102`）。
2. 新 `portrait` id（≥170 起自行递增），`EnsurePortraitShift`。
3. 按 **chaos-front-portrait** 做 `200×160`，艺术区约 `72×88`、`top_pad≈32`。
4. Harmony：`PortraitController.Show` → 换 sprite；`replace==true` 才写 Shift。

### 机体（MS）

1. `unitType` 克隆自接近定位的模板：
   - **小型** `size=0`：如 `31`（异形斗兵）
   - **大型** `size=1`：如 `50`（天使长）——商店走「大型」页 / `UnlockedLArms`
   - **舰船** `size=2` + `kind=1`：见战舰节
2. 按 **chaos-front-unit-icon** 做 `64×64`（`art=40,y_off=7`），并与基准机 cy≈38–40 对齐。
3. Harmony：`Resources.Load` / 商店 `InitShop` 已按 catalog id 查表。

### 战舰

1. 与机体同一套 unit 表；**clone_from 必须选舰船模板**（不要用 MS 模板硬套航速/体型）。
2. 图标仍走 `64×64`；艺术比例可略扁/略宽，但仍居中、略偏下进六角底。
3. 无 portrait，除非同时加舰长驾驶员。

## 批量时的代码形态（目标）

当前插件仍是「单机 RX-78 + 单人阿姆罗」。批量前先把硬编码改成数据驱动，再加条目：

- 清单文件（建议）：`plugins/CfGundamMod/content/catalog.json` 或 `content/*.yaml`
- 字段：`unitId, unitCloneFrom, charId, charCloneFrom, portraitId, names, png 文件名, shift`
- `GundamContent.EnsureTables` 循环清单追加
- `TextureCache` 按 id 缓存多张 sprite（不要全局单例一张）

未改成查表前，**不要**宣称已支持批量；先做结构再灌数据。

## 验收口令

| 界面 | 通过标准 |
|------|----------|
| 商店 / 地图六角 | 机体完整、不飞出框、不过分偏上 |
| 任命 3×3 | 头+肩可见，不是半只眼 |
| 编队右侧条 | 能认出脸，不是一条白边或全黑 |
| 名单/语言 | 显示中文名，不是模板名 |

## 游戏路径（本机默认）

- 游戏：`F:/SteamLibrary/steamapps/common/Chaos Front`
- 插件内容：`.../BepInEx/plugins/CfGundamMod/`（DLL 在 `plugins/CfGundamMod.dll` 时，ContentDir 为同级文件夹 `CfGundamMod/`）
- 工程内容源：`plugins/CfGundamMod/content/`
- 出图脚本：`tools/process_genesis_oyw.py`（可推广为通用 compose）
