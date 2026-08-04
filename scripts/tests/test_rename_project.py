from pathlib import Path

import pytest

from scripts.rename_project import rename_project, validate_names


def test_rename_project_updates_identifiers_and_package_directory(tmp_path: Path):
    source = tmp_path / "DjangoApiStarter"
    source.mkdir()
    (source / "settings.py").write_text("ROOT_URLCONF = 'DjangoApiStarter.urls'\n")
    (tmp_path / "pyproject.toml").write_text('name = "soda-starter"\n')
    (tmp_path / "README.md").write_text("# SODA Starter\n")

    changed = rename_project(
        tmp_path,
        package="gallery_tours",
        distribution="gallery-tours-api",
        display_name="Gallery Tours",
    )

    assert not source.exists()
    assert (tmp_path / "gallery_tours/settings.py").read_text() == (
        "ROOT_URLCONF = 'gallery_tours.urls'\n"
    )
    assert (tmp_path / "pyproject.toml").read_text() == ('name = "gallery-tours-api"\n')
    assert (tmp_path / "README.md").read_text() == "# Gallery Tours\n"
    assert len(changed) == 3


def test_rename_project_dry_run_does_not_write(tmp_path: Path):
    source = tmp_path / "DjangoApiStarter"
    source.mkdir()
    settings = source / "settings.py"
    settings.write_text("DjangoApiStarter")

    changed = rename_project(
        tmp_path,
        package="gallery_tours",
        distribution="gallery-tours-api",
        display_name="Gallery Tours",
        dry_run=True,
    )

    assert changed == [settings]
    assert source.exists()
    assert settings.read_text() == "DjangoApiStarter"


@pytest.mark.parametrize(
    "package,distribution",
    [
        ("GalleryTours", "gallery-tours"),
        ("gallery-tours", "gallery-tours"),
        ("gallery_tours", "Gallery-Tours"),
        ("gallery_tours", "gallery_tours"),
    ],
)
def test_validate_names_rejects_unsafe_identifiers(package, distribution):
    with pytest.raises(ValueError):
        validate_names(package, distribution, "Gallery Tours")
