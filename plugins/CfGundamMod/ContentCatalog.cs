using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text.RegularExpressions;

namespace CfGundamMod
{
    [Serializable]
    public class CatalogFile
    {
        public CatalogUnit[] units;
        public CatalogCharacter[] characters;
        public CatalogSkill[] skills;
    }

    [Serializable]
    public class CatalogSkill
    {
        public int id;
        public int cloneFrom;
        public string name;
        public string info;
    }

    [Serializable]
    public class CatalogUnit
    {
        public int id;
        public int cloneFrom;
        public string name;
        public string info;
        public string iconPng;
        /// <summary>CF mapUnit atlas PNG 768x576 (12x9 of 64). Troop/ship map sprites.</summary>
        public string mapPng;
    }

    [Serializable]
    public class CatalogCharacter
    {
        public int id;
        public int cloneFrom;
        public string name;
        public string info;
        public int portraitId;
        public string portraitPng;
        public float shiftX = 4f;
        public float shiftY = -15f;
        public int[] skills;
        public int[] talents;
        public int joinLv;
    }

    internal static class ContentCatalog
    {
        private static CatalogFile _file;
        private static Dictionary<int, CatalogUnit> _unitsById;
        private static Dictionary<int, CatalogCharacter> _charsById;
        private static Dictionary<int, CatalogCharacter> _charsByPortrait;
        private static Dictionary<string, CatalogUnit> _unitsByName;
        private static Dictionary<int, CatalogSkill> _skillsById;

        public static IReadOnlyList<CatalogUnit> Units => _file?.units ?? Array.Empty<CatalogUnit>();
        public static IReadOnlyList<CatalogCharacter> Characters => _file?.characters ?? Array.Empty<CatalogCharacter>();
        public static IReadOnlyList<CatalogSkill> Skills => _file?.skills ?? Array.Empty<CatalogSkill>();

        public static void EnsureLoaded()
        {
            if (_file != null)
                return;

            var path = Path.Combine(TextureCache.ContentDir, "catalog.json");
            if (!File.Exists(path))
            {
                var alt = Path.Combine(
                    Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".",
                    "CfGundamMod",
                    "catalog.json");
                path = File.Exists(alt) ? alt : path;
            }

            if (!File.Exists(path))
                throw new FileNotFoundException("Missing catalog.json", path);

            var json = File.ReadAllText(path);
            _file = ParseCatalog(json);
            if (_file == null)
                throw new InvalidOperationException("catalog.json parse failed");

            _unitsById = new Dictionary<int, CatalogUnit>();
            _unitsByName = new Dictionary<string, CatalogUnit>(StringComparer.Ordinal);
            _charsById = new Dictionary<int, CatalogCharacter>();
            _charsByPortrait = new Dictionary<int, CatalogCharacter>();
            _skillsById = new Dictionary<int, CatalogSkill>();

            if (_file.units != null)
            {
                foreach (var u in _file.units)
                {
                    if (u == null || u.id <= 0)
                        continue;
                    _unitsById[u.id] = u;
                    if (!string.IsNullOrEmpty(u.name))
                        _unitsByName[u.name] = u;
                }
            }

            if (_file.characters != null)
            {
                foreach (var c in _file.characters)
                {
                    if (c == null || c.id <= 0)
                        continue;
                    _charsById[c.id] = c;
                    if (c.portraitId > 0)
                        _charsByPortrait[c.portraitId] = c;
                }
            }

            if (_file.skills != null)
            {
                foreach (var s in _file.skills)
                {
                    if (s == null || s.id <= 0)
                        continue;
                    _skillsById[s.id] = s;
                }
            }

            Plugin.Log?.LogInfo(
                $"Catalog loaded: {_unitsById.Count} units, {_charsById.Count} characters, {_skillsById.Count} skills from {path}");
        }

