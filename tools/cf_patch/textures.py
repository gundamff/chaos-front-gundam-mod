from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import UnityPy
from PIL import Image


class TextureInjectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class TextureInventory:
    name: str
    width: int
    height: int
    texture_format: object
    has_sprite: bool

    def describe(self) -> str:
        layout = "Texture2D+Sprite" if self.has_sprite else "Texture2D-only"
        return (
            f"{self.name}={self.width}x{self.height}, "
            f"format={self.texture_format}, {layout}"
        )


def resize_placeholder(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        return source.convert("RGBA").resize(size, Image.Resampling.LANCZOS)


def _asset_name(asset) -> str:
    return getattr(asset, "m_Name", getattr(asset, "name", ""))


def _inventory(env, name: str) -> TextureInventory:
    textures = []
    sprite_names = set()
    for obj in env.objects:
        if obj.type.name not in {"Texture2D", "Sprite"}:
            continue
        asset = obj.read()
        asset_name = _asset_name(asset)
        if obj.type.name == "Sprite":
            sprite_names.add(asset_name)
        elif asset_name == name:
            textures.append(asset)

    if len(textures) != 1:
        reason = "not found" if not textures else f"found {len(textures)} matches"
        raise TextureInjectionError(f"Texture2D {name!r} {reason}")

    texture = textures[0]
    return TextureInventory(
        name=name,
        width=int(texture.m_Width),
        height=int(texture.m_Height),
        texture_format=texture.m_TextureFormat,
        has_sprite=name in sprite_names,
    )


def _ensure_targets_absent(env, names: set[str]) -> None:
    existing = set()
    for obj in env.objects:
        if obj.type.name not in {"Texture2D", "Sprite"}:
            continue
        name = _asset_name(obj.read())
        if name in names:
            existing.add(name)
    if existing:
        listing = ", ".join(sorted(existing))
        raise TextureInjectionError(f"target texture or Sprite already exists: {listing}")


def inject_textures(
    env, manifest: Mapping[str, object], assets_root: Path
) -> list[str]:
    unit_candidates = manifest["unit_texture_candidates"]
    if not isinstance(unit_candidates, list) or not unit_candidates:
        raise TextureInjectionError(
            "manifest unit_texture_candidates must be a non-empty list"
        )
    unit_targets = {str(candidate) for candidate in unit_candidates}
    portrait_target = str(manifest["portrait_texture"])
    _ensure_targets_absent(env, unit_targets | {portrait_target})

    unit = _inventory(env, "mapUnit31")
    portrait = _inventory(env, "portrait1")
    files = manifest["files"]
    if not isinstance(files, Mapping):
        raise TextureInjectionError("manifest files must be a mapping")

    resized = [
        resize_placeholder(
            Path(assets_root) / str(files["unit"]), (unit.width, unit.height)
        ),
        resize_placeholder(
            Path(assets_root) / str(files["portrait"]),
            (portrait.width, portrait.height),
        ),
    ]
    for image in resized:
        image.close()

    inventory = f"{unit.describe()}; {portrait.describe()}"
    raise TextureInjectionError(
        f"UnityPy {UnityPy.__version__} cannot add or clone Texture2D objects through a "
        "supported API; refusing to overwrite live textures. "
        f"Inventory: {inventory}"
    )
