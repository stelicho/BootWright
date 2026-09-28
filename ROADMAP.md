# BootWright Roadmap

_Last updated: 2026-09-27. Living doc -- edit freely as priorities change._

## Current status

BootWright (v0.2.0) is a working, end-to-end CLI for building a PXE boot
environment on top of iPXE. Every module below is implemented (no stubs),
but the catalogs it draws from (features, targets, distro ISOs) are
intentionally small starter sets meant to grow over time.

| Module | Responsibility |
| --- | --- |
| `cli.py` | `bootwright` console-script entry point; parses `--no-depends`, `--tftp-root`, `--yes` |
| `dependencies.py` | Detects/installs iPXE build deps (gcc, binutils, make, perl, liblzma, mtools, ISO tool, syslinux) across brew/macports/apt/dnf/pacman/zypper/apk/pkg/emerge/xbps/choco/scoop/winget/cygwin |
| `pxe.py` | Clones/updates vendored iPXE, writes `config/local/general.h` from `FEATURE_OPTIONS`, runs iPXE's Makefile for each `TARGETS` entry (bios, uefi-i386, uefi-x86_64, uefi-arm32, uefi-arm64) |
| `bootscript.py` | Renders the on-target `boot.ipxe` menu and the static embed bootstrap script baked into every build |
| `tftp.py` | Creates the platform TFTP root, deploys built images, adds custom/catalogued ISOs (`LINUX_ISO_CATALOG`: Debian, Ubuntu, Fedora, Rocky, AlmaLinux, openSUSE, Arch, Alpine -- amd64/arm64 where the distro publishes both), adds background images |
| `services.py` | Enables a TFTP daemon (macOS built-in tftpd, Debian/Ubuntu tftpd-hpa), starts a background HTTP fallback server, prints DHCP configuration guidance |
| `winpe.py` | Prints WinPE network-boot + Windows-install-fileshare setup guidance (per https://ipxe.org/howto/winpe); guidance only, no automation -- see Known limitations |
| `menu.py` | Interactive flow tying all of the above together |

`tests/` covers the pure/testable functions in each module above (pytest);
CI runs both `pytest` and `pylint` on every push/PR (`.github/workflows/`).

## Current flow (`menu.run()`, invoked by `bootwright`)

1. **Print banner.**
2. **Dependency check** -- `dependencies.ensure_dependencies_installed()`, skipped after first run (marker file) or with `--no-depends`.
3. **Sync iPXE source** -- `pxe.clone_or_update_ipxe()` clones or `git pull --ff-only`s `vendor/ipxe/`.
4. **Select features** -- walks every macro in `pxe.FEATURE_OPTIONS` (download protocols, network protocols, console, commands, image formats), y/n prompt per macro.
5. **Write config override** -- `pxe.write_local_config()` writes `src/config/local/general.h` with `#define`/`#undef` for every known macro.
6. **Select build targets** -- comma-separated pick from `pxe.TARGETS`; exits early if none chosen.
7. **Build** -- `pxe.build_targets()` runs iPXE's Makefile per target (checks for the right `gcc`/cross-compiler first), embedding the static bootstrap script; `pxe.list_build_outputs()` collects the resulting files.
8. **Resolve TFTP root** -- `menu.resolve_tftp_root()` uses `--tftp-root` or the platform default (`/private/tftpboot`, `/srv/tftpboot`, `C:\tftpboot`, `/tftpboot`), retrying on `PermissionError` by prompting for an alternate path.
9. **Select images to deploy** -- comma-separated or `'all'` pick from the just-built outputs; `tftp.deploy_images()` moves them into the TFTP root (UEFI outputs get disambiguated via `pxe.deployed_filename()` since they're all literally named `ipxe.efi`).
10. **Assemble boot menu entries** -- starts with "Boot from local disk", adds "iPXE shell" if `SHELL_CMD` was enabled.
11. **Offer a custom ISO** -- optional; copies a user-supplied `.iso` into its own subfolder and adds a sanboot menu entry.
12. **Offer catalogued Linux ISOs** -- optional; comma-separated or `'all'` pick from `LINUX_ISO_CATALOG`, downloads each, adds one sanboot menu entry per ISO.
13. **Offer a background image** -- optional; copies a local image or accepts a URL for the boot menu's `--picture` background.
14. **Write the boot menu** -- `bootscript.write_boot_menu()` renders `boot.ipxe` into the TFTP root from the assembled entries.
15. **Offer to enable a TFTP service** -- optional; macOS built-in tftpd or Debian/Ubuntu tftpd-hpa only, otherwise prints manual guidance.
16. **Offer to start an HTTP fallback server** -- optional; prefers `darkhttpd`, falls back to `python -m http.server`, runs in the background for the rest of the session.
17. **Offer WinPE / Windows-install guidance** -- optional; `winpe.print_winpe_guidance()` prints the copype/wimboot/boot.ipxe/fileshare walkthrough, tailored to the host OS for the fileshare step.
18. **Print DHCP configuration advice** -- next-server IP, boot filenames to hand out per client architecture, and notes on iPXE-aware chainloading to `boot.ipxe`.

## Known limitations / open items

- `LINUX_ISO_CATALOG` URLs are mostly pinned to specific point releases and will go stale (AlmaLinux's `-latest-` alias and Arch's kernel.org `latest/` alias are exceptions -- those two stay current on their own).
- `FEATURE_OPTIONS` is a curated subset of iPXE's full `general.h` macro set.
- Automatic TFTP service setup only covers macOS and Debian/Ubuntu; every other Linux distro and FreeBSD get manual instructions.
- DHCP server configuration is advisory only -- BootWright never touches a DHCP server itself.
- WinPE/Windows-install setup is guidance-only -- BootWright doesn't download wimboot, generate install.bat/winpeshl.ini, or configure a fileshare itself. Building the actual WinPE image needs Microsoft's Windows ADK, which only runs on Windows; automating a fileshare is a bigger persistent system change than TFTP, so both are left to the user to run by hand.
- `menu.py`'s interactive prompts are the only UI; there's no non-interactive/scriptable mode beyond the existing `--no-depends`/`--tftp-root`/`--yes` flags.

## Ideas for next increments

- [x] Expand `LINUX_ISO_CATALOG` (more distros, mirrors, architectures)
- [x] Add a `tests/` directory (pure functions in `pxe.py`/`tftp.py`/`bootscript.py`, plus `cli.py`/`menu.py`)
- [x] CI: pylint + pytest on every push/PR
- [ ] A way to point the ISO catalog at an arbitrary URL without hardcoding it
- [ ] Automatic TFTP service setup for more distros (Fedora/RHEL, Arch, etc.)
- [ ] A non-interactive mode (flags/config file) for scripted/CI use
- [ ] Track and warn about ISO catalog entries whose pinned release has been superseded upstream
- [ ] Actually automate WinPE/fileshare setup where it's feasible (e.g. downloading wimboot, generating install.bat/winpeshl.ini and the boot.ipxe entry) instead of guidance-only
- [ ] A public wiki with usage docs, once this repo is no longer private
