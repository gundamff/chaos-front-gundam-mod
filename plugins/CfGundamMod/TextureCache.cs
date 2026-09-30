using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEngine;
using UnityEngine.UI;

namespace CfGundamMod
{
    /// <summary>
    /// Vanilla sizes:
    /// - unitIcon UI: 64x64
    /// - portrait*: 200x160 + PortraitData Shift into ~48 mask
    /// - mapUnit atlas: 768x576 (12x9 of 64) → TroopSpriteController sprites[color*4+dir]
    /// Multi-entry cache keyed by unitId / portraitId (catalog.json).
    /// </summary>
    internal static class TextureCache
    {
        public const int UnitIconSize = 64;
        public const int UnitArtSize = 28;
        public const int UnitArtYOffset = -10;
        public const int PortraitWidth = 200;
        public const int PortraitHeight = 160;
        public const int MapCell = 64;
        public const int MapCols = 12;
        public const int MapRows = 9;
        public const int MapColors = 8;
        public const int MapDirs = 4;

        private const int PortraitTopPad = 32;
        private const int PortraitArtMaxW = 72;
        private const int PortraitArtMaxH = 88;

        private static readonly Dictionary<int, Sprite> UnitSprites = new Dictionary<int, Sprite>();
        private static readonly Dictionary<int, Sprite> PortraitSprites = new Dictionary<int, Sprite>();
        private static readonly Dictionary<int, MapSpritePack> MapPacks = new Dictionary<int, MapSpritePack>();
        private static readonly HashSet<int> AppliedMapInstances = new HashSet<int>();

        internal sealed class MapSpritePack
        {
            public Sprite[] ColorSprites; // length 32 = color * 4 + dir
            public Sprite[] WhiteSprites; // length 4
            public Sprite[] DirSprites;   // length 4 (row0 cols0-3) for ship controllers
        }

        [ThreadStatic]
        private static bool _applyingUnit;

        public static string ContentDir
        {
            get
            {
                var asmDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                return Path.Combine(asmDir ?? ".", "CfGundamMod");
            }
        }

        public static Sprite GetUnitSprite(int unitId)
        {
            if (UnitSprites.TryGetValue(unitId, out var cached) && cached != null)
                return cached;
            if (!ContentCatalog.TryGetUnit(unitId, out var entry) || string.IsNullOrEmpty(entry.iconPng))
                return null;
            var sprite = BuildUnitSprite(entry.iconPng, unitId);
            if (sprite != null)
                UnitSprites[unitId] = sprite;
            return sprite;
        }

        public static Sprite GetPortraitSprite(int portraitId)
        {
            if (PortraitSprites.TryGetValue(portraitId, out var cached) && cached != null)
                return cached;
            if (!ContentCatalog.TryGetByPortrait(portraitId, out var entry) || string.IsNullOrEmpty(entry.portraitPng))
                return null;
            var sprite = BuildPortraitSprite(entry.portraitPng, portraitId);
            if (sprite != null)
                PortraitSprites[portraitId] = sprite;
            return sprite;
        }

        public static MapSpritePack GetMapPack(int unitId)
        {
            if (MapPacks.TryGetValue(unitId, out var cached) && cached != null)
                return cached;
            if (!ContentCatalog.TryGetUnit(unitId, out var entry) || string.IsNullOrEmpty(entry.mapPng))
                return null;
            var pack = BuildMapPack(entry.mapPng, unitId);
            if (pack != null)
                MapPacks[unitId] = pack;
            return pack;
        }

