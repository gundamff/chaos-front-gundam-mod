using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;

namespace CfGundamMod
{
    /// <summary>
    /// Runtime append from content/catalog.json into Informations + LanguageCollect.
    /// Capacities: unitTypeNum=256, characterNum=2048, menuNameNum=8192.
    /// </summary>
    internal static class GundamContent
    {
        private static bool _tablesReady;
        private static readonly object Gate = new object();

        public static void EnsureTables()
        {
            if (!Plugin.EnableContent.Value)
                return;

            lock (Gate)
            {
                if (_tablesReady)
                    return;

                try
                {
                    ContentCatalog.EnsureLoaded();
                    ApplyTables();
                    _tablesReady = true;
                }
                catch (Exception ex)
                {
                    Plugin.Log.LogError($"EnsureTables failed: {ex}");
                }
            }
        }

        public static void EnsurePlayData(PlayData play)
        {
            if (!Plugin.EnableContent.Value || !Plugin.AutoUnlockAndRoster.Value)
                return;

            if (play == null)
                play = GetPlayDataInstance();
            if (play == null)
            {
                Plugin.Log.LogWarning("EnsurePlayData: PlayData.instance is null");
                return;
            }

            EnsureTables();

            try
            {
                ContentCatalog.EnsureLoaded();

                if (play.unlockedUnitTypes == null)
                    play.unlockedUnitTypes = new List<int>();
                foreach (var u in ContentCatalog.Units)
                {
                    if (u == null || u.id <= 0)
                        continue;
                    if (!play.unlockedUnitTypes.Contains(u.id))
                    {
                        play.unlockedUnitTypes.Add(u.id);
                        Plugin.Log.LogInfo($"Unlocked unitType {u.id} ({u.name})");
                    }
                }

                if (play.characters == null)
                    play.characters = new List<int>();
                foreach (var c in ContentCatalog.Characters)
                {
                    if (c == null || c.id <= 0)
                        continue;
                    if (!play.characters.Contains(c.id))
                    {
                        play.characters.Add(c.id);
                        Plugin.Log.LogInfo($"Added character {c.id} ({c.name}) to roster");
                    }
                }
            }
            catch (Exception ex)
            {
                Plugin.Log.LogError($"EnsurePlayData failed: {ex}");
            }
        }

        public static PlayData GetPlayDataInstance()
        {
            return Traverse.Create(typeof(PlayData)).Field("instance").GetValue<PlayData>();
        }

        private static void ApplyTables()
        {
            var info = Informations.Instance;
            if (info == null)
                throw new InvalidOperationException("Informations.Instance is null");

            foreach (var s in ContentCatalog.Skills)
            {
                if (s == null || s.id <= 0)
                    continue;

                EnsureSkillSlot(info, s.id);

                var template = info.GetSkill(s.cloneFrom);
                if (template == null)
                    throw new InvalidOperationException($"Template skill {s.cloneFrom} missing for {s.name}");

                int nameIdx = AppendLanguage(s.name ?? $"Skill{s.id}");
                int infoIdx = AppendLanguage(s.info ?? "");

                var existing = info.GetSkill(s.id);
                if (existing != null && existing.id == s.id)
                {
                    existing.name = nameIdx;
                    existing.info = infoIdx;
                    existing.type = template.type;
                    existing.sp = template.sp;
                    info.SetSkill(s.id, existing);
                    Plugin.Log.LogInfo($"Skill {s.id} updated ({s.name})");
                }
                else
                {
                    var cloned = new Skill
                    {
                        id = s.id,
                        name = nameIdx,
                        info = infoIdx,
                        type = template.type,
                        sp = template.sp,
                    };
                    info.SetSkill(s.id, cloned);
                    Plugin.Log.LogInfo($"Set Skill {s.id} ({s.name}, clone of {s.cloneFrom})");
                }
            }

            foreach (var u in ContentCatalog.Units)
            {
                if (u == null || u.id <= 0)
                    continue;

                var template = info.GetUnitTypeData(u.cloneFrom);
                if (template == null)
                    throw new InvalidOperationException($"Template unit {u.cloneFrom} missing for {u.name}");

                // Always allocate fresh language rows — never reuse possibly-wrong indices
                // from a previous broken AppendLanguage pass.
                int nameIdx = AppendLanguage(u.name ?? $"Unit{u.id}");
                int infoIdx = AppendLanguage(u.info ?? "");

                var existing = info.GetUnitTypeData(u.id);
                if (existing != null && existing.id == u.id)
                {
                    existing.name = nameIdx;
                    existing.info = infoIdx;
                    existing.model = u.id;
                    existing.icon = u.id;
                    info.SetUnitTypeData(u.id, existing);
                    Plugin.Log.LogInfo($"Unit {u.id} updated nameLang={nameIdx} infoLang={infoIdx} ({u.name})");
                }
                else
                {
                    var cloned = CloneUnit(template, u.id, nameIdx, infoIdx);
                    info.SetUnitTypeData(u.id, cloned);
                    Plugin.Log.LogInfo($"Set UnitTypeData {u.id} ({u.name}, clone of {u.cloneFrom}, nameLang={nameIdx})");
                }
            }

            foreach (var c in ContentCatalog.Characters)
            {
                if (c == null || c.id <= 0)
                    continue;

                var template = info.GetCharacter(c.cloneFrom);
                if (template == null)
                    throw new InvalidOperationException($"Template character {c.cloneFrom} missing for {c.name}");

                int nameIdx = AppendLanguage(c.name ?? $"Char{c.id}");
                int infoIdx = AppendLanguage(c.info ?? "");

                var existing = info.GetCharacter(c.id);
                if (existing != null && existing.id == c.id)
                {
                    existing.name = nameIdx;
                    existing.info = infoIdx;
                    existing.portrait = c.portraitId;
                    ApplyCharacterLoadout(existing, c, template);
                    info.SetCharacter(c.id, existing);
                    Plugin.Log.LogInfo($"Character {c.id} updated nameLang={nameIdx} portrait={c.portraitId} ({c.name})");
                }
                else
                {
                    var cloned = CloneCharacter(template, c.id, nameIdx, infoIdx, c.portraitId);
                    ApplyCharacterLoadout(cloned, c, template);
                    info.SetCharacter(c.id, cloned);
                    Plugin.Log.LogInfo($"Set Character {c.id} ({c.name}, portrait={c.portraitId}, nameLang={nameIdx})");
                }

                TextureCache.EnsurePortraitShift(c.portraitId, c.shiftX, c.shiftY);
            }
        }

