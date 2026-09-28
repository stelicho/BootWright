from pathlib import Path

from BootWright import cli


def test_main_forwards_defaults_to_menu_run(monkeypatch):
    calls = []
    monkeypatch.setattr(cli.menu, "run", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr("sys.argv", ["bootwright"])

    cli.main()

    assert calls == [
        {"skip_dependencies": False, "tftp_root_override": None, "assume_yes": False}
    ]


def test_main_forwards_parsed_flags_to_menu_run(monkeypatch):
    calls = []
    monkeypatch.setattr(cli.menu, "run", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(
        "sys.argv", ["bootwright", "--no-depends", "--tftp-root", "/tmp/tftpboot", "--yes"]
    )

    cli.main()

    assert calls == [
        {
            "skip_dependencies": True,
            "tftp_root_override": Path("/tmp/tftpboot"),
            "assume_yes": True,
        }
    ]