        public static void ApplyUnitIcon(GameObject go, int unitId)
        {
            if (go == null || _applyingUnit)
                return;
            var sprite = GetUnitSprite(unitId);
            if (sprite == null)
                return;

            _applyingUnit = true;
            try
            {
                var ic = go.GetComponent<ImageController>() ?? go.GetComponentInChildren<ImageController>(true);
                var img = go.GetComponent<Image>() ?? go.GetComponentInChildren<Image>(true);
                if (ic == null && img == null)
                {
                    Plugin.Log.LogWarning("unitIcon spawn has no Image/ImageController");
                    return;
                }

                if (ic != null)
                {
                    if (ic.images == null || ic.images.Length < 64)
                    {
                        var grown = new Sprite[64];
                        if (ic.images != null)
                            Array.Copy(ic.images, grown, ic.images.Length);
                        ic.images = grown;
                    }

                    for (int i = 0; i < ic.images.Length; i++)
                        ic.images[i] = sprite;
                }

                if (img != null)
                {
                    img.sprite = sprite;
                    img.preserveAspect = true;
                }

                ForceRect(go.transform as RectTransform, UnitIconSize, UnitIconSize);
                if (img != null)
                    ForceRect(img.rectTransform, UnitIconSize, UnitIconSize);

                Plugin.Log.LogInfo($"Applied unit icon {unitId} {UnitIconSize}x{UnitIconSize} on {go.name}");
            }
            finally
            {
                _applyingUnit = false;
            }
        }

        public static void ApplyTroopMapSprites(GameObject go, int unitId)
        {
            if (go == null)
                return;
            var ctrl = go.GetComponent<TroopSpriteController>()
                       ?? go.GetComponentInChildren<TroopSpriteController>(true);
            if (ctrl == null)
                return;

            int iid = ctrl.GetInstanceID();
            if (AppliedMapInstances.Contains(iid))
                return;

            var pack = GetMapPack(unitId);
            if (pack == null)
                return;

            if (ctrl.sprites != null && ctrl.sprites.Length > 0)
            {
                var neu = new Sprite[ctrl.sprites.Length];
                for (int i = 0; i < neu.Length; i++)
                    neu[i] = pack.ColorSprites[i % pack.ColorSprites.Length];
                ctrl.sprites = neu;
            }

            if (ctrl.whites != null && ctrl.whites.Length > 0)
            {
                var neu = new Sprite[ctrl.whites.Length];
                for (int i = 0; i < neu.Length; i++)
                    neu[i] = pack.WhiteSprites[i % pack.WhiteSprites.Length];
                ctrl.whites = neu;
            }

            // Force current render if Show already ran (shouldn't for InitSprite order)
            if (ctrl.sr != null && ctrl.sprites != null && ctrl.sprites.Length > 0)
                ctrl.sr.sprite = ctrl.sprites[0];

            AppliedMapInstances.Add(iid);
            string srName = ctrl.sr != null && ctrl.sr.sprite != null ? ctrl.sr.sprite.name : "null";
            Plugin.Log.LogInfo(
                $"Applied troop map sprites unit={unitId} sprites={ctrl.sprites?.Length ?? 0} whites={ctrl.whites?.Length ?? 0} on {go.name} sr={srName}");
        }

        public static void ApplyShipMapSprites(GameObject go, int unitId)
        {
            if (go == null)
                return;
            var ctrl = go.GetComponent<ShipSpriteController>()
                       ?? go.GetComponentInChildren<ShipSpriteController>(true);
            if (ctrl == null)
                return;

            int iid = ctrl.GetInstanceID();
            if (AppliedMapInstances.Contains(iid))
                return;

            var pack = GetMapPack(unitId);
            if (pack == null)
                return;

            if (ctrl.sprites != null && ctrl.sprites.Length > 0)
            {
                var neu = new Sprite[ctrl.sprites.Length];
                var src = pack.DirSprites != null && pack.DirSprites.Length > 0
                    ? pack.DirSprites
                    : pack.ColorSprites;
                for (int i = 0; i < neu.Length; i++)
                    neu[i] = src[i % src.Length];
                ctrl.sprites = neu;
            }

            AppliedMapInstances.Add(iid);
            Plugin.Log.LogInfo(
                $"Applied ship map sprites unit={unitId} sprites={ctrl.sprites?.Length ?? 0} on {go.name}");
        }

