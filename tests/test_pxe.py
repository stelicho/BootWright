from pathlib import Path

from BootWright import pxe


def test_deployed_filename_disambiguates_uefi_targets():
    assert pxe.deployed_filename("uefi-x86_64", Path("/bin-x86_64-efi/ipxe.efi")) == (
        "ipxe-uefi-x86_64.efi"
    )
    assert pxe.deployed_filename("uefi-arm64", Path("/bin-arm64-efi/ipxe.efi")) == (
        "ipxe-uefi-arm64.efi"
    )


def test_deployed_filename_leaves_other_names_alone():
    assert pxe.deployed_filename("bios", Path("/bin/ipxe.pxe")) == "ipxe.pxe"
    assert pxe.deployed_filename("bios", Path("/bin/undionly.kpxe")) == "undionly.kpxe"


def test_write_local_config_defines_selected_and_undefs_the_rest(tmp_path):
    config_path = tmp_path / "general.h"
    all_macros = {name for group in pxe.FEATURE_OPTIONS.values() for name in group}
    selected = {"SHELL_CMD", "DOWNLOAD_PROTO_HTTP"}

    pxe.write_local_config(selected, config_path=config_path)
    text = config_path.read_text()

    for macro in selected:
        assert f"#define {macro}" in text
    for macro in all_macros - selected:
        assert f"#undef {macro}" in text


def test_write_local_config_creates_parent_directories(tmp_path):
    config_path = tmp_path / "nested" / "dir" / "general.h"
    pxe.write_local_config(set(), config_path=config_path)
    assert config_path.is_file()


def test_list_build_outputs_only_includes_existing_files(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "ipxe.pxe").write_bytes(b"stub")
    # undionly.kpxe intentionally left missing.

    produced = pxe.list_build_outputs({"bios": bin_dir})

    assert produced == [("bios", bin_dir / "ipxe.pxe")]


def test_find_compiler_returns_none_for_unknown_binary():
    assert pxe.find_compiler("definitely-not-a-real-cross-compile-prefix-") is None
