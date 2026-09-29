from types import SimpleNamespace

import pytest

from tools.cf_patch.unity_text import (
    TextAssetDiscoveryError,
    read_text_asset,
    write_text_asset,
)


class FakeTextAsset:
    def __init__(self, name: str, script):
        self.m_Name = name
        self.m_Script = script
        self.saved = False

    def save(self):
        self.saved = True


class FakeObject:
    def __init__(self, asset, type_name: str = "TextAsset"):
        self.type = SimpleNamespace(name=type_name)
        self._asset = asset

    def read(self):
        return self._asset


def _environment(*objects):
    return SimpleNamespace(objects=list(objects))


def test_read_text_asset_reads_m_script_text():
    env = _environment(FakeObject(FakeTextAsset("UnitTypeData", "<UnitTypeData/>")))

    assert read_text_asset(env, "UnitTypeData") == "<UnitTypeData/>"


def test_read_text_asset_decodes_utf8_bytes():
    env = _environment(FakeObject(FakeTextAsset("LanguageData", "高达".encode())))

    assert read_text_asset(env, "LanguageData") == "高达"


def test_write_text_asset_saves_text_value():
    asset = FakeTextAsset("CharacterData", "<old/>")
    env = _environment(FakeObject(asset))

    write_text_asset(env, "CharacterData", "<new/>")

    assert asset.m_Script == "<new/>"
    assert asset.saved is True


def test_write_text_asset_preserves_bytes_storage():
    asset = FakeTextAsset("LanguageData", b"<old/>")
    env = _environment(FakeObject(asset))

    write_text_asset(env, "LanguageData", "<新/>")

    assert asset.m_Script == "<新/>".encode()
    assert asset.saved is True


def test_missing_text_asset_reports_inventory():
    env = _environment(
        FakeObject(FakeTextAsset("OtherData", "<OtherData/>")),
        FakeObject(FakeTextAsset("Ignored", ""), type_name="Texture2D"),
    )

    with pytest.raises(TextAssetDiscoveryError, match="OtherData"):
        read_text_asset(env, "UnitTypeData")
