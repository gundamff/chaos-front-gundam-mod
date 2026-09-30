using System;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;

namespace CfGundamMod
{
    [BepInPlugin(PluginInfo.PLUGIN_GUID, PluginInfo.PLUGIN_NAME, PluginInfo.PLUGIN_VERSION)]
    public class Plugin : BaseUnityPlugin
    {
        internal static ManualLogSource Log;
        internal static Plugin Instance;

        internal static ConfigEntry<bool> DumpDataApis;
        internal static ConfigEntry<bool> EnableContent;
        internal static ConfigEntry<bool> AutoUnlockAndRoster;

        private Harmony _harmony;

        private void Awake()
        {
            Instance = this;
            Log = Logger;

            DumpDataApis = Config.Bind("Debug", "DumpDataApis", false,
                "Log UnitType/Character/Portrait API types on load.");
            EnableContent = Config.Bind("Content", "Enable", true,
                "Load content/catalog.json and append units/characters after DataLoader.");
            AutoUnlockAndRoster = Config.Bind("Content", "AutoUnlockAndRoster", true,
                "On NewGame/LoadGame: unlock catalog units + add catalog characters to free pilot list.");

            Log.LogInfo($"{PluginInfo.PLUGIN_NAME} {PluginInfo.PLUGIN_VERSION} Awake");

            if (DumpDataApis.Value)
            {
                try { DataApiProbe.Dump(Log); }
                catch (Exception ex) { Log.LogError($"DataApiProbe failed: {ex}"); }
            }

            try
            {
                ContentCatalog.EnsureLoaded();
            }
            catch (Exception ex)
            {
                Log.LogError($"Catalog preload failed: {ex}");
            }

            _harmony = new Harmony(PluginInfo.PLUGIN_GUID);
            foreach (var t in typeof(Plugin).Assembly.GetTypes())
            {
                var attrs = t.GetCustomAttributes(typeof(HarmonyPatch), true);
                if (attrs == null || attrs.Length == 0)
                    continue;
                try
                {
                    _harmony.CreateClassProcessor(t).Patch();
                    Log.LogInfo($"Patched {t.FullName}");
                }
                catch (Exception ex)
                {
                    Log.LogError($"Patch failed {t.FullName}: {ex}");
                }
            }
        }
    }
}
