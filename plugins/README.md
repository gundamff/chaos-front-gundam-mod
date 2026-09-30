# Chaos Front Gundam Mod — BepInEx plugin

与 [Snrasha 社区](https://snrasha.github.io/chaosfront/plugins.html) 同框架：**BepInEx 5 + DLL**，不改 `resources.assets`，游戏更新后仍有效。

## 当前版本 0.3.0

启动后自动：

1. **克隆机体** `31 → 93`（RX-78-2），`model/icon=93`  
2. **克隆驾驶员** `102 → 1121`（阿姆罗），`portrait=170`  
3. 写入语言名；读档解锁机体 + 加入飞行员名单  
4. **贴图**：`Resources.Load(unitIcon93)` 回落模板后换成 SD 图标；`PortraitController.Show(170)` 换成阿姆罗立绘  

贴图文件（与 DLL 一同部署）：

`BepInEx/plugins/CfGundamMod/unit-rx78.png`  
`BepInEx/plugins/CfGundamMod/portrait-amuro.png`

## 构建部署

```powershell
cd D:\eclipse\git\chaos-front-gundam-mod\plugins\CfGundamMod
dotnet build -c Release
```

输出：`Chaos Front\BepInEx\plugins\CfGundamMod.dll`

## 验证

1. 关游戏 → 确认插件存在 → 开游戏  
2. 看 `BepInEx\LogOutput.log`，应有类似：

```
Chaos Front Gundam Mod 0.3.0 Awake
Set model/icon=93 for texture swap
set portrait=170 for texture swap
Resources.Load ...unitIcon93 → unitIcon31 (sprite swap pending)
Applied unit icon sprites on ...
Loaded sprite portrait-amuro ...
```

3. 进 5 号档（或任意档）→ 工厂应能买到 **RX-78-2** → 空闲飞行员有 **阿姆罗**

## 配置

`BepInEx\config\com.chaosfront.gundammod.cfg`

| 键 | 默认 | 含义 |
|----|------|------|
| Content.Enable | true | 总开关 |
| Content.AutoUnlockAndRoster | true | 读档/新游戏自动解锁+加人 |
| Content.UnitId / UnitCloneFrom | 93 / 31 | 机体 |
| Content.CharacterId / CharacterCloneFrom | 1121 / 102 | 驾驶员 |
| Content.UnitName / CharacterName | RX-78-2 / 阿姆罗 | 显示名 |

## 路线图

| 版本 | 状态 |
|------|------|
| 0.1 加载 + API dump | 完成 |
| 0.2 运行时追加机体/驾驶员 | 完成 |
| **0.3 运行时替换 icon / portrait** | **当前** |

## 与离线 cf_patch 的关系

- **优先用本 DLL**（抗更新）  
- 离线改 `resources.assets` 会被 Steam 更新抹掉，且易与存档 ID 不一致导致黑屏  
