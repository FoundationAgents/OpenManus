import pytest

from app.utils.files_utils import should_exclude_file


@pytest.mark.parametrize(
    "path",
    [
        "src/building/main.py",
        "src/rebuild/main.py",
        "docs/distribution/api.md",
        ".github/workflows/ci.yml",
        "node_modules_backup/readme.md",
        "nested/distilled/readme.md",
        "src/build.py",
    ],
)
def test_directory_name_substrings_are_not_excluded(path):
    assert not should_exclude_file(path)


@pytest.mark.parametrize(
    "path",
    [
        "build/main.py",
        "src/build/main.py",
        "dist/main.js",
        "node_modules/package/index.js",
        "nested/.git/config",
        "nested/.next/cache/data.txt",
        "nested/.gitignore",
        "nested/package-lock.json",
        "nested/image.PNG",
    ],
)
def test_existing_exclusion_rules_are_preserved(path):
    assert should_exclude_file(path)
