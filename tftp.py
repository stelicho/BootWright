"""Create and populate the TFTP root directory that PXE clients boot from."""

import platform
import shutil
import urllib.request
from pathlib import Path

# Conventional TFTP root per platform. macOS's is the path historically
# used by the built-in bootpd/tftpd (Internet Sharing), so it may already
# exist; the others are just common convention and are created if missing.
DEFAULT_TFTP_ROOTS: dict[str, Path] = {
    "Windows": Path("C:/tftpboot"),
    "Darwin": Path("/private/tftpboot"),
    "Linux": Path("/srv/tftpboot"),
    "FreeBSD": Path("/tftpboot"),
}
FALLBACK_TFTP_ROOT = Path("/tftpboot")

# Known Linux installer ISOs BootWright can fetch automatically. Minimal
# starter set -- more distros/mirrors/architectures to be added later.
LINUX_ISO_CATALOG: dict[str, dict[str, str]] = {
    "debian": {
        "label": "Debian 12 (bookworm) netinst, amd64",
        "url": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.9.0-amd64-netinst.iso",
        "subdir": "debian",
    },
    "fedora": {
        "label": "Fedora Server 41 netinst, x86_64",
        "url": "https://download.fedoraproject.org/pub/fedora/linux/releases/41/Server/x86_64/iso/Fedora-Server-netinst-x86_64-41-1.4.iso",
        "subdir": "fedora",
    },
}


def default_tftp_root() -> Path:
    return DEFAULT_TFTP_ROOTS.get(platform.system(), FALLBACK_TFTP_ROOT)


def ensure_tftp_root(root: Path | None = None) -> Path:
    """Create (or verify) the TFTP root directory, returning its path.

    Raises PermissionError if root doesn't exist and can't be created
    (e.g. it lives directly under / or C:\\ and requires elevation) --
    callers should catch this and offer the user an alternate path or
    ask them to re-run elevated, rather than silently escalating here.
    """
    root = root or default_tftp_root()
    if not root.is_dir():
        root.mkdir(parents=True, exist_ok=True)
    return root


def _avoid_collision(path: Path) -> Path:
    """If path already exists, append -1, -2, ... before the suffix until one is free."""
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def deploy_images(images: list[tuple[Path, str]], tftp_root: Path) -> list[Path]:
    """Move each (source_path, destination_filename) pair into the root of tftp_root.

    Destination filenames come from pxe.deployed_filename() and are
    stable per target, so re-deploying after a rebuild intentionally
    overwrites the previous image under the same name -- that's what lets
    a PXE/DHCP config with a fixed boot-filename keep working after an
    update, instead of pointing at a stale image.
    """
    destinations = []
    for source, destination_name in images:
        destination = tftp_root / destination_name
        shutil.move(str(source), str(destination))
        destinations.append(destination)
    return destinations


def add_custom_iso(iso_path: Path, tftp_root: Path, folder_name: str) -> Path:
    """Copy a user-supplied ISO into tftp_root/folder_name/, returning its new path.

    Unlike deploy_images, this is a one-off user-supplied asset, not a
    rebuild of something with a stable name -- so an existing file with
    the same name is a genuine naming collision, not an intentional
    update, and gets a numeric suffix instead of being overwritten.
    """
    destination_dir = tftp_root / folder_name
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = _avoid_collision(destination_dir / iso_path.name)
    shutil.copy2(str(iso_path), str(destination))
    return destination


def linux_iso_destination(distro_key: str, tftp_root: Path) -> Path:
    """Return where download_linux_iso() would place distro_key's ISO, without downloading it."""
    entry = LINUX_ISO_CATALOG[distro_key]
    return tftp_root / entry["subdir"] / Path(entry["url"]).name


def download_linux_iso(distro_key: str, tftp_root: Path) -> Path:
    """Download a catalogued Linux installer ISO into tftp_root/<distro>/, returning its path.

    If that exact file already exists, it's treated as already
    downloaded (the catalog URL is pinned to a specific release, so the
    content would be identical) and re-download is skipped rather than
    overwriting or renaming.
    """
    entry = LINUX_ISO_CATALOG[distro_key]
    destination = linux_iso_destination(distro_key, tftp_root)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        return destination

    with urllib.request.urlopen(entry["url"]) as response, open(destination, "wb") as out_file:
        shutil.copyfileobj(response, out_file)

    return destination
