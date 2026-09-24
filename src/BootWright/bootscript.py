"""Generate the iPXE boot menu (boot.ipxe) served from the TFTP root, and
the tiny static bootstrap script embedded into every built binary.

Distinct from menu.py, which is BootWright's own interactive CLI menu --
this module generates iPXE's own on-target boot menu script.
"""

from dataclasses import dataclass
from pathlib import Path

# Embedded into every built binary via `make ... EMBED=<this file>`.
# Static and identical for every build: it only references iPXE's own
# ${next-server} runtime variable (populated from DHCP), so it never
# needs to know the real TFTP root path at build time. That's what lets
# the real, editable menu (boot.ipxe) be regenerated later -- e.g. after
# adding a new ISO -- without ever rebuilding/recompiling iPXE again.
DEFAULT_EMBED_SCRIPT = (
    "#!ipxe\n"
    "dhcp || exit 1\n"
    "chain tftp://${next-server}/boot.ipxe ||\n"
    "chain http://${next-server}/boot.ipxe ||\n"
    "shell\n"
)


@dataclass(frozen=True)
class MenuEntry:
    """One item in the generated boot.ipxe menu."""

    label: str
    boot_commands: tuple[str, ...]  # iPXE commands run when this item is chosen


def local_disk_entry() -> MenuEntry:
    return MenuEntry("Boot from local disk", ("exit",))


def shell_entry() -> MenuEntry:
    return MenuEntry("iPXE shell", ("shell",))


def iso_entry(label: str, relative_path: str) -> MenuEntry:
    """A menu entry that SAN-boots an ISO already deployed under tftp_root/relative_path."""
    return MenuEntry(
        label,
        (f"sanboot --no-describe tftp://${{next-server}}/{relative_path} || goto MENU",),
    )


def render_boot_menu(
    entries: list[MenuEntry], background_url: str | None = None, timeout_ms: int = 15000
) -> str:
    """Render boot.ipxe text for the given menu entries.

    Uses iPXE's dynamic-UI commands (menu/item/choose/goto) and, for ISO
    entries, sanboot --no-describe -- verified against
    vendor/ipxe/src/hci/commands/dynui_cmd.c, console_cmd.c, and
    sanboot_cmd.c.
    """
    lines = ["#!ipxe"]
    if background_url:
        lines.append(f"console --picture {background_url} --keep || echo Could not load background image")

    if not entries:
        # Nothing to choose between -- just fall through to local boot.
        lines.append("exit")
        return "\n".join(lines) + "\n"

    lines.append(":MENU")
    lines.append("menu BootWright Boot Menu")
    names = [f"option{index}" for index in range(len(entries))]
    for name, entry in zip(names, entries):
        lines.append(f"item {name} {entry.label}")

    lines.append(f"choose --timeout {timeout_ms} --default {names[0]} selected || goto MENU")
    lines.append("goto ${selected}")

    for name, entry in zip(names, entries):
        lines.append(f":{name}")
        lines.extend(entry.boot_commands)

    return "\n".join(lines) + "\n"


def write_boot_menu(
    tftp_root: Path, entries: list[MenuEntry], background_url: str | None = None
) -> Path:
    """Write the rendered boot menu to tftp_root/boot.ipxe."""
    destination = tftp_root / "boot.ipxe"
    destination.write_text(render_boot_menu(entries, background_url))
    return destination
