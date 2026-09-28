# pylint: disable=protected-access
from pathlib import Path

from BootWright import tftp


def test_avoid_collision_returns_same_path_when_free(tmp_path):
    target = tmp_path / "image.iso"
    assert tftp._avoid_collision(target) == target


def test_avoid_collision_appends_incrementing_suffix(tmp_path):
    target = tmp_path / "image.iso"
    target.write_bytes(b"existing")
    (tmp_path / "image-1.iso").write_bytes(b"existing")

    result = tftp._avoid_collision(target)

    assert result == tmp_path / "image-2.iso"


def test_linux_iso_destination_matches_catalog_subdir_and_filename(tmp_path):
    for distro_key, entry in tftp.LINUX_ISO_CATALOG.items():
        expected = tmp_path / entry["subdir"] / Path(entry["url"]).name
        assert tftp.linux_iso_destination(distro_key, tmp_path) == expected


def test_deploy_images_moves_files_to_tftp_root(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    tftp_root = tmp_path / "tftpboot"
    tftp_root.mkdir()

    source_file = source_dir / "ipxe.pxe"
    source_file.write_bytes(b"stub")

    deployed = tftp.deploy_images([(source_file, "ipxe.pxe")], tftp_root)

    assert deployed == [tftp_root / "ipxe.pxe"]
    assert (tftp_root / "ipxe.pxe").read_bytes() == b"stub"
    assert not source_file.exists()


def test_add_custom_iso_avoids_overwriting_existing_file(tmp_path):
    tftp_root = tmp_path / "tftpboot"
    tftp_root.mkdir()
    iso_path = tmp_path / "custom.iso"
    iso_path.write_bytes(b"new content")

    (tftp_root / "myfolder").mkdir()
    (tftp_root / "myfolder" / "custom.iso").write_bytes(b"old content")

    destination = tftp.add_custom_iso(iso_path, tftp_root, "myfolder")

    assert destination == tftp_root / "myfolder" / "custom-1.iso"
    assert destination.read_bytes() == b"new content"
    assert (tftp_root / "myfolder" / "custom.iso").read_bytes() == b"old content"


def test_default_tftp_root_has_an_entry_for_every_platform_name(monkeypatch):
    for system_name, expected_root in tftp.DEFAULT_TFTP_ROOTS.items():
        monkeypatch.setattr(tftp.platform, "system", lambda name=system_name: name)
        assert tftp.default_tftp_root() == expected_root


def test_default_tftp_root_falls_back_for_unknown_platform(monkeypatch):
    monkeypatch.setattr(tftp.platform, "system", lambda: "PlanNine")
    assert tftp.default_tftp_root() == tftp.FALLBACK_TFTP_ROOT
