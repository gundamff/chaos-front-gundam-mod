from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from tools.cf_patch.textures import (
    TextureInjectionError,
    inject_textures,
    resize_placeholder,
)


def test_resize_placeholder_matches_target_dimensions_and_rgba(tmp_path: Path):
    source = tmp_path / "placeholder.png"
    Image.new("RGB", (64, 64), "#334455").save(source)

    resized = resize_placeholder(source, (768, 576))

    assert resized.size == (768, 576)
    assert resized.mode == "RGBA"


def test_resize_placeholder_does_not_modify_source(tmp_path: Path):
    source = tmp_path / "placeholder.png"
    Image.new("RGB", (64, 64), "#334455").save(source)

    resize_placeholder(source, (200, 160))

    with Image.open(source) as original:
        assert original.size == (64, 64)
        assert original.mode == "RGB"


class FakeAsset:
    def __init__(self, name: str, width: int | None = None, height: int | None = None):
        self.m_Name = name
        self.m_Width = width
        self.m_Height = height
        self.m_TextureFormat = 4


class FakeObject:
    def __init__(self, type_name: str, asset: FakeAsset):
        self.type = SimpleNamespace(name=type_name)
        self.asset = asset

    def read(self):
        return self.asset


def test_inject_refuses_to_overwrite_when_unitypy_cannot_add_objects(tmp_path: Path):
    assets = tmp_path / "assets"
    assets.mkdir()
    Image.new("RGB", (64, 64), "#334455").save(assets / "unit.png")
    Image.new("RGB", (64, 64), "#556677").save(assets / "portrait.png")
    env = SimpleNamespace(
        objects=[
            FakeObject("Texture2D", FakeAsset("mapUnit31", 768, 576)),
            FakeObject("Texture2D", FakeAsset("portrait1", 200, 160)),
            FakeObject("Sprite", FakeAsset("portrait1")),
        ]
    )
    manifest = {
        "unit_texture_candidates": ["mapUnit93", "mapUnit93_0"],
        "portrait_texture": "portrait170",
        "files": {
            "unit": "assets/unit.png",
            "portrait": "assets/portrait.png",
        },
    }

    with pytest.raises(
        TextureInjectionError,
        match=r"cannot add or clone Texture2D.*refusing to overwrite live textures",
    ):
        inject_textures(env, manifest, tmp_path)

    assert [obj.asset.m_Name for obj in env.objects] == [
        "mapUnit31",
        "portrait1",
        "portrait1",
    ]
