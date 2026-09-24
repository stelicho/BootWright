"""Enable/start the TFTP and HTTP services needed to actually serve the
TFTP root over the network, and print DHCP configuration guidance.

Every command that actually modifies system state here is printed before
it runs, mirroring dependencies.install_missing() -- these are real,
persistent system changes (enabling launchd/systemd services, editing
/etc/default/tftpd-hpa), so callers should confirm with the user before
invoking them, not run them unconditionally.
"""

import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from . import dependencies

MACOS_TFTP_PLIST = Path("/System/Library/LaunchDaemons/tftp.plist")
# Hardcoded inside that plist's ProgramArguments; since /System is
# SIP-sealed on modern macOS, the plist can be enabled/loaded but never
# edited, so the built-in daemon can only ever serve this exact path.
MACOS_TFTP_ROOT = Path("/private/tftpboot")


def enable_macos_tftpd(tftp_root: Path) -> bool:
    """Enable/start macOS's built-in tftpd. Only works for the default TFTP root."""
    if tftp_root.resolve() != MACOS_TFTP_ROOT:
        print(
            f"  macOS's built-in tftpd only serves {MACOS_TFTP_ROOT}; "
            f"your TFTP root is {tftp_root}. Skipping."
        )
        return False
    if not MACOS_TFTP_PLIST.exists():
        print("  Built-in tftpd not found on this macOS version. Skipping.")
        return False

    commands = [
        ["sudo", "launchctl", "enable", "system/com.apple.tftpd"],
        ["sudo", "launchctl", "bootstrap", "system", str(MACOS_TFTP_PLIST)],
        ["sudo", "launchctl", "kickstart", "-kp", "system/com.apple.tftpd"],
    ]
    for command in commands:
        print(f"  {' '.join(command)}")
        # bootstrap fails harmlessly if the service is already loaded
        subprocess.run(command, check=False)
    return True


def enable_linux_tftpd(tftp_root: Path) -> bool:
    """Install (if needed) and enable tftpd-hpa, pointed at tftp_root.

    v1 scope is Debian/Ubuntu (tftpd-hpa via apt) only -- other distros
    get manual guidance instead of an attempted automated setup.
    """
    if "apt" not in dependencies.detect_package_managers():
        print("  Automatic TFTP service setup is currently only implemented for Debian/Ubuntu (tftpd-hpa).")
        print(f"  Install and configure a TFTP daemon for your distro manually, pointed at: {tftp_root}")
        return False

    if shutil.which("in.tftpd") is None:
        command = dependencies.install_command("apt", "tftpd-hpa")
        print(f"  {' '.join(command)}")
        subprocess.run(command, check=True)

    config_text = (
        'TFTP_USERNAME="tftp"\n'
        f'TFTP_DIRECTORY="{tftp_root}"\n'
        'TFTP_ADDRESS=":69"\n'
        'TFTP_OPTIONS="--secure"\n'
    )
    write_command = ["sudo", "tee", "/etc/default/tftpd-hpa"]
    print(f"  {' '.join(write_command)}  (TFTP_DIRECTORY={tftp_root})")
    subprocess.run(write_command, input=config_text, text=True, check=True, stdout=subprocess.DEVNULL)

    restart_command = ["sudo", "systemctl", "enable", "--now", "tftpd-hpa"]
    print(f"  {' '.join(restart_command)}")
    subprocess.run(restart_command, check=True)
    return True


def enable_tftp_service(tftp_root: Path) -> bool:
    """Enable a persistent TFTP service pointed at tftp_root, if we know how on this platform."""
    system = platform.system()
    if system == "Darwin":
        return enable_macos_tftpd(tftp_root)
    if system == "Linux":
        return enable_linux_tftpd(tftp_root)

    print(f"  Automatic TFTP service setup isn't implemented for {system} yet.")
    print(f"  Install and configure a TFTP daemon manually, pointed at: {tftp_root}")
    return False


def start_http_server(tftp_root: Path, port: int = 8080) -> subprocess.Popen:
    """Start a background HTTP server serving tftp_root for the rest of this session.

    Prefers darkhttpd if it's on PATH, otherwise falls back to Python's
    own http.server module, which needs no extra install and works
    identically on every platform Python runs on. Session-only: no
    service unit is created, so this doesn't survive a reboot.
    """
    if shutil.which("darkhttpd"):
        command = ["darkhttpd", str(tftp_root), "--port", str(port)]
    else:
        command = [sys.executable, "-m", "http.server", str(port), "--directory", str(tftp_root)]
    return subprocess.Popen(command, start_new_session=True)


def local_ip() -> str:
    """Best-effort guess at this machine's LAN-facing IP, for the DHCP advisory.

    UDP connect() just picks a route without sending any packets, so
    this reads back whichever local address the OS would use, without
    depending on internet access actually working.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]


def print_dhcp_advice(tftp_root: Path, deployed_filenames: list[str], http_port: int | None = None) -> None:
    """Print guidance for configuring an existing DHCP server to chainload these images.

    BootWright can't safely modify a DHCP server it doesn't control, so
    this only prints what needs to be configured, in terms general
    enough to apply to dnsmasq, ISC dhcpd, router-based DHCP, pfSense,
    etc alike.
    """
    ip = local_ip()
    print("\n--- DHCP configuration needed ---")
    print(f"TFTP root: {tftp_root}")
    print(f"next-server (TFTP server IP): {ip}")
    if http_port is not None:
        print(f"HTTP fallback: http://{ip}:{http_port}/")

    print("\nHand out one of these as the PXE boot filename, matching the client's")
    print("architecture (DHCP option 93 / vendor-class, per RFC 4578):")
    for name in deployed_filenames:
        print(f"  - {name}")

    print(
        "\nMany DHCP servers (dnsmasq, ISC dhcpd) can detect that a client is "
        "already running iPXE -- it identifies itself distinctly on its second "
        "request -- and, only at that point, hand out 'boot.ipxe' instead of the "
        "binary again. That lets the same config serve plain PXE ROMs on the "
        "first request and the generated menu on the second. Since BootWright "
        "doesn't know which DHCP server you're running, you'll need to wire "
        "this up yourself -- consult your DHCP server's iPXE-chainloading docs."
    )
    print(f"\nEither way, {tftp_root / 'boot.ipxe'} is already there and ready once")
    print("the first-stage binary loads it.")