        public static void ApplyPortrait(PortraitController pc, int portraitId, bool replace)
        {
            var sprite = GetPortraitSprite(portraitId);
            if (pc == null || sprite == null)
                return;

            try
            {
                float sx = 4f, sy = -15f;
                if (ContentCatalog.TryGetByPortrait(portraitId, out var entry))
                {
                    sx = entry.shiftX;
                    sy = entry.shiftY;
                }
                EnsurePortraitShift(portraitId, sx, sy);

                if (pc.potraits != null)
                {
                    var idx = portraitId - 1;
                    if (idx >= 0)
                    {
                        if (idx >= pc.potraits.Length)
                        {
                            var grown = new Sprite[idx + 1];
                            Array.Copy(pc.potraits, grown, pc.potraits.Length);
                            pc.potraits = grown;
                        }
                        pc.potraits[idx] = sprite;
                    }
                }

                var img = pc.GetComponent<Image>();
                if (img == null)
                    return;

                img.sprite = sprite;
                img.preserveAspect = false;

                if (replace)
                {
                    var shift = Informations.Instance != null
                        ? Informations.Instance.GetPortraitShift(portraitId)
                        : new Vector2(sx, sy);
                    img.rectTransform.anchoredPosition = shift;
                    Plugin.Log.LogInfo($"Portrait {portraitId} sprite+shift={shift}");
                }
                else
                {
                    Plugin.Log.LogInfo($"Portrait {portraitId} sprite only (replace=false)");
                }
            }
            catch (Exception ex)
            {
                Plugin.Log.LogError($"ApplyPortrait failed: {ex}");
            }
        }

        public static void EnsurePortraitShift(int id, float shiftX, float shiftY)
        {
            var info = Informations.Instance;
            if (info == null || id <= 0)
                return;

            try
            {
                if (Informations.portraitNum < id)
                    Informations.portraitNum = id;

                if (info.portraitShiftTable == null || info.portraitShiftTable.Length < Informations.portraitNum)
                {
                    var neu = new Vector2[Informations.portraitNum];
                    if (info.portraitShiftTable != null)
                        Array.Copy(info.portraitShiftTable, neu, Math.Min(info.portraitShiftTable.Length, neu.Length));
                    info.portraitShiftTable = neu;
                }

                info.SetPortraitShift(id, new Vector2(shiftX, shiftY));
            }
            catch (Exception ex)
            {
                Plugin.Log.LogError($"EnsurePortraitShift failed: {ex}");
            }
        }

        private static void ForceRect(RectTransform rt, float w, float h)
        {
            if (rt == null)
                return;
            rt.localScale = Vector3.one;
            rt.sizeDelta = new Vector2(w, h);
        }

