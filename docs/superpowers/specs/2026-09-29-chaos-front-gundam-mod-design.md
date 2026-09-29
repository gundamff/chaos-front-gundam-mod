# Chaos Front 高达 Mod（竖切）— 设计文档

日期：2026-09-29  
状态：待用户审阅后进入 implementation plan  
路径：标准通道 / Superpowers brainstorm → writing-plans

## 1. 背景与目标

《Chaos Front》（ChaosGalaxyStudio，Unity Mono）机体表现为 **92 种（ID 1–92）**，素材主要在 `Chaos Front_Data/resources.assets`。先前在 `chaos-front-save-editor` 中已验证：

- `UnitTypeData` / `CharacterData` / `LanguageData` 等 TextAsset（XML）
- 地图机体精灵 `mapUnit<model>`（且现表 `model === id`）
- 驾驶员头像 `portraitN`
- 存档为 Easy Save 3 明文 JSON；解锁机体靠 `PlayerUnlockedUnitTypes`

本仓库目标：用《SD 高达 G 世代 Advance》汉化 ROM 导出素材，**追加**高达机体与驾驶员（**不替换**原作内容）。

### v1 成功标准（竖切）

追加 **1 台机体 + 1 名驾驶员**，并满足：

1. 游戏启动无报错，原作机体仍正常  
2. 存档注入后：编队可见 RX-78-2 图/名与阿姆罗头像/名  
3. 可上地图、可进战斗（不崩溃即可）  
4. 解锁后工厂能购买机体 93（若有额外门槛，只做最小补齐）  
5. 提供 `resources.assets` 一键还原  

### 明确不做（v1）

- 新武器 / 新能力表项、平衡调整  
- 剧情招人事件链（驾驶员以存档注入为准）  
- 批量机体、BepInEx / 运行时注入  
- 公开分发 ROM 或版权素材  

### 后续范围（同一管线，非 v1）

- **战舰**：追加 `kind=1` 条目 + 对应 `model` 贴图 + 解锁/存档注入（不另起架构）  
- 批量 UC 机体、运行时框架、武器表移植：竖切通过后再开  

## 2. 决策摘要

| 议题 | 选择 |
|------|------|
| 内容策略 | 追加，不替换 |
| v1 范围 | 竖切：RX-78-2 + 阿姆罗 |
| 装入方式 | 先离线改包验证；注入框架后置 |
| 素材源 | 仓库内 GBA ROM，工具自行导出 |
| 战斗数据 | 克隆原作小型机体数值与武器/能力 ID |
| 验收获取 | 游戏数据可解锁购买 **且** 存档一键注入 |
| 技术路线 | 原地改 `resources.assets`（UnityPy 优先） |

## 3. 仓库架构

```
chaos-front-gundam-mod/
├── rom/                    # .gitignore：GBA ROM
├── raw/                    # .gitignore：GBA 导出中间产物
├── assets/                 # 已适配的 PNG + manifest（可提交样例，不含 ROM）
├── patches/                # 声明式补丁（新机体/驾驶员字段、克隆模板 id）
├── tools/
│   ├── gba_export/         # ROM → raw/assets
│   ├── cf_patch/           # 备份并原地改 Chaos Front 资源
│   └── save_inject/        # ES3 存档追加机体+驾驶员+解锁
├── backups/                # .gitignore：游戏文件备份
├── docs/superpowers/specs/
└── README.md               # 本地自用说明 + 版权免责（不附 ROM）
```

三条管线用文件交接、互不耦合：

| 管线 | 输入 | 输出 |
|------|------|------|
| GBA 导出 | `rom/*.gba` | `raw/` + 适配后 `assets/` |
| CF 补丁 | `patches/` + `assets/` + 游戏目录 | 已备份的改包游戏 |
| 存档注入 | `.cf` 路径 + 新 ID | 可上阵存档 |

## 4. 数据模型

### 4.1 ID 分配（实施时再扫实表确认）

| 实体 | 新 ID | 依据 |
|------|-------|------|
| `unitType` | 93 | 现表 1–92 连续 |
| `model` | 93 | 绑定 `mapUnit93`（含子帧如 `_0`） |
| 驾驶员 | 1121 | 现角色 max≈1120；不用 942–1000 空洞 |
| `portrait` | 170 | 现 portrait max≈169 → `portrait170` |

显示名：「RX-78-2」「阿姆罗」优先取自汉化 ROM 字符串；失败则在 `patches/` 写死中文。

### 4.2 机体（追加一条）

