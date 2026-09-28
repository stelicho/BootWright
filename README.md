# BootWright

[![Pylint](https://github.com/stelicho/BootWright/actions/workflows/pylint.yml/badge.svg)](https://github.com/stelicho/BootWright/actions/workflows/pylint.yml)
[![Tests](https://github.com/stelicho/BootWright/actions/workflows/tests.yml/badge.svg)](https://github.com/stelicho/BootWright/actions/workflows/tests.yml)

BootWright is a collection of Python scripts that automate building a fully
functional PXE boot environment on top of [iPXE](https://ipxe.org). It walks
you through checking build dependencies, choosing which iPXE features and
target platforms to compile, building the resulting boot images, and
deploying them into a TFTP root -- optionally alongside custom or
downloaded installer ISOs.

## Features

- **Cross-platform dependency setup** (`dependencies.py`) -- checks for
  iPXE's build requirements (gcc, binutils, make, perl, liblzma, mtools, an
  ISO mastering tool, syslinux) and can install missing ones through
  whichever package manager is available: Homebrew or MacPorts (macOS),
  Chocolatey/Scoop/winget/Cygwin (Windows), apt/dnf/pacman/zypper/apk/
  emerge/xbps (Linux), or pkg (FreeBSD).
- **iPXE build automation** (`pxe.py`) -- clones/updates the iPXE source,
  generates a `src/config/local/general.h` override from a curated list of
  feature toggles (download protocols, console types, boot commands,
  image formats), and drives iPXE's own Makefile to build any combination
  of:
  - BIOS (x86 / x86_64)
  - UEFI32 (i386)
  - UEFI64 (x86_64)
  - ARM32 (UEFI)
  - ARM64 (UEFI)
- **TFTP root deployment** (`tftp.py`) -- creates/verifies the platform's
  conventional TFTP root (`C:\tftpboot`, `/private/tftpboot`,
  `/srv/tftpboot`, or `/tftpboot`), moves the built images in with
  collision-safe naming, and can add a custom `.iso` or download any of a
  dozen catalogued Linux installer ISOs (Debian, Ubuntu, Fedora, Rocky,
  AlmaLinux, openSUSE, Arch, Alpine, across amd64/arm64 where available)
  into its own subfolder.
- **WinPE / Windows install guidance** (`winpe.py`) -- prints a walkthrough,
  based on [iPXE's own wiki](https://ipxe.org/howto/winpe), for building a
  WinPE network-boot image with the Windows ADK and installing Windows onto
  a client from a fileshare. This is guidance only: creating the WinPE image
  requires Microsoft's Windows-only tooling, so BootWright doesn't attempt
  to automate it.
- **Interactive menu** (`menu.py`) -- ties all of the above together into
  a single guided flow.

## Requirements

- Python 3.11+
- Git
- A supported package manager for your OS (see above) if you want
  BootWright to install missing build tools for you
- A working GNU-style `gcc`/`binutils` toolchain for the platforms you
  intend to build; cross-compiling ARM images from a non-ARM host needs
  an ARM cross-compiler (e.g. `aarch64-linux-gnu-gcc`,
  `arm-linux-gnueabihf-gcc`) on `PATH`

## Installation

```sh
pip install .
```

or, for local development (editable install, plus `pytest`/`pylint`):

```sh
pip install -e ".[dev]"
```

This installs a `bootwright` console command.

## Getting started

```sh
bootwright
```

On first run this checks your platform's iPXE build dependencies and
offers to install anything missing. It then walks you through:

1. Selecting which iPXE features to enable
2. Selecting which target platform(s) to build
3. Building the selected images
4. Creating/verifying your TFTP root
5. Choosing which built images to deploy into it
6. Optionally adding a custom ISO, downloading catalogued Linux installer
   ISOs, and setting a boot menu background
7. Optionally enabling a TFTP/HTTP service and getting WinPE/Windows-install
   guidance

`bootwright --help` lists flags for skipping the dependency check
(`--no-depends`), overriding the TFTP root (`--tftp-root`), and
auto-confirming dependency installs (`--yes`).

You can also run the dependency checker on its own:

```sh
python3 -m BootWright.dependencies --install
```

## Project layout

```
BootWright/
  __init__.py       package metadata
  cli.py             `bootwright` console-script entry point
  menu.py            interactive CLI flow
  pxe.py             iPXE clone/configure/build
  tftp.py            TFTP root creation and image/ISO deployment
  bootscript.py      renders the on-target boot.ipxe menu
  services.py        TFTP/HTTP service setup and DHCP configuration advice
  dependencies.py    cross-platform build dependency checker/installer
  winpe.py           WinPE + Windows-install-fileshare setup guidance
  vendor/ipxe/       iPXE source (cloned at runtime, not tracked in git)
tests/               pytest suite for the modules above
```

## Testing

```sh
pip install -e ".[dev]"
pytest
pylint src/BootWright tests
```

## Versioning

BootWright follows [Semantic Versioning](https://semver.org/):
`MAJOR.MINOR.PATCH`. While the major version is `0` (pre-1.0), the CLI's
flags, module APIs, and catalogs may still change between minor versions
without a deprecation period -- treat `0.x` as "usable, but not yet a
stability guarantee." Once `1.0.0` ships, `MAJOR` bumps mean breaking
changes, `MINOR` bumps mean backwards-compatible features, and `PATCH`
bumps mean backwards-compatible fixes.

Each release is tagged `vMAJOR.MINOR.PATCH` (e.g. `v0.2.0`) and recorded in
[CHANGELOG.md](CHANGELOG.md). The version in `pyproject.toml` and
`BootWright.__version__` always matches the most recent tag.

## Status

Actively under development -- expect the feature/target catalogs and ISO
list to keep growing. See [ROADMAP.md](ROADMAP.md) for what's implemented
and what's next, and [CHANGELOG.md](CHANGELOG.md) for what's already
shipped.

## License

See [LICENSE](LICENSE) (GPLv2), matching the license of iPXE itself.
