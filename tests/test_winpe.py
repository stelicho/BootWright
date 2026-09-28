# pylint: disable=protected-access
from pathlib import Path

from BootWright import winpe


def test_print_winpe_guidance_covers_the_core_ipxe_wiki_steps(capsys):
    winpe.print_winpe_guidance(Path("/srv/tftpboot"), http_port=8080)
    output = capsys.readouterr().out

    assert "copype amd64" in output
    assert "wimboot" in output
    assert "install.bat" in output
    assert "winpeshl.ini" in output
    assert "net use" in output
    assert "8080" in output


def test_print_winpe_guidance_without_http_port_still_mentions_a_web_server(capsys):
    winpe.print_winpe_guidance(Path("/srv/tftpboot"), http_port=None)
    output = capsys.readouterr().out
    assert "web server" in output


def test_fileshare_guidance_is_tailored_per_platform(monkeypatch):
    monkeypatch.setattr(winpe.platform, "system", lambda: "Windows")
    assert any("New-SmbShare" in line for line in winpe._fileshare_guidance())

    monkeypatch.setattr(winpe.platform, "system", lambda: "Darwin")
    assert any("Sharing" in line for line in winpe._fileshare_guidance())

    monkeypatch.setattr(winpe.platform, "system", lambda: "Linux")
    assert any("smb.conf" in line for line in winpe._fileshare_guidance())