- **克隆模板**：原作小型机体 `id=31`「异形斗兵」（`kind=2, size=0, levelType=4, weapon1=7, ability1=16` 等）
- **覆盖**：`id`/`model`=93，`name`/`info` 为高达文案  
- **不新增** `WeaponData` / `AbilityData`

### 4.3 驾驶员（追加一条）

- 克隆一名原作角色（优先 `joinLv` 低、技能少）  
- **覆盖**：`id=1121`，`portrait=170`，名/简介  
- **不新增** Skill/Talent 表项  

### 4.4 解锁与出现

**存档侧（主验收加速）：**

- `PlayerUnlockedUnitTypes` 加入 93  
- `PlayerCharacters` / `PlayerCharacterEXPs` 追加 1121  
- `PlayerUnits` 追加：`unitType=93, characterId=1121, armyId=PlayerArmyId`，`exp` 取合理默认  

**游戏数据侧（证明正道）：**

- 表内可读 93 / 1121  
- 已解锁时工厂可列出并购买；招人事件链不纳入 v1  

### 4.5 战舰（后续）

同一 append 模型：新 `unitType` + `model`，克隆原作 `kind=1` 模板，补齐船坞/地图贴图槽；存档解锁字段与机体相同路径。

## 5. 管线步骤

### 阶段 0：环境与备份

1. 配置游戏根目录（默认 `F:\SteamLibrary\steamapps\common\Chaos Front`）  
2. 补丁前复制将修改的 `resources.assets` / `.resS` / 相关 `sharedassets*` → `backups/<timestamp>/`  

### 阶段 1：GBA 导出

1. 只读打开 `rom/*.gba`（当前：`SD高达G世纪A汉化2.0_存档修复.gba`）  
2. 导出 RX-78-2、阿姆罗精灵/头像与中文名 → `raw/`  
3. 生成适配尺寸的 `assets/unit-93.png`、`assets/portrait-170.png` 与 `assets/manifest.json`  
4. **降级**：ROM 解析卡住时允许占位 PNG，仍填写目标槽名，优先打通 CF 侧  

### 阶段 2：CF 原地补丁

1. UnityPy（优先）打开 `Chaos Front_Data/resources.assets`  
2. 解析并扩写 `UnitTypeData` / `CharacterData`（若名称走索引则含 `LanguageData`）  
3. 写入 Texture2D / Sprite：`mapUnit93*`、`portrait170`（对照原作 `mapUnit31` / 既有 portrait 元数据复刻）  
4. 写回；校验机体条数与角色 maxId  
5. 提供 `restore` 从备份还原  

### 阶段 3：存档注入

1. 复用 save-editor 的 ES3 读写思路（精简脚本，不强制 Electron）  
2. 对指定 `savedataN.cf`：备份 → 解锁 → 追加角色与机体  
3. 结构异常则拒绝写入  

### 阶段 4：人工验收

按 §1 五条清单执行；工厂失败则只补最小缺失条件。

## 6. 风险与应对

| 风险 | 应对 |
|------|------|
| IL 写死机体/角色上限 | 竖切首要验证点；失败则记录证据，改评估运行时注入 |
| 贴图进包但不显示 | 逐项复刻原作 Sprite/图集引用 |
| 名字乱码或不显示 | 确认内嵌 XML vs `LanguageData` 索引 |
| GBA 导出困难 | 占位图先通 CF；GBA 并行完善 |
| Steam 校验覆盖 | README 说明本地改包与 `restore` |
| 版权 | ROM/素材不入库、不公开分发；仅个人学习 |

## 7. 命令面（预期）

实施计划中落地为可重复命令，示意：

```text
python -m tools.gba_export --rom rom/...gba --out assets
python -m tools.cf_patch --game "F:\...\Chaos Front" --patch patches/v1-rx78.yaml
python -m tools.cf_patch --restore backups/<timestamp>
python -m tools.save_inject --save "...\savedata0.cf" --unit 93 --character 1121
```

具体 CLI 以 implementation plan 为准。

## 8. 里程碑

1. GBA 导出或占位图 + manifest  
2. CF 补丁可追加表项 + 贴图 + restore  
3. 存档注入可重复  
4. 进游戏五项验收全过  
5. （后续）战舰竖切复用同一工具链  

## 9. 版权与发布边界

- 本工具链仅供已合法持有《Chaos Front》与素材来源 ROM 的用户 **本地** 使用  
- 仓库 **不** 包含 ROM、完整导出图集或可再分发的万代/官方素材包  
- 与 ChaosGalaxyStudio / 万代南梦宫等无关联、无授权
