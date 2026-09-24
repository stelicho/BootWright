"""Check for (and optionally install) iPXE's build-time dependencies.

Per https://ipxe.org build requirements: gcc, binutils, make, perl,
liblzma/xz headers, mtools, an ISO mastering tool (mkisofs / genisoimage /
xorrisofs), and syslinux (for isolinux.bin, only needed for .iso images).

Package manager coverage:
  macOS:    Homebrew (brew), MacPorts (port)
  Windows:  Chocolatey (choco), Scoop (scoop), winget, Cygwin (apt-cyg)
  Linux:    apt, dnf, pacman, zypper, apk, emerge (Gentoo), xbps (Void)
  FreeBSD:  pkg

Package names below are best-effort per manager/repo -- verify with that
manager's own search command if an install fails.

Checking is always safe and read-only. Installing requires --install and,
per-command, a confirmation prompt, since it modifies shared system state
and may need elevated privileges.
"""

import argparse
import ctypes
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PackageManager = str

PACKAGE_ROOT = Path(__file__).resolve().parent
FIRST_RUN_MARKER = PACKAGE_ROOT / ".dependencies_checked"


@dataclass(frozen=True)
class Dependency:
    name: str
    binaries: tuple[str, ...]  # any one of these on PATH satisfies the dependency
    packages: dict[PackageManager, str | None]  # None = no known package for that manager
    note: str = ""


DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency(
        "gcc", ("gcc",),
        {"brew": "gcc", "macports": "gcc", "apt": "gcc", "dnf": "gcc", "pacman": "gcc",
         "zypper": "gcc", "apk": "gcc", "pkg": "gcc", "emerge": "sys-devel/gcc",
         "xbps": "gcc", "choco": "mingw", "scoop": "gcc", "winget": "MSYS2.MSYS2",
         "cygwin": "gcc-core"},
        note="On Windows, a working GNU toolchain is best obtained via MSYS2 or WSL.",
    ),
    Dependency(
        "binutils", ("as", "ld", "objcopy", "ar", "ranlib"),
        {"brew": "binutils", "macports": "binutils", "apt": "binutils", "dnf": "binutils",
         "pacman": "binutils", "zypper": "binutils", "apk": "binutils", "pkg": "binutils",
         "emerge": "sys-devel/binutils", "xbps": "binutils", "choco": "mingw",
         "scoop": "binutils", "winget": "MSYS2.MSYS2", "cygwin": "binutils"},
    ),
    Dependency(
        "make", ("make", "gmake"),
        {"brew": "make", "macports": "gmake", "apt": "make", "dnf": "make", "pacman": "make",
         "zypper": "make", "apk": "make", "pkg": "gmake", "emerge": "sys-devel/make",
         "xbps": "make", "choco": "make", "scoop": "make", "winget": "GnuWin32.Make",
         "cygwin": "make"},
    ),
    Dependency(
        "perl", ("perl",),
        {"brew": "perl", "macports": "perl5", "apt": "perl", "dnf": "perl", "pacman": "perl",
         "zypper": "perl", "apk": "perl", "pkg": "perl5", "emerge": "dev-lang/perl",
         "xbps": "perl", "choco": "strawberryperl", "scoop": "perl",
         "winget": "StrawberryPerl.StrawberryPerl", "cygwin": "perl"},
    ),
    Dependency(
        "liblzma (xz)", ("xz",),
        {"brew": "xz", "macports": "xz", "apt": "liblzma-dev", "dnf": "xz-devel",
         "pacman": "xz", "zypper": "xz-devel", "apk": "xz-dev", "pkg": "liblzma",
         "emerge": "app-arch/xz-utils", "xbps": "liblzma-devel", "choco": "xz",
         "scoop": "xz", "winget": "XZUtils.XZUtils", "cygwin": "liblzma-devel"},
        note="Checked via the xz binary; the actual build need is the liblzma headers.",
    ),
    Dependency(
        "mtools", ("mcopy", "mtools"),
        {"brew": "mtools", "macports": "mtools", "apt": "mtools", "dnf": "mtools",
         "pacman": "mtools", "zypper": "mtools", "apk": "mtools", "pkg": "mtools",
         "emerge": "sys-fs/mtools", "xbps": "mtools", "choco": None, "scoop": None,
         "winget": None, "cygwin": "mtools"},
        note="Only needed for bin/ipxe.usb; no common Windows package.",
    ),
    Dependency(
        "ISO mastering tool", ("xorrisofs", "mkisofs", "genisoimage"),
        {"brew": "xorriso", "macports": "xorriso", "apt": "genisoimage", "dnf": "genisoimage",
         "pacman": "libisoburn", "zypper": "mkisofs", "apk": "xorriso", "pkg": "cdrtools",
         "emerge": "app-cdr/cdrtools", "xbps": "xorriso", "choco": None, "scoop": None,
         "winget": None, "cygwin": None},
        note="Only needed for bin/ipxe.iso.",
    ),
    Dependency(
        "syslinux", ("syslinux", "isolinux-bin"),
        {"brew": None, "macports": None, "apt": "syslinux", "dnf": "syslinux",
         "pacman": "syslinux", "zypper": "syslinux", "apk": "syslinux", "pkg": None,
         "emerge": "sys-boot/syslinux", "xbps": "syslinux", "choco": None, "scoop": None,
         "winget": None, "cygwin": None},
        note="Provides isolinux.bin for bin/ipxe.iso only; not packaged for macOS or Windows.",
    ),
)

