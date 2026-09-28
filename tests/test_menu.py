from BootWright import menu


def test_select_targets_parses_comma_separated_numbers(monkeypatch):
    keys = list(menu.pxe.TARGETS.keys())
    monkeypatch.setattr("builtins.input", lambda prompt="": "1, 3")

    assert menu.select_targets() == [keys[0], keys[2]]


def test_select_targets_ignores_out_of_range_and_non_numeric_parts(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "1, abc, 999")

    assert menu.select_targets() == [list(menu.pxe.TARGETS.keys())[0]]


def test_offer_linux_iso_download_all_downloads_every_catalog_entry(monkeypatch, tmp_path):
    responses = iter(["y", "all"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
    monkeypatch.setattr(
        menu.tftp, "download_linux_iso", lambda key, root: root / f"{key}.iso"
    )

    entries = menu.offer_linux_iso_download(tmp_path)

    assert len(entries) == len(menu.tftp.LINUX_ISO_CATALOG)


def test_offer_linux_iso_download_declines_when_user_says_no(monkeypatch, tmp_path):
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    assert not menu.offer_linux_iso_download(tmp_path)


def test_offer_linux_iso_download_selects_specific_entries(monkeypatch, tmp_path):
    catalog_keys = list(menu.tftp.LINUX_ISO_CATALOG.keys())
    responses = iter(["y", "2"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
    monkeypatch.setattr(
        menu.tftp, "download_linux_iso", lambda key, root: root / f"{key}.iso"
    )

    entries = menu.offer_linux_iso_download(tmp_path)

    assert len(entries) == 1
    assert entries[0].label == menu.tftp.LINUX_ISO_CATALOG[catalog_keys[1]]["label"]
