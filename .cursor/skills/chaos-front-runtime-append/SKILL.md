---
name: chaos-front-runtime-append
description: >-
  Appends Chaos Front units/characters/portraits at runtime via BepInEx Harmony
  (clone tables, LanguageData names, unlock, sprite swap). Use when adding
  UnitType/Character rows, fixing AmbiguousMatch/InitShop/Show recursion, or
  extending CfGundamMod ID allocation for batch imports.
---

# Chaos Front 运行时追加（表 + Harmony）

## 容量与策略

| 表 | 静态容量（约） | 策略 |
|----|----------------|------|
| UnitType | 256 | 追加新 id，克隆模板 |
| Character | 2048 | 追加；飞行员 `type` 与模板一致 |
| Language / menu 名 | 8192 | **显示名必须追加 Language 再挂索引** |
| Portrait Shift | 需扩表 | vanilla portrait 约到 169；新 id 要扩 `portraitShiftTable` |

**禁止**覆盖 1–92 等玩家已有内容。v1 纹理注入进 assets 曾不稳定 → 现行方案是 **运行时换 Sprite**。

## 已占用示例 id（批量时从此错开）

| 用途 | Id | 模板 |
|------|-----|------|
| RX-78-2 unit | 93 | unit 31（小型） |
| 扎古Ⅱ unit | 94 | unit 31（小型） |
| 艾尔梅斯 unit | 95 | unit **50**（大型 size=1） |
| 白色木马 unit | 96 | unit **12**（战略母舰 size=2 / kind=1） |
| 阿姆罗 character | 1121 | character 102，portrait 170 |
| 夏亚 character | 1122 | character 102，portrait 171 |
| 拉拉 character | 1123 | character 102，portrait **172** |


新内容：unit `97+`，character `1124+`，portrait `173+`（或维护 `catalog` 统一分配）。

## 语言表（易错）

`LanguageCollect` 约定不一致：

| API | 行为 |
|-----|------|
| `SetMenuName(i, data)` | 写入 `menuName[i]`（**0-based**） |
| `GetMenuName(i)` | 读取 `menuName[i - 1]`（**1-based**，且 `i<=0` 无效） |
| `UnitTypeData.name` / `Character.name` | 存 **1-based** id |

追加字符串时：在数组空位 `slot` 写入后，**返回 `slot + 1`** 给表字段。  
返回 `slot` 会导致全体名字错位一格（阿姆罗显示扎古简介等）。

## 追加顺序

1. Language 字符串行（名、简介）——按上表返回 1-based id  
2. UnitType 克隆 + 改 name/info 索引、model/icon  
3. Character 克隆 + `portrait = 新 id`  
4. `EnsurePortraitShift(portraitId)`  
5. （可选）解锁 + 加入空闲驾驶员列表  

入口：`plugins/CfGundamMod/GundamContent.cs`。


## Harmony 坑（已踩过）

| 症状 | 原因 | 处理 |
|------|------|------|
| 补丁一半没挂上 | 一次 Patch 全程序集遇 `AmbiguousMatch` | 按类 `CreateClassProcessor` + try/catch |
| 商店打开崩 | `InitShop` 参数名猜错 | 用真实签名（`s`, `order` 等） |
| 硬崩溃 / 栈溢出 | `ApplyUnitIcon` 内再 `Show` | 只改 sprite/rect，加 `_applyingUnit` 守卫 |
| 立绘全黑 | Shift 过大或艺术区出窗 | 见 portrait skill；Shift 小步调 |
| 立绘只改一处 | 只在 `replace:true` 写 Shift | 与 `PortraitController.Show` 行为一致 |
| 全体串名 / 名字错位一格 | 返回了 0-based slot | **返回 `slot+1`**（GetMenuName 为 1-based） |
| 两机编队条高低不齐 | 各 PNG 内容中心 y 不一致 | 对齐基准机 cy≈38–40，调 PIL `y_off`（默认 7） |

## 文件部署

```text
BepInEx/plugins/CfGundamMod.dll
BepInEx/plugins/CfGundamMod/          ← ContentDir（DLL 文件名旁边的文件夹）
    portrait-amuro.png
    unit-rx78.png
    …批量后多文件…
BepInEx/config/com.chaosfront.gundammod.cfg
```

`TextureCache.ContentDir` = `dirname(dll) + "/CfGundamMod"`。  
工程侧源文件：`plugins/CfGundamMod/content/`，用脚本同步到游戏目录。

## 批量改造要点

把 `Plugin` 里单个 `UnitId`/`CharacterId`/`PortraitId` 升级为清单循环：

- 加载 `content/catalog.json`
- `EnsureTables` foreach 追加
- `VisualPatches` / `TextureCache` 用 `Dictionary<int, Sprite>`
- 配置保留「总开关」即可，细项进清单

未完成查表前，每加一台就改代码可接受，但 skill **batch-import** 要求优先做查表。

## 验证日志关键词

- `Patched CfGundamMod.Patches...`
- `Set Character 1121` / `portrait=170`
- `Using pre-sized portrait 200x160` / `Loaded source portrait-amuro`
- `Applied unit icon 64x64`
