from __future__ import annotations


class TextAssetDiscoveryError(RuntimeError):
    pass


def _asset_name(asset) -> str:
    return getattr(asset, "m_Name", getattr(asset, "name", ""))


def _script_attribute(asset) -> str:
    if hasattr(asset, "m_Script"):
        return "m_Script"
    if hasattr(asset, "script"):
        return "script"
    raise TextAssetDiscoveryError(
        f"TextAsset {_asset_name(asset)!r} has no m_Script/script field"
    )


def _find_text_asset(env, name: str):
    assets = []
    inventory = []
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        asset = obj.read()
        asset_name = _asset_name(asset)
        inventory.append(asset_name or "<unnamed>")
        if asset_name == name:
            assets.append(asset)

    if len(assets) != 1:
        reason = "not found" if not assets else f"found {len(assets)} matches"
        listing = ", ".join(sorted(inventory)) or "<none>"
        raise TextAssetDiscoveryError(
            f"TextAsset {name!r} {reason}; TextAsset inventory: {listing}"
        )
    return assets[0]


def read_text_asset(env, name: str) -> str:
    asset = _find_text_asset(env, name)
    value = getattr(asset, _script_attribute(asset))
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode("utf-8")
    raise TypeError(f"TextAsset {name!r} script has unsupported type {type(value)!r}")


def write_text_asset(env, name: str, xml: str) -> None:
    asset = _find_text_asset(env, name)
    attribute = _script_attribute(asset)
    current = getattr(asset, attribute)
    value = xml.encode("utf-8") if isinstance(current, bytes) else xml
    setattr(asset, attribute, value)
    asset.save()
