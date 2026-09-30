# Chaos Front 模组尺寸与路径速查

## 立绘 portrait

| 常数 | 值 |
|------|-----|
| 画布 | 200×160 |
| Genesis 类特写艺术区 | max ≈ 72×88 |
| top_pad | ≈ 32 |
| 默认 Shift | X=4, Y=-15 |
| 任命遮罩 | ≈ 48×48（预制体 + Shift） |

**不要**把特写脸铺满 200×160。

## 机体 / 战舰 unitIcon

| 常数 | 值 |
|------|-----|
| 画布 | 64×64 |
| 艺术边长 `art` | **40**（舰/MA 可 42） |
| PIL `y_off` | **7**（起点）；对齐基准机内容中心 **cy ≈ 38～40** |
| Unity `UnitArtYOffset` | 仅非 64 回退路径用 -10；已是 64×64 的 PNG 直接用 |

详见 [chaos-front-unit-icon](../chaos-front-unit-icon/SKILL.md)。禁止对已合成 64 图二次 `compose`（会矮胖）；图标用正面站姿，不用地图移动帧。

**水平线：** 多机并排时先量 `unit-rx78.png` 的 cy，再调新机 `y_off`，不要凭感觉。

## 语言 id（必读）

| API | 约定 |
|-----|------|
| `SetMenuName(i)` | 写 `menuName[i]`（0-based） |
| `GetMenuName(i)` | 读 `menuName[i-1]`（**1-based**） |
| 表字段 `name`/`info` | 存 **1-based** → Append 后返回 `slot+1` |

错成 0-based 会全员串名（阿姆罗显示扎古简介等）。详见 `chaos-front-runtime-append`。

## 目录

| 用途 | 路径 |
|------|------|
| 工程 PNG | `plugins/CfGundamMod/content/` |
| 出图脚本 | `tools/process_genesis_oyw.py` |
| Genesis 源 | `raw/Nintendo Switch - SD Gundam G Generation Genesis/...` |
| 处理后预览 | `raw/genesis_processed/` |
| 游戏插件内容 | `F:/SteamLibrary/steamapps/common/Chaos Front/BepInEx/plugins/CfGundamMod/` |
| 游戏 DLL | `.../BepInEx/plugins/CfGundamMod.dll` |

## 已用 id

| 内容 | id |
|------|-----|
| RX-78-2 | unit **93**（小型 size=0，模板 31） |
| 扎古Ⅱ | unit **94**（小型 size=0，模板 31） |
| 艾尔梅斯 | unit **95**（**大型 size=1**，模板 **50** 天使长） |
| 阿姆罗 | character **1121**，portrait **170** |
| 夏亚 | character **1122**，portrait **171** |
| 拉拉 | character **1123**，portrait **172** |
| 克隆模板 | 小型 unit 31；大型 unit 50；character 102 |

**Size 约定：** `UnitTypeData.size` — `0` 小型商店页、`1` 大型页、`2` 舰船。大型机必须 `cloneFrom` 带 `Size=1` 的模板（或克隆后改 size）。


清单文件：`plugins/CfGundamMod/content/catalog.json`（再加条目即可批量）。

