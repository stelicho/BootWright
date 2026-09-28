"""Print guidance for network-booting Windows PE and installing Windows over
a fileshare, per https://ipxe.org/howto/winpe.

BootWright doesn't automate any of this: generating the actual WinPE image
requires Microsoft's Windows ADK (copype, DISM, ImageX), which only runs on
Windows, and setting up a persistent fileshare is a bigger, more permanent
system change than anything else BootWright touches automatically. So this
module only prints the steps -- mirroring services.print_dhcp_advice, which
takes the same stance on DHCP server configuration.
"""

import platform
from pathlib import Path


def _fileshare_guidance() -> list[str]:
    """Platform-tailored guidance for sharing the Windows installation media.

    Empty strings are blank lines, kept blank (not indented) by the caller.
    """
    system = platform.system()
    if system == "Windows":
        return [
            "On this Windows machine, share the folder containing your Windows",
            "installation media (the extracted contents of the Windows ISO) so WinPE",
            "can reach it over the network, e.g. in PowerShell (as Administrator):",
            "",
            "  New-SmbShare -Name installers -Path C:\\installers -FullAccess Everyone",
            "",
            "Copy the Windows installer files under that folder (e.g. C:\\installers\\win11\\)",
            "so setup.exe ends up at \\\\<this-machine>\\installers\\win11\\setup.exe.",
        ]
    if system == "Darwin":
        return [
            "On this Mac, share the folder containing your Windows installation media",
            "over SMB via System Settings -> General -> Sharing -> File Sharing: add the",
            "folder and enable 'Share files and folders using SMB'. From the command",
            "line instead: sharing -a /path/to/installers -s 001 (SMB only).",
            "",
            "Copy the Windows installer files under that folder (e.g. installers/win11/)",
            "so setup.exe ends up reachable as \\\\<this-mac>\\installers\\win11\\setup.exe.",
        ]
    return [
        "On this machine, install and configure Samba to share the folder containing",
        "your Windows installation media, e.g. in /etc/samba/smb.conf:",
        "",
        "  [installers]",
        "    path = /srv/installers",
        "    read only = yes",
        "    guest ok = yes",
        "",
        "Then: sudo systemctl restart smbd",
        "",
        "Copy the Windows installer files under that folder (e.g. /srv/installers/win11/)",
        "so setup.exe ends up reachable as \\\\<this-machine>\\installers\\win11\\setup.exe.",
    ]


def print_winpe_guidance(tftp_root: Path, http_port: int | None) -> None:
    """Print the full WinPE network-boot + Windows-install-over-fileshare walkthrough."""
    web_root_note = (
        f"BootWright's own HTTP server, already serving {tftp_root} on port {http_port}"
        if http_port is not None
        else f"a web server (e.g. BootWright's own HTTP option, or Apache/IIS) serving {tftp_root}"
    )

    print("\n--- WinPE network boot + Windows install setup (manual steps) ---")
    print(
        "BootWright can't build the WinPE image itself -- that needs Microsoft's Windows\n"
        "ADK, which only runs on Windows. The full walkthrough is at "
        "https://ipxe.org/howto/winpe;\nsummary below."
    )

    print("\n1. On a Windows machine, install the Windows ADK (or AIK for older Windows),")
    print("   then generate WinPE images for each architecture you need:")
    print("     mkdir C:\\temp\\winpe")
    print("     copype x86 C:\\temp\\winpe\\x86")
    print("     copype amd64 C:\\temp\\winpe\\amd64")

    print("\n2. (Optional) Inject network drivers Windows PE doesn't already include,")
    print("   using ImageX and DISM (also part of the ADK/AIK):")
    print("     imagex /mountrw C:\\temp\\winpe\\amd64\\media\\sources\\boot.wim 1 "
          "C:\\temp\\winpe\\amd64\\mount")
    print("     dism /image:C:\\temp\\winpe\\amd64\\mount /add-driver "
          "/driver:C:\\temp\\winpe\\drivers /recurse")
    print("     imagex /unmount /commit C:\\temp\\winpe\\amd64\\mount")

    print("\n3. Copy each C:\\temp\\winpe\\<arch>\\ tree to a web-accessible directory --")
    print(f"   {web_root_note}. Also download wimboot into that same")
    print("   directory: https://github.com/ipxe/wimboot/releases")

    print("\n4. Write install.bat there, pointing at your fileshare (step 6):")
    print("     wpeinit")
    print("     net use \\\\myserver\\installers")
    print("     \\\\myserver\\installers\\win11\\setup.exe")
    print("   and winpeshl.ini alongside it, to auto-run install.bat on boot:")
    print("     [LaunchApps]")
    print('     "install.bat"')

    print("\n5. Add a boot.ipxe menu entry (or run this from the iPXE shell) that loads")
    print("   WinPE via wimboot, picking the right architecture at boot time:")
    print("     cpuid --ext 29 && set arch amd64 || set arch x86")
    print("     kernel wimboot")
    print("     initrd install.bat                     install.bat")
    print("     initrd winpeshl.ini                    winpeshl.ini")
    print("     initrd ${arch}/media/Boot/BCD          BCD")
    print("     initrd ${arch}/media/Boot/boot.sdi     boot.sdi")
    print("     initrd ${arch}/media/sources/boot.wim  boot.wim")
    print("     boot")

    print("\n6. Set up the fileshare install.bat connects to, holding your Windows")
    print("   installation media (the extracted contents of a Windows ISO):")
    for line in _fileshare_guidance():
        print(f"   {line}" if line else "")

    print(
        "\nOnce WinPE boots and connects, setup.exe installs a full Windows onto the\n"
        "local disk (or an iSCSI target, if that's what you sanboot'd into instead)."
    )