# Per-OS candidate managers, in priority order, as (manager_name, probe_binary).
_CANDIDATES_BY_OS: dict[str, list[tuple[str, str]]] = {
    "Darwin": [("brew", "brew"), ("macports", "port")],
    "Windows": [("choco", "choco"), ("scoop", "scoop"), ("winget", "winget")],
    "Linux": [
        ("apt", "apt-get"), ("dnf", "dnf"), ("pacman", "pacman"), ("zypper", "zypper"),
        ("apk", "apk"), ("emerge", "emerge"), ("xbps", "xbps-install"),
    ],
    "FreeBSD": [("pkg", "pkg")],
}


def detect_package_managers() -> list[PackageManager]:
    """Return every supported package manager found on PATH, in priority order."""
    system = platform.system()

    if system.startswith("CYGWIN"):
        return ["cygwin"] if shutil.which("apt-cyg") else []

    candidates = _CANDIDATES_BY_OS.get(system, [])
    found = [name for name, probe in candidates if shutil.which(probe)]

    if system == "Windows" and (shutil.which("apt-cyg") or shutil.which("cygcheck")):
        found.append("cygwin")

    return found


def is_satisfied(dep: Dependency) -> bool:
    return any(shutil.which(binary) for binary in dep.binaries)


def check_all() -> dict[str, bool]:
    return {dep.name: is_satisfied(dep) for dep in DEPENDENCIES}


def _is_admin() -> bool:
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except OSError:
            return False
    return os.geteuid() == 0


_ROOT_REQUIRED_MANAGERS = {"apt", "dnf", "pacman", "zypper", "apk", "pkg", "macports", "emerge", "xbps"}

_INSTALL_COMMANDS: dict[PackageManager, list[str]] = {
    "brew": ["brew", "install", "{package}"],
    "macports": ["port", "install", "{package}"],
    "apt": ["apt-get", "install", "-y", "{package}"],
    "dnf": ["dnf", "install", "-y", "{package}"],
    "pacman": ["pacman", "-S", "--noconfirm", "{package}"],
    "zypper": ["zypper", "install", "-y", "{package}"],
    "apk": ["apk", "add", "{package}"],
    "pkg": ["pkg", "install", "-y", "{package}"],
    "emerge": ["emerge", "--ask=n", "{package}"],
    "xbps": ["xbps-install", "-y", "{package}"],
    "choco": ["choco", "install", "-y", "{package}"],
    "scoop": ["scoop", "install", "{package}"],
    "winget": ["winget", "install", "--id", "{package}", "-e"],
    "cygwin": ["apt-cyg", "install", "{package}"],
}


def install_command(manager: PackageManager, package: str) -> list[str]:
    command = [part.format(package=package) for part in _INSTALL_COMMANDS[manager]]
    if manager in _ROOT_REQUIRED_MANAGERS and not _is_admin():
        command = ["sudo", *command]
    return command


def choose_package_manager(managers: list[PackageManager]) -> PackageManager | None:
    if not managers:
        return None
    if len(managers) == 1:
        return managers[0]

    print("\nMultiple package managers found:")
    for index, manager in enumerate(managers, start=1):
        print(f"  {index}. {manager}")
    choice = input(f"Use which one? [1-{len(managers)}] ").strip()
    if choice.isdigit() and 0 < int(choice) <= len(managers):
        return managers[int(choice) - 1]
    return None


def install_missing(manager: PackageManager, missing: list[Dependency], assume_yes: bool) -> None:
    for dep in missing:
        package = dep.packages.get(manager)
        if package is None:
            print(f"  Skipping {dep.name}: no known {manager} package. {dep.note}")
            continue

        command = install_command(manager, package)
        print(f"\n{dep.name}: {' '.join(command)}")
        if not assume_yes:
            answer = input("  Run this command? [y/N] ").strip().lower()
            if answer not in ("y", "yes"):
                continue

        subprocess.run(command, check=True)


def report(statuses: dict[str, bool]) -> None:
    print("iPXE build dependency check:")
    for dep in DEPENDENCIES:
        status = "OK" if statuses[dep.name] else "MISSING"
        print(f"  [{status}] {dep.name}")


def ensure_dependencies_installed(assume_yes: bool = False) -> None:
    """On first run only, check dependencies and offer to install any that are missing.

    Marks itself done via FIRST_RUN_MARKER regardless of outcome, so the
    menu doesn't re-prompt every launch -- rerun with --install (main())
    directly if something was skipped and needs another pass. assume_yes
    skips the per-package confirmation prompt (from the CLI's --yes).
    """
    if FIRST_RUN_MARKER.exists():
        return

    print("First run detected -- checking iPXE build dependencies for your platform...")
    statuses = check_all()
    report(statuses)

    missing = [dep for dep in DEPENDENCIES if not statuses[dep.name]]
    if missing:
        managers = detect_package_managers()
        manager = choose_package_manager(managers)
        if manager is None:
            print("\nNo supported package manager detected; install the above manually.")
        else:
            print(f"\nUsing package manager: {manager}")
            install_missing(manager, missing, assume_yes=assume_yes)
    else:
        print("\nAll dependencies satisfied.")

    FIRST_RUN_MARKER.touch()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Attempt to install missing dependencies.")
    parser.add_argument("--yes", action="store_true", help="Don't prompt before each install command.")
    args = parser.parse_args()

    statuses = check_all()
    report(statuses)

    missing = [dep for dep in DEPENDENCIES if not statuses[dep.name]]
    if not missing:
        print("\nAll dependencies satisfied.")
        return

    if not args.install:
        print("\nRun with --install to attempt installing missing dependencies.")
        return

    managers = detect_package_managers()
    manager = choose_package_manager(managers)
    if manager is None:
        print("\nNo supported package manager detected; install the above manually.")
        return

    print(f"\nUsing package manager: {manager}")
    install_missing(manager, missing, assume_yes=args.yes)


if __name__ == "__main__":
    main()
