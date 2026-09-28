# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versioning follows [Semantic Versioning](https://semver.org/) -- see
"Versioning" in [README.md](README.md) for what that means while
BootWright is still pre-1.0.

## [0.2.0] - 2026-09-27

### Added

- GitHub Actions CI: `pylint` and `pytest` on every push/PR
  (`.github/workflows/`)
- `winpe.py`: guided (non-automated) walkthrough for network-booting
  WinPE and installing Windows from a fileshare, per
  [ipxe.org/howto/winpe](https://ipxe.org/howto/winpe)
- `tests/`: pytest suite covering `pxe`, `tftp`, `bootscript`, `cli`,
  `menu`, and `winpe`
- `SECURITY.md`
- A GitHub wiki user guide (installation, usage, features, ISOs, WinPE,
  services/DHCP, troubleshooting)
- `LINUX_ISO_CATALOG` entries for Ubuntu, Rocky Linux, AlmaLinux,
  openSUSE, Arch Linux, and Alpine, alongside Debian and Fedora, mostly
  across amd64/arm64
- `pyproject.toml` classifiers, keywords, and a `dev` extra
  (`pytest`, `pylint`)

### Fixed

- `LINUX_ISO_CATALOG`'s Debian entries, which 404'd (they were pinned to
  Debian 12, but the "current" URL now serves Debian 13)
- `LINUX_ISO_CATALOG`'s Fedora entry, updated from a stale release 41
  URL to the current release 43

## [0.1.0] - 2026-09-25

### Added

- Initial `bootwright` pip-installable CLI (`cli.py`, `pyproject.toml`)
- iPXE build automation: clone/update vendored iPXE, feature-toggle
  config generation, multi-target builds (`pxe.py`)
- TFTP root creation and image/ISO deployment, with an initial
  `LINUX_ISO_CATALOG` (Debian, Fedora) (`tftp.py`)
- Generated on-target boot menu (`boot.ipxe`) (`bootscript.py`)
- Cross-platform build-dependency checker/installer (`dependencies.py`)
- TFTP/HTTP service activation and DHCP configuration advice
  (`services.py`)
- Interactive menu tying the above together (`menu.py`)

[0.2.0]: https://github.com/stelicho/BootWright/releases/tag/v0.2.0
[0.1.0]: https://github.com/stelicho/BootWright/releases/tag/v0.1.0
