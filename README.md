# BootWright

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
  collision-safe naming, and can add a custom `.iso` or download a
  catalogued Linux installer ISO into its own subfolder.
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

## Getting started

Run from the parent directory of `BootWright/` so it's importable as a
package:

```sh
python3 -m BootWright.menu
```

On first run this checks your platform's iPXE build dependencies and
offers to install anything missing. It then walks you through:

1. Selecting which iPXE features to enable
2. Selecting which target platform(s) to build
3. Building the selected images
4. Creating/verifying your TFTP root
5. Choosing which built images to deploy into it
6. Optionally adding a custom ISO or downloading a Linux installer ISO

You can also run the dependency checker on its own:

```sh
python3 BootWright/dependencies.py --install
```

## Project layout

```
BootWright/
  __init__.py       package metadata
  menu.py           interactive CLI flow
  pxe.py             iPXE clone/configure/build
  tftp.py             TFTP root creation and image/ISO deployment
  dependencies.py    cross-platform build dependency checker/installer
  vendor/ipxe/        iPXE source (cloned at runtime, not tracked in git)
```

## Status

Actively under development -- expect the feature/target catalogs and ISO
list to keep growing.

## License

See [LICENSE](LICENSE) (GPLv2), matching the license of iPXE itself.