        private static MapSpritePack BuildMapPack(string fileName, int unitId)
        {
            var tex = LoadTexture(fileName);
            if (tex == null)
                return null;

            if (tex.width != MapCols * MapCell || tex.height != MapRows * MapCell)
            {
                Plugin.Log.LogError(
                    $"Map atlas {fileName} expected {MapCols * MapCell}x{MapRows * MapCell}, got {tex.width}x{tex.height}");
                return null;
            }

            tex.filterMode = FilterMode.Point;
            tex.wrapMode = TextureWrapMode.Clamp;

            // Vanilla troopSprite.sprites is filled row-major from the atlas (12 cols × 8 color rows).
            // Show(colorStyle, dir) uses index = colorStyle * 4 + dir, and colorStyle steps by 1
            // across groups of 4 cells (3 groups per row × 8 rows = 24 styles).
            int colorCells = MapCols * MapColors; // 96
            var colors = new Sprite[colorCells];
            for (int i = 0; i < colorCells; i++)
            {
                int col = i % MapCols;
                int rowFromTop = i / MapCols;
                float x = col * MapCell;
                // Unity texture y=0 is bottom; PNG top row → high y after LoadImage
                float y = (MapRows - 1 - rowFromTop) * MapCell;
                var sp = Sprite.Create(
                    tex,
                    new Rect(x, y, MapCell, MapCell),
                    new Vector2(0.5f, 0.5f),
                    100f);
                sp.name = $"map-{unitId}_{i}";
                colors[i] = sp;
            }

            var whites = new Sprite[MapDirs];
            var dirs = new Sprite[MapDirs];
            for (int dir = 0; dir < MapDirs; dir++)
            {
                float x = dir * MapCell;
                whites[dir] = Sprite.Create(
                    tex,
                    new Rect(x, 0f, MapCell, MapCell),
                    new Vector2(0.5f, 0.5f),
                    100f);
                whites[dir].name = $"map-{unitId}_white_d{dir}";
                dirs[dir] = colors[dir];
            }

            Plugin.Log.LogInfo($"Built map pack {fileName} for unit {unitId} cells={colorCells}");
            return new MapSpritePack
            {
                ColorSprites = colors,
                WhiteSprites = whites,
                DirSprites = dirs,
            };
        }

        private static Sprite BuildUnitSprite(string fileName, int unitId)
        {
            var src = LoadTexture(fileName);
            if (src == null)
                return null;

            string name = $"unit-{unitId}_ui64";
            if (src.width == UnitIconSize && src.height == UnitIconSize)
            {
                src.filterMode = FilterMode.Point;
                var direct = Sprite.Create(
                    src,
                    new Rect(0, 0, UnitIconSize, UnitIconSize),
                    new Vector2(0.5f, 0.5f),
                    100f);
                direct.name = name;
                Plugin.Log.LogInfo($"Using pre-sized unit icon {fileName}");
                return direct;
            }

            var tex = new Texture2D(UnitIconSize, UnitIconSize, TextureFormat.RGBA32, false);
            tex.filterMode = FilterMode.Point;
            tex.wrapMode = TextureWrapMode.Clamp;
            Clear(tex, Color.clear);
            int x = (UnitIconSize - UnitArtSize) / 2;
            int y = (UnitIconSize - UnitArtSize) / 2 + UnitArtYOffset;
            Blit(src, tex, x, y, UnitArtSize, UnitArtSize);
            tex.Apply(false, true);
            tex.name = name;
            var sprite = Sprite.Create(tex, new Rect(0, 0, UnitIconSize, UnitIconSize), new Vector2(0.5f, 0.5f), 100f);
            sprite.name = name;
            return sprite;
        }

        private static Sprite BuildPortraitSprite(string fileName, int portraitId)
        {
            var src = LoadTexture(fileName);
            if (src == null)
                return null;

            string name = $"portrait-{portraitId}_200x160";
            if (src.width == PortraitWidth && src.height == PortraitHeight)
            {
                src.filterMode = FilterMode.Point;
                var direct = Sprite.Create(
                    src,
                    new Rect(0, 0, PortraitWidth, PortraitHeight),
                    new Vector2(0.5f, 0.5f),
                    100f);
                direct.name = name;
                Plugin.Log.LogInfo($"Using pre-sized portrait {fileName}");
                return direct;
            }

            var cropped = TrimDarkBorders(src, 8);
            var tex = new Texture2D(PortraitWidth, PortraitHeight, TextureFormat.RGBA32, false);
            tex.filterMode = FilterMode.Point;
            Clear(tex, Color.black);
            float scale = Math.Min((float)PortraitArtMaxW / cropped.width, (float)PortraitArtMaxH / cropped.height);
            int dw = Math.Max(1, Mathf.RoundToInt(cropped.width * scale));
            int dh = Math.Max(1, Mathf.RoundToInt(cropped.height * scale));
            int dx = (PortraitWidth - dw) / 2;
            int dy = PortraitHeight - PortraitTopPad - dh;
            if (dy < 0) dy = 0;
            if (dy + dh > PortraitHeight)
                dh = PortraitHeight - dy;
            Blit(cropped, tex, dx, dy, dw, dh);
            tex.Apply(false, true);
            tex.name = name;
            var sprite = Sprite.Create(tex, new Rect(0, 0, PortraitWidth, PortraitHeight), new Vector2(0.5f, 0.5f), 100f);
            sprite.name = name;
            return sprite;
        }

