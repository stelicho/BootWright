from BootWright import bootscript


def test_render_boot_menu_with_no_entries_just_exits():
    rendered = bootscript.render_boot_menu([])
    assert rendered == "#!ipxe\nexit\n"


def test_render_boot_menu_lists_every_entry_and_wires_up_goto():
    entries = [bootscript.local_disk_entry(), bootscript.shell_entry()]
    rendered = bootscript.render_boot_menu(entries)

    assert "item option0 Boot from local disk" in rendered
    assert "item option1 iPXE shell" in rendered
    assert ":option0" in rendered and "exit" in rendered
    assert ":option1" in rendered and "shell" in rendered
    assert "choose --timeout 15000 --default option0 selected || goto MENU" in rendered


def test_render_boot_menu_includes_background_picture_command():
    rendered = bootscript.render_boot_menu(
        [bootscript.local_disk_entry()], background_url="http://example/bg.png"
    )
    assert "console --picture http://example/bg.png --keep" in rendered


def test_iso_entry_sanboots_the_relative_path():
    entry = bootscript.iso_entry("Debian", "debian/debian-13.7.0-amd64-netinst.iso")
    assert entry.label == "Debian"
    assert entry.boot_commands == (
        "sanboot --no-describe tftp://${next-server}/debian/debian-13.7.0-amd64-netinst.iso "
        "|| goto MENU",
    )


def test_write_boot_menu_writes_to_tftp_root(tmp_path):
    destination = bootscript.write_boot_menu(tmp_path, [bootscript.local_disk_entry()])
    assert destination == tmp_path / "boot.ipxe"
    assert destination.read_text().startswith("#!ipxe\n")
