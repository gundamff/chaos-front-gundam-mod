using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;

namespace CfGundamMod.Patches
{
    /// <summary>
    /// 摇摆闪避（Skill 66）：发动时不挂整回合「必闪」Buff，改为 1 次充能；
    /// 命中结算里视同 Buff 32（必闪）；下场突击/撞击战结束后消耗。
    /// </summary>
    internal static class SwayDodgeState
    {
        public const int SkillId = 66;
        public const int SureDodgeBuffId = 32;
        public const int TemplateSkillId = 40;

        private static readonly HashSet<TroopBackUp> Charges = new HashSet<TroopBackUp>();
        private static readonly HashSet<TroopBackUp> ConvertAddBuff = new HashSet<TroopBackUp>();
        private static readonly HashSet<TroopBackUp> UsedInFight = new HashSet<TroopBackUp>();
        private static int FightDepth;

        public static void Arm(TroopBackUp troop)
        {
            if (troop == null)
                return;
            Charges.Add(troop);
            Plugin.Log?.LogInfo($"SwayDodge armed {Describe(troop)}");
        }

        public static bool HasCharge(TroopBackUp troop)
        {
            return troop != null && Charges.Contains(troop);
        }

        public static void MarkConvert(TroopBackUp troop)
        {
            if (troop != null)
                ConvertAddBuff.Add(troop);
        }

        public static bool ShouldConvertAddBuff(TroopBackUp troop)
        {
            return troop != null && ConvertAddBuff.Remove(troop);
        }

        public static void NoteUsedIfCharged(TroopBackUp troop)
        {
            if (FightDepth > 0 && HasCharge(troop))
                UsedInFight.Add(troop);
        }

        public static void BeginFight()
        {
            FightDepth++;
        }

        public static void EndFight()
        {
            if (FightDepth <= 0)
                return;
            FightDepth--;
            if (FightDepth > 0)
                return;

            foreach (var t in UsedInFight)
            {
                if (Charges.Remove(t))
                    Plugin.Log?.LogInfo($"SwayDodge consumed {Describe(t)}");
            }

            UsedInFight.Clear();
        }

        private static string Describe(TroopBackUp troop)
        {
            try
            {
                var u = troop.unit;
                if (u == null)
                    return "troop?";
                return $"char={u.characterId} type={u.unitType} side={troop.side}";
            }
            catch
            {
                return "troop";
            }
        }

        public static void MarkTroopsInObjectGraph(object root)
        {
            // kept for compatibility — unused after fight-depth consume
        }
    }

    [HarmonyPatch(typeof(BattleController), nameof(BattleController.UseSkillOrder))]
    internal static class Patch_UseSkillOrder_Sway
    {
        private static void Prefix(object __0)
        {
            if (__0 == null || !Plugin.EnableContent.Value)
                return;

            try
            {
                if (__0 is IEnumerable list)
                {
                    foreach (var msg in list)
                        RemapSkillsOnMessage(msg);
                }
            }
            catch (Exception ex)
            {
                Plugin.Log?.LogWarning($"SwayDodge UseSkillOrder: {ex.Message}");
            }
        }

        private static void RemapSkillsOnMessage(object msg)
        {
            if (msg == null)
                return;

            var skillsField = AccessTools.Field(msg.GetType(), "skills");
            var groupField = AccessTools.Field(msg.GetType(), "group");
            if (skillsField == null)
                return;

            var skillsObj = skillsField.GetValue(msg) as IList;
            if (skillsObj == null || skillsObj.Count == 0)
                return;

            bool remapped = false;
            for (int i = 0; i < skillsObj.Count; i++)
            {
                var entry = skillsObj[i];
                if (entry == null)
                    continue;

                if (entry is int sid)
                {
                    if (sid == SwayDodgeState.SkillId)
                    {
                        skillsObj[i] = SwayDodgeState.TemplateSkillId;
                        remapped = true;
                    }

                    continue;
                }

                var idField = AccessTools.Field(entry.GetType(), "id")
                    ?? AccessTools.Field(entry.GetType(), "skillId");
                if (idField != null && idField.FieldType == typeof(int))
                {
                    int id = (int)idField.GetValue(entry);
                    if (id == SwayDodgeState.SkillId)
                    {
                        idField.SetValue(entry, SwayDodgeState.TemplateSkillId);
                        remapped = true;
                    }
                }
            }

            if (!remapped)
                return;

            MarkGroupTroops(groupField?.GetValue(msg));
        }

        private static void MarkGroupTroops(object group)
        {
            if (group == null)
                return;

            foreach (var f in group.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                object val;
                try { val = f.GetValue(group); }
                catch { continue; }

                if (val is TroopBackUp one)
                    SwayDodgeState.MarkConvert(one);
                else if (val is IEnumerable seq && !(val is string))
                {
                    foreach (var item in seq)
                    {
                        if (item is TroopBackUp tb)
                            SwayDodgeState.MarkConvert(tb);
                    }
                }
            }
        }
    }

    [HarmonyPatch(typeof(TroopBackUp), nameof(TroopBackUp.AddBuff))]
    internal static class Patch_TroopBackUp_AddBuff_Sway
    {
        private static bool Prefix(TroopBackUp __instance, TroopBuff __0)
        {
            if (!Plugin.EnableContent.Value || __0 == null)
                return true;

            if (__0.buffId != SwayDodgeState.SureDodgeBuffId)
                return true;

            if (!SwayDodgeState.ShouldConvertAddBuff(__instance))
                return true;

            SwayDodgeState.Arm(__instance);
            return false;
        }
    }

    [HarmonyPatch(typeof(TroopBackUp), nameof(TroopBackUp.BuffListContain))]
    internal static class Patch_BuffListContain_Sway
    {
        private static void Postfix(TroopBackUp __instance, int id, ref bool __result)
        {
            if (!Plugin.EnableContent.Value)
                return;
            if (id != SwayDodgeState.SureDodgeBuffId)
                return;
            if (!SwayDodgeState.HasCharge(__instance))
                return;

            __result = true;
            SwayDodgeState.NoteUsedIfCharged(__instance);
        }
    }

    [HarmonyPatch(typeof(BattleController), nameof(BattleController.GetStormFightMessage))]
    internal static class Patch_StormFight_Sway
    {
        private static void Prefix()
        {
            if (Plugin.EnableContent.Value)
                SwayDodgeState.BeginFight();
        }

        private static void Postfix()
        {
            if (Plugin.EnableContent.Value)
                SwayDodgeState.EndFight();
        }
    }

    [HarmonyPatch(typeof(BattleController), nameof(BattleController.GetRamFightMessage))]
    internal static class Patch_RamFight_Sway
    {
        private static void Prefix()
        {
            if (Plugin.EnableContent.Value)
                SwayDodgeState.BeginFight();
        }

        private static void Postfix()
        {
            if (Plugin.EnableContent.Value)
                SwayDodgeState.EndFight();
        }
    }
}
