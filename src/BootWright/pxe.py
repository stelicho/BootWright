"""Clone, configure, and build iPXE boot images.

iPXE ships its own Makefile; there's nothing to generate there. What we
generate is a config override header at src/config/local/general.h (an
untracked location iPXE reads after its own config/general.h, so it can
#define/#undef feature macros without touching tracked files), and then
we invoke the existing Makefile with the right bin-<arch>-<platform>
target and CROSS_COMPILE prefix for the platforms the user picked.
"""

import shutil
import subprocess
from pathlib import Path

from . import bootscript

PACKAGE_ROOT = Path(__file__).resolve().parent
IPXE_REPO_URL = "https://github.com/ipxe/ipxe.git"
IPXE_SRC_DIR = PACKAGE_ROOT / "vendor" / "ipxe"
IPXE_BUILD_DIR = IPXE_SRC_DIR / "src"
LOCAL_CONFIG_PATH = IPXE_BUILD_DIR / "config" / "local" / "general.h"

# Curated feature toggles. Key is the exact iPXE preprocessor macro name;
# value is (description, default_enabled). Grouped by category for the menu.
# Not exhaustive -- see src/config/general.h for the full set.
FEATURE_OPTIONS: dict[str, dict[str, tuple[str, bool]]] = {
    "Download protocols": {
        "DOWNLOAD_PROTO_HTTP": ("HTTP downloads", True),
        "DOWNLOAD_PROTO_HTTPS": ("HTTPS downloads", True),
        "DOWNLOAD_PROTO_TFTP": ("TFTP downloads", True),
        "DOWNLOAD_PROTO_FTP": ("FTP downloads", False),
        "DOWNLOAD_PROTO_NFS": ("NFS downloads", False),
    },
    "Network protocols": {
        "NET_PROTO_IPV6": ("IPv6 support", True),
        "NET_PROTO_LLDP": ("Link Layer Discovery Protocol", True),
    },
    "Console": {
        "CONSOLE_FRAMEBUFFER": ("Graphical framebuffer console", False),
        "CONSOLE_SERIAL": ("Serial console", True),
        "CONSOLE_SYSLOG": ("Remote syslog console", False),
    },
    "Commands": {
        "SHELL_CMD": ("Interactive iPXE shell", True),
        "SANBOOT_CMD": ("sanboot command (boot from SAN)", True),
        "MENU_CMD": ("menu/iterm/isset boot menu commands", True),
        "PING_CMD": ("ping command", False),
        "VLAN_CMD": ("vcreate/vdestroy VLAN commands", False),
    },
    "Image formats": {
        "IMAGE_PNG": ("PNG image decoding", False),
        "IMAGE_GZIP": ("gzip-compressed image support", False),
        "IMAGE_SCRIPT": ("iPXE scripting (.ipxe files)", True),
    },
}

# Target platforms, named and ordered to match the BIOS/UEFI32/UEFI64/
# ARM32/ARM64 split used by pfSense and similar router-distro installers.
# There's no such thing as "ARM BIOS" -- legacy BIOS is an x86-only 16-bit
# real-mode firmware interface that ARM hardware has never implemented, so
# ARM targets are UEFI-only by nature, not by choice here.
#
# "bin" is the directory make will produce, matching iPXE's
# bin[-<arch>-<platform>] naming convention. cross_compile is a suggested
# CROSS_COMPILE prefix; None means the host's native compiler is expected
# to work.
TARGETS: dict[str, dict] = {
    "bios": {
        # A single i386 legacy-BIOS PXE ROM covers both x86 and x86_64
        # machines: BIOS always starts in 16-bit real mode regardless of
        # the CPU's 64-bit capability, so there's no separate "BIOS
        # x86_64" build to make.
        #
        # ipxe.pxe/undionly.kpxe are the raw TFTP-served PXE images.
        # ipxe.dsk/.iso/.usb are removable-media images -- out of scope for
        # a TFTP boot environment and skipped to avoid needing mtools/
        # xorriso/syslinux just to serve PXE. Add them back as their own
        # target later if bootable media is needed.
        "label": "BIOS (x86 / x86_64)",
        "bin": "bin",
        "outputs": ["ipxe.pxe", "undionly.kpxe"],
        "cross_compile": None,
    },
    "uefi-i386": {
        "label": "UEFI32 (i386)",
        "bin": "bin-i386-efi",
        "outputs": ["ipxe.efi"],
        "cross_compile": None,
    },
    "uefi-x86_64": {
        "label": "UEFI64 (x86_64)",
        "bin": "bin-x86_64-efi",
        "outputs": ["ipxe.efi"],
        "cross_compile": None,
    },
    "uefi-arm32": {
        "label": "ARM32 (UEFI)",
        "bin": "bin-arm32-efi",
        "outputs": ["ipxe.efi"],
        "cross_compile": "arm-linux-gnueabihf-",
    },
    "uefi-arm64": {
        "label": "ARM64 (UEFI)",
        "bin": "bin-arm64-efi",
        "outputs": ["ipxe.efi"],
        "cross_compile": "aarch64-linux-gnu-",
    },
}


