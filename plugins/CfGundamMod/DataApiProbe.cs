using System;
using System.Linq;
using System.Reflection;
using BepInEx.Logging;

namespace CfGundamMod
{
    internal static class DataApiProbe
    {
        private static readonly string[] Needles =
        {
            "UnitType",
            "CharacterData",
            "LanguageData",
            "Portrait",
            "mapUnit",
            "unlockUnit",
        };

        public static void Dump(ManualLogSource log)
        {
            Assembly asm = null;
            foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (string.Equals(a.GetName().Name, "Assembly-CSharp", StringComparison.Ordinal))
                {
                    asm = a;
                    break;
                }
            }

            if (asm == null)
            {
                try { asm = Assembly.Load("Assembly-CSharp"); }
                catch (Exception ex)
                {
                    log.LogWarning($"Assembly-CSharp not loaded yet: {ex.Message}");
                    return;
                }
            }

            log.LogInfo($"Probing {asm.FullName}");
            Type[] types;
            try { types = asm.GetTypes(); }
            catch (ReflectionTypeLoadException ex)
            {
                types = ex.Types.Where(t => t != null).ToArray();
            }

            foreach (var t in types.OrderBy(x => x.FullName))
            {
                var name = t.FullName ?? t.Name;
                if (!Needles.Any(n => name.IndexOf(n, StringComparison.OrdinalIgnoreCase) >= 0))
                    continue;
                log.LogInfo($"TYPE {name}");
            }
        }
    }
}