        /// <summary>
        /// Minimal JSON object-array parser (no external dep; Unity JsonUtility absent in this Managed set).
        /// </summary>
        internal static CatalogFile ParseCatalog(string json)
        {
            var units = new List<CatalogUnit>();
            var chars = new List<CatalogCharacter>();
            var skills = new List<CatalogSkill>();

            foreach (var obj in ExtractObjectArray(json, "units"))
            {
                units.Add(new CatalogUnit
                {
                    id = GetInt(obj, "id"),
                    cloneFrom = GetInt(obj, "cloneFrom"),
                    name = GetString(obj, "name"),
                    info = GetString(obj, "info"),
                    iconPng = GetString(obj, "iconPng"),
                    mapPng = GetString(obj, "mapPng"),
                });
            }

            foreach (var obj in ExtractObjectArray(json, "skills"))
            {
                skills.Add(new CatalogSkill
                {
                    id = GetInt(obj, "id"),
                    cloneFrom = GetInt(obj, "cloneFrom"),
                    name = GetString(obj, "name"),
                    info = GetString(obj, "info"),
                });
            }

            foreach (var obj in ExtractObjectArray(json, "characters"))
            {
                chars.Add(new CatalogCharacter
                {
                    id = GetInt(obj, "id"),
                    cloneFrom = GetInt(obj, "cloneFrom"),
                    name = GetString(obj, "name"),
                    info = GetString(obj, "info"),
                    portraitId = GetInt(obj, "portraitId"),
                    portraitPng = GetString(obj, "portraitPng"),
                    shiftX = GetFloat(obj, "shiftX", 4f),
                    shiftY = GetFloat(obj, "shiftY", -15f),
                    skills = GetIntArray(obj, "skills"),
                    talents = GetIntArray(obj, "talents"),
                    joinLv = GetInt(obj, "joinLv"),
                });
            }

            return new CatalogFile
            {
                units = units.ToArray(),
                characters = chars.ToArray(),
                skills = skills.ToArray(),
            };
        }

        private static IEnumerable<string> ExtractObjectArray(string json, string key)
        {
            var keyMatch = Regex.Match(json, "\"" + Regex.Escape(key) + "\"\\s*:\\s*\\[", RegexOptions.CultureInvariant);
            if (!keyMatch.Success)
                yield break;

            int i = keyMatch.Index + keyMatch.Length;
            int depth = 0;
            int start = -1;
            for (; i < json.Length; i++)
            {
                char c = json[i];
                if (c == '{')
                {
                    if (depth == 0)
                        start = i;
                    depth++;
                }
                else if (c == '}')
                {
                    depth--;
                    if (depth == 0 && start >= 0)
                    {
                        yield return json.Substring(start, i - start + 1);
                        start = -1;
                    }
                }
                else if (c == ']' && depth == 0)
                    yield break;
            }
        }

        private static string GetString(string obj, string key)
        {
            var m = Regex.Match(obj, "\"" + Regex.Escape(key) + "\"\\s*:\\s*\"([^\"]*)\"", RegexOptions.CultureInvariant);
            return m.Success ? Unescape(m.Groups[1].Value) : null;
        }

        private static int GetInt(string obj, string key)
        {
            var m = Regex.Match(obj, "\"" + Regex.Escape(key) + "\"\\s*:\\s*(-?\\d+)", RegexOptions.CultureInvariant);
            return m.Success ? int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture) : 0;
        }

        private static float GetFloat(string obj, string key, float fallback)
        {
            var m = Regex.Match(obj, "\"" + Regex.Escape(key) + "\"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)", RegexOptions.CultureInvariant);
            return m.Success
                ? float.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture)
                : fallback;
        }

        private static int[] GetIntArray(string obj, string key)
        {
            var m = Regex.Match(obj, "\"" + Regex.Escape(key) + "\"\\s*:\\s*\\[([^\\]]*)\\]", RegexOptions.CultureInvariant);
            if (!m.Success || string.IsNullOrWhiteSpace(m.Groups[1].Value))
                return null;

            var parts = m.Groups[1].Value.Split(',');
            var list = new List<int>();
            foreach (var p in parts)
            {
                var t = p.Trim();
                if (t.Length == 0)
                    continue;
                if (int.TryParse(t, NumberStyles.Integer, CultureInfo.InvariantCulture, out int v))
                    list.Add(v);
            }

            return list.Count == 0 ? null : list.ToArray();
        }

        private static string Unescape(string s) => s.Replace("\\n", "\n").Replace("\\\"", "\"").Replace("\\\\", "\\");

        public static bool TryGetUnit(int id, out CatalogUnit unit)
        {
            EnsureLoaded();
            return _unitsById.TryGetValue(id, out unit);
        }

        public static bool TryGetUnitByName(string name, out CatalogUnit unit)
        {
            EnsureLoaded();
            return _unitsByName.TryGetValue(name, out unit);
        }

        public static bool TryGetCharacter(int id, out CatalogCharacter character)
        {
            EnsureLoaded();
            return _charsById.TryGetValue(id, out character);
        }

        public static bool TryGetByPortrait(int portraitId, out CatalogCharacter character)
        {
            EnsureLoaded();
            return _charsByPortrait.TryGetValue(portraitId, out character);
        }

        public static bool IsModUnit(int id)
        {
            EnsureLoaded();
            return _unitsById.ContainsKey(id);
        }

        public static bool IsModPortrait(int portraitId)
        {
            EnsureLoaded();
            return _charsByPortrait.ContainsKey(portraitId);
        }
    }
}