        private static Texture2D LoadTexture(string fileName)
        {
            var path = Path.Combine(ContentDir, fileName);
            if (!File.Exists(path))
            {
                var alt = Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".", fileName);
                path = File.Exists(alt) ? alt : path;
            }

            if (!File.Exists(path))
            {
                Plugin.Log.LogError($"Missing texture: {path}");
                return null;
            }

            var bytes = File.ReadAllBytes(path);
            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            if (!ImageConversion.LoadImage(tex, bytes, false))
            {
                Plugin.Log.LogError($"LoadImage failed: {path}");
                return null;
            }

            tex.name = Path.GetFileNameWithoutExtension(fileName);
            tex.filterMode = FilterMode.Point;
            tex.wrapMode = TextureWrapMode.Clamp;
            Plugin.Log.LogInfo($"Loaded source {tex.name} {tex.width}x{tex.height}");
            return tex;
        }

        private static void Clear(Texture2D tex, Color color)
        {
            var px = new Color[tex.width * tex.height];
            for (int i = 0; i < px.Length; i++)
                px[i] = color;
            tex.SetPixels(px);
        }

        private static void Blit(Texture2D src, Texture2D dst, int dx, int dy, int dw, int dh)
        {
            var corner = src.GetPixel(2, src.height - 3);
            bool keyBackdrop = corner.r > 0.65f && corner.g > 0.5f && corner.b > 0.35f;

            for (int y = 0; y < dh; y++)
            {
                int sy = Math.Min(src.height - 1, y * src.height / dh);
                int dy2 = dy + y;
                if (dy2 < 0 || dy2 >= dst.height)
                    continue;
                for (int x = 0; x < dw; x++)
                {
                    int sx = Math.Min(src.width - 1, x * src.width / dw);
                    int dx2 = dx + x;
                    if (dx2 < 0 || dx2 >= dst.width)
                        continue;
                    var c = src.GetPixel(sx, sy);
                    if (c.a < 0.05f)
                        continue;
                    if (keyBackdrop && IsNear(c, corner, 0.12f))
                        continue;
                    dst.SetPixel(dx2, dy2, c);
                }
            }
        }

        private static bool IsNear(Color a, Color b, float tol)
        {
            return Math.Abs(a.r - b.r) <= tol && Math.Abs(a.g - b.g) <= tol && Math.Abs(a.b - b.b) <= tol;
        }

        private static Texture2D TrimDarkBorders(Texture2D src, int threshold)
        {
            int minX = src.width, minY = src.height, maxX = 0, maxY = 0;
            for (int y = 0; y < src.height; y++)
            for (int x = 0; x < src.width; x++)
            {
                var c = src.GetPixel(x, y);
                if (c.a < 0.05f)
                    continue;
                if (c.r * 255 < threshold && c.g * 255 < threshold && c.b * 255 < threshold)
                    continue;
                if (x < minX) minX = x;
                if (y < minY) minY = y;
                if (x > maxX) maxX = x;
                if (y > maxY) maxY = y;
            }

            if (maxX <= minX || maxY <= minY)
                return src;

            int w = maxX - minX + 1;
            int h = maxY - minY + 1;
            var cropped = new Texture2D(w, h, TextureFormat.RGBA32, false);
            cropped.filterMode = FilterMode.Point;
            cropped.SetPixels(src.GetPixels(minX, minY, w, h));
            cropped.Apply(false, false);
            return cropped;
        }
    }
}
