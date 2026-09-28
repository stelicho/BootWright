"""Interactive menu for configuring, building, and deploying iPXE boot images."""

from pathlib import Path

from . import bootscript, dependencies, pxe, services, tftp, winpe


def prompt_yes_no(question: str, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{question} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def select_features() -> set[str]:
    """Walk every macro in pxe.FEATURE_OPTIONS, returning the ones the user enabled."""
    selected: set[str] = set()
    print("\nSelect iPXE features to enable:")
    for category, options in pxe.FEATURE_OPTIONS.items():
        print(f"\n-- {category} --")
        for macro, (description, default_enabled) in options.items():
            if prompt_yes_no(f"  {description} ({macro})", default_enabled):
                selected.add(macro)
    return selected


def select_targets() -> list[str]:
    """Prompt for a comma-separated list of pxe.TARGETS to build."""
    keys = list(pxe.TARGETS.keys())
    print("\nAvailable build targets:")
    for index, key in enumerate(keys, start=1):
        print(f"  {index}. {pxe.TARGETS[key]['label']}")

    raw = input("Select targets to build (comma-separated numbers): ").strip()
    chosen = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 0 < int(part) <= len(keys):
            chosen.append(keys[int(part) - 1])
    return chosen


def select_images_to_deploy(produced: list[tuple[str, Path]]) -> list[tuple[Path, str]]:
    """Prompt for which of the just-built images to move into the TFTP root.

    Returns (source_path, destination_filename) pairs. Destination
    filenames are disambiguated per target (see pxe.deployed_filename)
    since every UEFI build produces a file literally named ipxe.efi.
    """
    if not produced:
        return []

    entries = [
        (path, pxe.deployed_filename(target_key, path), pxe.TARGETS[target_key]["label"])
        for target_key, path in produced
    ]

    print("\nBuilt images available to add to the TFTP root:")
    for index, (_, deploy_name, label) in enumerate(entries, start=1):
        print(f"  {index}. {deploy_name}  ({label})")

    raw = input("Select images to add (comma-separated numbers, or 'all'): ").strip().lower()
    if raw == "all":
        return [(path, deploy_name) for path, deploy_name, _ in entries]

    chosen = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 0 < int(part) <= len(entries):
            path, deploy_name, _ = entries[int(part) - 1]
            chosen.append((path, deploy_name))
    return chosen


def resolve_tftp_root(initial_candidate: Path | None = None) -> Path | None:
    """Ensure the platform's TFTP root exists, letting the user retry with another path on failure."""
    candidate = initial_candidate or tftp.default_tftp_root()
    while True:
        try:
            return tftp.ensure_tftp_root(candidate)
        except PermissionError:
            print(
                f"\nCouldn't create/access {candidate} -- re-run with administrator/root "
                "privileges, or enter a different path."
            )
            raw = input("TFTP root path (blank to cancel): ").strip()
            if not raw:
                return None
            candidate = Path(raw).expanduser()


def offer_custom_iso(tftp_root: Path) -> bootscript.MenuEntry | None:
    if not prompt_yes_no("\nDo you have a custom .iso you'd like to add?", False):
        return None

    raw_path = input("Path to the .iso file: ").strip()
    iso_path = Path(raw_path).expanduser()
    if not iso_path.is_file():
        print(f"  {iso_path} not found, skipping.")
        return None

    folder_name = input("Folder name to place it under (e.g. mycustomrom): ").strip()
    if not folder_name:
        print("  No folder name given, skipping.")
        return None

    destination = tftp.add_custom_iso(iso_path, tftp_root, folder_name)
    if destination.name != iso_path.name:
        print(f"  Note: {iso_path.name} already existed there; saved as {destination.name}")
    print(f"  Added {destination}")

    label = input("Menu label for this entry (blank to use the filename): ").strip()
    relative_path = destination.relative_to(tftp_root).as_posix()
    return bootscript.iso_entry(label or destination.stem, relative_path)


def offer_linux_iso_download(tftp_root: Path) -> list[bootscript.MenuEntry]:
    """Offer the catalogued Linux installer ISOs, letting the user download any number of them."""
    if not prompt_yes_no("\nDownload a Linux install ISO?", False):
        return []

    catalog_keys = list(tftp.LINUX_ISO_CATALOG.keys())
    print("Available distros:")
    for index, key in enumerate(catalog_keys, start=1):
        print(f"  {index}. {tftp.LINUX_ISO_CATALOG[key]['label']}")

    raw = input(
        f"Select distros to download (comma-separated numbers, or 'all') [1-{len(catalog_keys)}]: "
    ).strip().lower()
    if raw == "all":
        chosen_keys = catalog_keys
    else:
        chosen_keys = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and 0 < int(part) <= len(catalog_keys):
                chosen_keys.append(catalog_keys[int(part) - 1])

    entries = []
    for distro_key in chosen_keys:
        entry_info = tftp.LINUX_ISO_CATALOG[distro_key]
        if tftp.linux_iso_destination(distro_key, tftp_root).exists():
            print(f"  {entry_info['label']} already present, skipping download.")
        else:
            print(f"  Downloading {entry_info['label']} ...")
        destination = tftp.download_linux_iso(distro_key, tftp_root)
        print(f"  Added {destination}")

        relative_path = destination.relative_to(tftp_root).as_posix()
        entries.append(bootscript.iso_entry(entry_info["label"], relative_path))
    return entries


def offer_background_image(tftp_root: Path, selected_macros: set[str]) -> str | None:
    """Ask for a boot-menu background image; returns a URI/filename for bootscript, or None."""
    if not prompt_yes_no("\nWould you like to set a background image for the boot menu?", False):
        return None

    required = {"CONSOLE_FRAMEBUFFER", "IMAGE_PNG"}
    missing = required - selected_macros
    if missing:
        print(
            f"  Note: {', '.join(sorted(missing))} weren't enabled for this build -- the "
            "picture won't render until you rebuild with them on. Writing the menu "
            "with it anyway so it's ready for next time."
        )

    raw = input("Local image path or URL (PNG recommended): ").strip()
    if not raw:
        return None

    if raw.startswith(("http://", "https://", "tftp://")):
        return raw

    image_path = Path(raw).expanduser()
    if not image_path.is_file():
        print(f"  {image_path} not found, skipping background image.")
        return None

    destination = tftp.add_background_image(image_path, tftp_root)
    print(f"  Added {destination}")
    return destination.name


def offer_winpe_guidance(tftp_root: Path, http_port: int | None) -> None:
    if not prompt_yes_no(
        "\nWould you like guidance on setting up a WinPE network boot and a Windows "
        "install fileshare?",
        False,
    ):
        return
    winpe.print_winpe_guidance(tftp_root, http_port)


def offer_tftp_service(tftp_root: Path) -> None:
    if not prompt_yes_no("\nEnable/start a TFTP server for this TFTP root?", False):
        return
    services.enable_tftp_service(tftp_root)


def offer_http_service(tftp_root: Path) -> int | None:
    if not prompt_yes_no("\nStart an HTTP server to serve the same TFTP root?", False):
        return None

    port_raw = input("Port to serve on [8080]: ").strip()
    port = int(port_raw) if port_raw.isdigit() else 8080
    process = services.start_http_server(tftp_root, port)
    print(
        f"  Serving {tftp_root} on port {port} in the background (pid {process.pid}). "
        f"It keeps running after BootWright exits; stop it later with: kill {process.pid}"
    )
    return port


def run(
    skip_dependencies: bool = False,
    tftp_root_override: Path | None = None,
    assume_yes: bool = False,
) -> None:
    """Run the interactive configure/build/deploy flow end to end."""
    print("BootWright - iPXE Boot Environment Builder")

    if not skip_dependencies:
        dependencies.ensure_dependencies_installed(assume_yes=assume_yes)

    print(f"\nSyncing iPXE source into {pxe.IPXE_SRC_DIR} ...")
    pxe.clone_or_update_ipxe()

    selected_macros = select_features()
    config_path = pxe.write_local_config(selected_macros)
    print(f"\nWrote config overrides to {config_path}")

    target_keys = select_targets()
    if not target_keys:
        print("No targets selected, exiting.")
        return

    print(f"\nBuilding: {', '.join(pxe.TARGETS[key]['label'] for key in target_keys)}")
    build_results = pxe.build_targets(target_keys, selected_macros=selected_macros)
    produced_images = pxe.list_build_outputs(build_results)

    tftp_root = resolve_tftp_root(tftp_root_override)
    if tftp_root is None:
        print("No TFTP root available, leaving built images in place.")
        return
    print(f"\nUsing TFTP root: {tftp_root}")

    images_to_deploy = select_images_to_deploy(produced_images)
    deployed = tftp.deploy_images(images_to_deploy, tftp_root)
    for path in deployed:
        print(f"  Deployed {path}")

    menu_entries = [bootscript.local_disk_entry()]
    if "SHELL_CMD" in selected_macros:
        menu_entries.append(bootscript.shell_entry())

    custom_entry = offer_custom_iso(tftp_root)
    if custom_entry is not None:
        menu_entries.append(custom_entry)

    menu_entries.extend(offer_linux_iso_download(tftp_root))

    background_url = offer_background_image(tftp_root, selected_macros)

    menu_path = bootscript.write_boot_menu(tftp_root, menu_entries, background_url)
    print(f"\nWrote boot menu to {menu_path}")

    offer_tftp_service(tftp_root)
    http_port = offer_http_service(tftp_root)
    offer_winpe_guidance(tftp_root, http_port)

    services.print_dhcp_advice(tftp_root, [path.name for path in deployed], http_port)


if __name__ == "__main__":
    run()