        private static void ApplyCharacterLoadout(Character dest, CatalogCharacter cfg, Character template)
        {
            if (cfg.skills != null && cfg.skills.Length > 0)
                dest.skills = CopyInts(cfg.skills);
            if (cfg.talents != null && cfg.talents.Length > 0)
                dest.talents = CopyInts(cfg.talents);
            if (cfg.joinLv > 0)
            {
                dest.joinLv = cfg.joinLv;
                dest.SetLevel(cfg.joinLv);
            }
            else if (template != null)
            {
                dest.SetLevel(dest.joinLv > 0 ? dest.joinLv : template.joinLv);
            }
        }

        private static void EnsureSkillSlot(Informations info, int skillId)
        {
            var field = typeof(Informations).GetField("skillTable",
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            var numField = typeof(Informations).GetField("skillNum",
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            if (field == null)
                return;

            var table = field.GetValue(info) as Skill[];
            if (table == null)
                return;

            if (skillId < table.Length)
            {
                if (numField != null)
                {
                    int num = (int)numField.GetValue(info);
                    if (skillId >= num)
                        numField.SetValue(info, skillId + 1);
                }

                return;
            }

            var grown = new Skill[skillId + 1];
            Array.Copy(table, grown, table.Length);
            field.SetValue(info, grown);
            if (numField != null)
                numField.SetValue(info, skillId + 1);
            Plugin.Log.LogInfo($"Expanded skillTable to {grown.Length} for skill {skillId}");
        }

        private static bool LangOccupied(LanguageData d)
        {
            return !string.IsNullOrEmpty(d.CN) || !string.IsNullOrEmpty(d.EN)
                || !string.IsNullOrEmpty(d.JP) || !string.IsNullOrEmpty(d.TC)
                || !string.IsNullOrEmpty(d.ES);
        }

        private static int AppendLanguage(string text)
        {
            var lc = LanguageCollect.Instance;
            if (lc == null)
                throw new InvalidOperationException("LanguageCollect.Instance is null");

            var field = typeof(LanguageCollect).GetField("menuName",
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            var arr = field?.GetValue(lc) as LanguageData[];
            if (arr == null)
            {
                lc.GetMenuName(1); // 1-based API
                arr = field?.GetValue(lc) as LanguageData[];
            }
            if (arr == null)
                throw new InvalidOperationException("LanguageCollect.menuName is null");

            // Find next free 0-based slot in the backing array.
            int slot = 0;
            for (int i = 0; i < arr.Length; i++)
            {
                if (LangOccupied(arr[i]))
                    slot = i + 1;
            }

            if (slot >= arr.Length)
                throw new InvalidOperationException("LanguageCollect.menuName exhausted");

            var data = new LanguageData
            {
                EN = text,
                CN = text,
                TC = text,
                JP = text,
                ES = text,
            };

            // SetMenuName writes menuName[index] (0-based).
            // GetMenuName reads menuName[index - 1] (1-based id).
            // UnitTypeData.name / Character.name store the 1-based id.
            arr[slot] = data;
            field.SetValue(lc, arr);
            try
            {
                lc.SetMenuName(slot, data);
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"SetMenuName({slot}) failed, array write kept: {ex.Message}");
            }

            int id = slot + 1; // 1-based for game tables
            var verify = lc.GetMenuName(id);
            Plugin.Log.LogInfo($"AppendLanguage slot={slot} id={id} set='{text}' get='{verify}'");
            if (!string.Equals(verify, text, StringComparison.Ordinal))
            {
                Plugin.Log.LogError(
                    $"AppendLanguage verify mismatch id={id}: want '{text}' got '{verify}' arr='{arr[slot].CN}'");
            }

            return id;
        }

        private static UnitTypeData CloneUnit(UnitTypeData src, int newId, int nameIdx, int infoIdx)
        {
            return new UnitTypeData
            {
                id = newId,
                name = nameIdx,
                icon = newId,
                info = infoIdx,
                model = newId,
                kind = src.kind,
                type = src.type,
                organism = src.organism,
                size = src.size,
                hp = src.hp,
                en = src.en,
                agile = src.agile,
                limit = src.limit,
                move = src.move,
                hangarS = src.hangarS,
                hangarL = src.hangarL,
                weapons = CopyInts(src.weapons),
                shield = src.shield,
                ablitys = CopyInts(src.ablitys),
                value = src.value,
                buy = src.buy,
                sell = src.sell,
                customCost = src.customCost,
                repair = src.repair,
                levelType = src.levelType,
            };
        }

        private static Character CloneCharacter(Character src, int newId, int nameIdx, int infoIdx, int portraitId)
        {
            var c = new Character
            {
                id = newId,
                name = nameIdx,
                info = infoIdx,
                portrait = portraitId,
                species = src.species,
                type = src.type,
                joinLv = src.joinLv,
                shoot = src.shoot,
                maneuver = src.maneuver,
                leadship = src.leadship,
                sp = src.sp,
                melee = src.melee,
                reaction = src.reaction,
                talents = CopyInts(src.talents),
                skills = CopyInts(src.skills),
                skillSpeechs = CopyInts(src.skillSpeechs),
            };
            // Level applied later in ApplyCharacterLoadout
            return c;
        }

        private static int[] CopyInts(int[] src)
        {
            if (src == null)
                return null;
            var dst = new int[src.Length];
            Array.Copy(src, dst, src.Length);
            return dst;
        }
    }

    [HarmonyPatch(typeof(DataLoader), nameof(DataLoader.LoadCharacterData))]
    internal static class Patch_LoadCharacterData
    {
        private static void Postfix()
        {
            Plugin.Log?.LogInfo("Postfix LoadCharacterData → EnsureTables");
            GundamContent.EnsureTables();
        }
    }

    [HarmonyPatch(typeof(PlayData), nameof(PlayData.Newgame))]
    internal static class Patch_Newgame
    {
        private static void Postfix(PlayData __instance)
        {
            Plugin.Log?.LogInfo("Postfix PlayData.Newgame → EnsurePlayData");
            GundamContent.EnsurePlayData(__instance);
        }
    }

    [HarmonyPatch(typeof(RecordController), nameof(RecordController.LoadGame))]
    internal static class Patch_LoadGame
    {
        private static void Postfix(int num)
        {
            Plugin.Log?.LogInfo($"Postfix RecordController.LoadGame({num}) → EnsurePlayData");
            GundamContent.EnsurePlayData(GundamContent.GetPlayDataInstance());
        }
    }

    [HarmonyPatch(typeof(RecordController), nameof(RecordController.LoadBreak))]
    internal static class Patch_LoadBreak
    {
        private static void Postfix()
        {
            Plugin.Log?.LogInfo("Postfix RecordController.LoadBreak → EnsurePlayData");
            GundamContent.EnsureTables();
            GundamContent.EnsurePlayData(GundamContent.GetPlayDataInstance());
        }
    }
}