def clone_or_update_ipxe(src_dir: Path = IPXE_SRC_DIR, repo_url: str = IPXE_REPO_URL) -> None:
    """Clone the iPXE repo into src_dir, or fetch+pull if it already exists."""
    if (src_dir / ".git").exists():
        subprocess.run(["git", "-C", str(src_dir), "pull", "--ff-only"], check=True)
    else:
        src_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo_url, str(src_dir)], check=True)


def find_compiler(cross_compile: str | None) -> str | None:
    """Return the path to the gcc binary iPXE's Makefile would use, or None if missing."""
    binary = f"{cross_compile or ''}gcc"
    return shutil.which(binary)


def write_local_config(selected_macros: set[str], config_path: Path = LOCAL_CONFIG_PATH) -> Path:
    """Write src/config/local/general.h enabling exactly selected_macros.

    Every known macro in FEATURE_OPTIONS is written as either #define
    (enabled) or #undef (disabled), so the result doesn't depend on
    general.h's own defaults.
    """
    all_macros = {name for group in FEATURE_OPTIONS.values() for name in group}

    lines = [
        "/* Auto-generated by BootWright. Do not edit; changes will be overwritten. */",
        "#ifndef CONFIG_LOCAL_GENERAL_H",
        "#define CONFIG_LOCAL_GENERAL_H",
        "",
    ]
    for macro in sorted(all_macros):
        lines.append(f"#define {macro}" if macro in selected_macros else f"#undef {macro}")
    lines.append("")
    lines.append("#endif /* CONFIG_LOCAL_GENERAL_H */")
    lines.append("")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines))
    return config_path


def write_embed_script(build_dir: Path = IPXE_BUILD_DIR) -> Path:
    """Write bootscript.DEFAULT_EMBED_SCRIPT to a fixed path make can EMBED=.

    The embed script is static (see bootscript.DEFAULT_EMBED_SCRIPT), so
    this only needs writing once regardless of which/how many targets
    get built.
    """
    destination = build_dir / ".bootwright-embed.ipxe"
    destination.write_text(bootscript.DEFAULT_EMBED_SCRIPT)
    return destination


def build_target(
    target_key: str,
    build_dir: Path = IPXE_BUILD_DIR,
    selected_macros: set[str] | None = None,
) -> Path:
    """Run make for a single target key from TARGETS, returning its bin directory.

    Every build gets EMBED=<the static bootstrap script>, so the result
    auto-chains to boot.ipxe at boot. That requires IMAGE_SCRIPT to be
    enabled; selected_macros is optional and only used to warn if it isn't.
    """
    target = TARGETS[target_key]
    cross_compile = target["cross_compile"]

    if find_compiler(cross_compile) is None:
        compiler = f"{cross_compile or ''}gcc"
        raise RuntimeError(
            f"No '{compiler}' found on PATH; required to build '{target['label']}'."
        )

    if selected_macros is not None and "IMAGE_SCRIPT" not in selected_macros:
        print(
            "Warning: IMAGE_SCRIPT is disabled -- the embedded bootstrap script "
            "won't run, so this image won't auto-chain to boot.ipxe."
        )

    embed_script = write_embed_script(build_dir)

    make_targets = [f"{target['bin']}/{output}" for output in target["outputs"]]
    command = ["make", f"EMBED={embed_script}"]
    if cross_compile:
        command.append(f"CROSS_COMPILE={cross_compile}")
    command.extend(make_targets)

    subprocess.run(command, cwd=str(build_dir), check=True)
    return build_dir / target["bin"]


def build_targets(
    target_keys: list[str],
    build_dir: Path = IPXE_BUILD_DIR,
    selected_macros: set[str] | None = None,
) -> dict[str, Path]:
    """Build each requested target, returning a mapping of target key to its bin directory."""
    return {key: build_target(key, build_dir, selected_macros) for key in target_keys}


def list_build_outputs(build_results: dict[str, Path]) -> list[tuple[str, Path]]:
    """Return (target_key, path) for every output file that actually exists."""
    produced = []
    for target_key, bin_dir in build_results.items():
        for output_name in TARGETS[target_key]["outputs"]:
            candidate = bin_dir / output_name
            if candidate.exists():
                produced.append((target_key, candidate))
    return produced


def deployed_filename(target_key: str, source: Path) -> str:
    """Disambiguate a filename for deployment into a shared TFTP root.

    Every UEFI target produces a file literally named ipxe.efi -- fine
    inside their separate bin-<arch>-efi/ build directories, but if two
    or more of those get deployed into the same TFTP root they'd
    overwrite each other. Tag it with the target key in that case.
    """
    if source.name == "ipxe.efi":
        return f"ipxe-{target_key}.efi"
    return source.name
