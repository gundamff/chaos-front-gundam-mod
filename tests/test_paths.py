from tools.common.paths import repo_root, resources_assets


def test_repo_root_contains_patches():
    assert (repo_root() / "patches" / "v1-rx78.yaml").is_file()


def test_resources_assets_name():
    assert resources_assets().name == "resources.assets"
