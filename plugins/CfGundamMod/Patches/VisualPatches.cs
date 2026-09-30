using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace CfGundamMod.Patches
{
    internal static class VisualSpawnState
    {
        [ThreadStatic]
        internal static bool PendingUnitIcon;

        [ThreadStatic]
        internal static bool PendingTroopSprite;

        [ThreadStatic]
        internal static bool PendingShipSprite;

        [ThreadStatic]
        internal static int PendingUnitId;
    }

    /// <summary>
    /// Mod units set model/icon to their new id, but Unity prefabs only exist for vanilla ids.
    /// Redirect loads to cloneFrom so hangar launch / map sprites / UI icons resolve.
    /// </summary>
    internal static class ModPrefabRedirect
    {
        private static readonly string[] Prefixed =
        {
            "Prefabs/UI/UnitIcon/unitIcon",
            "Prefabs/Battle/TroopSprite/troopSprite",
            "Prefabs/BigMap/ShipSprites/shipSprite",
            "AnimatorController/unit",
        };

        internal static bool TryRedirect(string path, out string fallback, out int modUnitId, out bool swapUnitIcon, out bool swapTroop, out bool swapShip)
        {
            fallback = null;
            modUnitId = 0;
            swapUnitIcon = false;
            swapTroop = false;
            swapShip = false;
            if (string.IsNullOrEmpty(path))
                return false;

            foreach (var prefix in Prefixed)
            {
                if (!path.StartsWith(prefix, StringComparison.Ordinal))
                    continue;

                string rest = path.Substring(prefix.Length);
                string idPart = rest;
                string trail = "";
                int slash = rest.IndexOf('/');
                if (slash >= 0)
                {
                    idPart = rest.Substring(0, slash);
                    trail = rest.Substring(slash);
                }

                if (!int.TryParse(idPart, out int unitId))
                    return false;
                if (!ContentCatalog.TryGetUnit(unitId, out var entry))
                    return false;

                fallback = prefix + entry.cloneFrom + trail;
                modUnitId = unitId;
                swapUnitIcon = prefix.Contains("unitIcon");
                swapTroop = prefix.Contains("troopSprite");
                swapShip = prefix.Contains("shipSprite");
                return true;
            }

            return false;
        }
    }

    internal static class VisualPending
    {
        internal static void Mark(int unitId, bool swapIcon, bool swapTroop, bool swapShip)
        {
            VisualSpawnState.PendingUnitId = unitId;
            VisualSpawnState.PendingUnitIcon = swapIcon;
            VisualSpawnState.PendingTroopSprite = swapTroop;
            VisualSpawnState.PendingShipSprite = swapShip;
        }

        internal static void Clear()
        {
            VisualSpawnState.PendingUnitIcon = false;
            VisualSpawnState.PendingTroopSprite = false;
            VisualSpawnState.PendingShipSprite = false;
            VisualSpawnState.PendingUnitId = 0;
        }

        internal static void Apply(UnityEngine.Object result)
        {
            bool icon = VisualSpawnState.PendingUnitIcon;
            bool troop = VisualSpawnState.PendingTroopSprite;
            bool ship = VisualSpawnState.PendingShipSprite;
            int unitId = VisualSpawnState.PendingUnitId;
            Clear();
            if (unitId <= 0 || result == null)
                return;

            GameObject go = result as GameObject;
            if (go == null && result is Component c)
                go = c.gameObject;
            if (go == null)
                return;

            if (icon)
                TextureCache.ApplyUnitIcon(go, unitId);
            if (troop)
                TextureCache.ApplyTroopMapSprites(go, unitId);
            if (ship)
                TextureCache.ApplyShipMapSprites(go, unitId);
        }
    }

    [HarmonyPatch]
    internal static class Patch_ResourcesLoad
    {
        private static MethodBase TargetMethod()
        {
            return typeof(Resources)
                .GetMethods(BindingFlags.Public | BindingFlags.Static)
                .First(m =>
                    m.Name == "Load"
                    && !m.IsGenericMethod
                    && m.ReturnType == typeof(UnityEngine.Object)
                    && m.GetParameters().Length == 1
                    && m.GetParameters()[0].ParameterType == typeof(string));
        }

        private static bool Prefix(string path, ref UnityEngine.Object __result)
        {
            if (!Plugin.EnableContent.Value)
                return true;
            if (!ModPrefabRedirect.TryRedirect(path, out var fallback, out int unitId,
                    out bool swapIcon, out bool swapTroop, out bool swapShip))
                return true;

            __result = Resources.Load(fallback, typeof(GameObject));
            if (__result == null)
            {
                Plugin.Log.LogError($"Fallback Resources.Load failed: {fallback}");
                VisualPending.Clear();
                return false;
            }

            VisualPending.Mark(unitId, swapIcon, swapTroop, swapShip);
            Plugin.Log.LogInfo($"Resources.Load {path} → {fallback}");
            return false;
        }
    }

    [HarmonyPatch]
    internal static class Patch_ResourcesLoadTyped
    {
        private static MethodBase TargetMethod()
        {
            return typeof(Resources)
                .GetMethods(BindingFlags.Public | BindingFlags.Static)
                .First(m =>
                    m.Name == "Load"
                    && !m.IsGenericMethod
                    && m.ReturnType == typeof(UnityEngine.Object)
                    && m.GetParameters().Length == 2
                    && m.GetParameters()[0].ParameterType == typeof(string)
                    && m.GetParameters()[1].ParameterType == typeof(Type));
        }

        private static bool Prefix(string path, Type systemTypeInstance, ref UnityEngine.Object __result)
        {
            if (!Plugin.EnableContent.Value)
                return true;
            if (!ModPrefabRedirect.TryRedirect(path, out var fallback, out int unitId,
                    out bool swapIcon, out bool swapTroop, out bool swapShip))
                return true;

            __result = Resources.Load(fallback, systemTypeInstance ?? typeof(GameObject));
            if (__result == null)
            {
                Plugin.Log.LogError($"Fallback Resources.Load(Type) failed: {fallback}");
                VisualPending.Clear();
                return false;
            }

            VisualPending.Mark(unitId, swapIcon, swapTroop, swapShip);
            Plugin.Log.LogInfo($"Resources.Load(Type) {path} → {fallback}");
            return false;
        }
    }

    [HarmonyPatch]
    internal static class Patch_InstantiateObject
    {
        private static MethodBase TargetMethod()
        {
            return typeof(UnityEngine.Object)
                .GetMethods(BindingFlags.Public | BindingFlags.Static)
                .First(m =>
                    m.Name == "Instantiate"
                    && !m.IsGenericMethod
                    && m.ReturnType == typeof(UnityEngine.Object)
                    && m.GetParameters().Length == 1
                    && m.GetParameters()[0].ParameterType == typeof(UnityEngine.Object));
        }

        private static void Postfix(UnityEngine.Object __result) => VisualPending.Apply(__result);
    }

    [HarmonyPatch]
    internal static class Patch_InstantiateObjectParent
    {
        private static MethodBase TargetMethod()
        {
            return typeof(UnityEngine.Object)
                .GetMethods(BindingFlags.Public | BindingFlags.Static)
                .First(m =>
                    m.Name == "Instantiate"
                    && !m.IsGenericMethod
                    && m.ReturnType == typeof(UnityEngine.Object)
                    && m.GetParameters().Length == 2
                    && m.GetParameters()[0].ParameterType == typeof(UnityEngine.Object)
                    && m.GetParameters()[1].ParameterType == typeof(Transform));
        }

        private static void Postfix(UnityEngine.Object __result) => VisualPending.Apply(__result);
    }

    [HarmonyPatch]
    internal static class Patch_InstantiateObjectXform
    {
        private static MethodBase TargetMethod()
        {
            return typeof(UnityEngine.Object)
                .GetMethods(BindingFlags.Public | BindingFlags.Static)
                .First(m =>
                    m.Name == "Instantiate"
                    && !m.IsGenericMethod
                    && m.ReturnType == typeof(UnityEngine.Object)
                    && m.GetParameters().Length == 3
                    && m.GetParameters()[0].ParameterType == typeof(UnityEngine.Object)
                    && m.GetParameters()[1].ParameterType == typeof(Vector3)
                    && m.GetParameters()[2].ParameterType == typeof(Quaternion));
        }

        private static void Postfix(UnityEngine.Object __result) => VisualPending.Apply(__result);
    }

    [HarmonyPatch(typeof(PortraitController), nameof(PortraitController.Show))]
    internal static class Patch_PortraitShow
    {
        private static void Postfix(PortraitController __instance, int id, bool replace)
        {
            if (!Plugin.EnableContent.Value || !ContentCatalog.IsModPortrait(id))
                return;

            TextureCache.ApplyPortrait(__instance, id, replace);
        }
    }

    [HarmonyPatch(typeof(UnitShopButton), nameof(UnitShopButton.InitShop))]
    internal static class Patch_UnitShopInitShop
    {
        private static void Postfix(UnitShopButton __instance, int s, int order)
        {
            TrySwapShopIcon(__instance, s, order);
        }

        internal static void TrySwapShopIcon(UnitShopButton button, int s, int order)
        {
            try
            {
                if (!Plugin.EnableContent.Value || button == null)
                    return;

                if (button.nameText != null
                    && ContentCatalog.TryGetUnitByName(button.nameText.text, out var byName))
                {
                    SwapIconUnder(button.iconBack, byName.id);
                    return;
                }

                var pd = PlayData.Instance;
                if (pd == null)
                    return;

                int id = -1;
                if (s == 0 && pd.UnlockedSArms != null && order >= 0 && order < pd.UnlockedSArms.Count)
                    id = pd.UnlockedSArms[order];
                else if (s == 1 && pd.UnlockedLArms != null && order >= 0 && order < pd.UnlockedLArms.Count)
                    id = pd.UnlockedLArms[order];
                else if (s == 2 && pd.UnlockedShips != null && order >= 0 && order < pd.UnlockedShips.Count)
                    id = pd.UnlockedShips[order];

                if (ContentCatalog.IsModUnit(id))
                    SwapIconUnder(button.iconBack, id);
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"UnitShop icon swap: {ex.Message}");
            }
        }

        private static void SwapIconUnder(RectTransform iconBack, int unitId)
        {
            if (iconBack == null || iconBack.childCount == 0)
            {
                Plugin.Log.LogWarning($"Shop iconBack empty for unit {unitId}");
                return;
            }

            TextureCache.ApplyUnitIcon(iconBack.GetChild(0).gameObject, unitId);
        }
    }

    [HarmonyPatch(typeof(UnitShopButton), nameof(UnitShopButton.InitSell))]
    internal static class Patch_UnitShopInitSell
    {
        private static void Postfix(UnitShopButton __instance, int s, int order)
        {
            Patch_UnitShopInitShop.TrySwapShopIcon(__instance, s, order);
        }
    }

    [HarmonyPatch(typeof(ImageController), nameof(ImageController.Show))]
    internal static class Patch_ImageControllerShow
    {
        private static void Postfix(ImageController __instance, int id)
        {
            if (!Plugin.EnableContent.Value || __instance?.images == null || __instance.images.Length == 0)
                return;

            var first = __instance.images[0];
            if (first == null || first.name == null || !first.name.StartsWith("unit-", StringComparison.Ordinal))
                return;

            var img = __instance.GetComponent<UnityEngine.UI.Image>();
            if (img != null && img.sprite != first)
                img.sprite = __instance.images[Math.Max(0, Math.Min(id - 1, __instance.images.Length - 1))] ?? first;
        }
    }
}
