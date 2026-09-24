"""Interactive menu for configuring, building, and deploying iPXE boot images."""

from pathlib import Path

from . import dependencies, pxe, tftp


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


def resolve_tftp_root() -> Path | None:
    """Ensure the platform's TFTP root exists, letting the user retry with another path on failure."""
    candidate = tftp.default_tftp_root()
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


def offer_custom_iso(tftp_root: Path) -> None:
    if not prompt_yes_no("\nDo you have a custom .iso you'd like to add?", False):
        return

    raw_path = input("Path to the .iso file: ").strip()
    iso_path = Path(raw_path).expanduser()
    if not iso_path.is_file():
        print(f"  {iso_path} not found, skipping.")
        return

    folder_name = input("Folder name to place it under (e.g. mycustomrom): ").strip()
    if not folder_name:
        print("  No folder name given, skipping.")
        return

    destination = tftp.add_custom_iso(iso_path, tftp_root, folder_name)
    if destination.name != iso_path.name:
        print(f"  Note: {iso_path.name} already existed there; saved as {destination.name}")
    print(f"  Added {destination}")


def offer_linux_iso_download(tftp_root: Path) -> None:
    if not prompt_yes_no("\nDownload a Linux install ISO?", False):
        return

    catalog_keys = list(tftp.LINUX_ISO_CATALOG.keys())
    print("Available distros:")
    for index, key in enumerate(catalog_keys, start=1):
        print(f"  {index}. {tftp.LINUX_ISO_CATALOG[key]['label']}")

    raw = input(f"Select a distro [1-{len(catalog_keys)}], or blank to skip: ").strip()
    if not raw.isdigit() or not (0 < int(raw) <= len(catalog_keys)):
        return

    distro_key = catalog_keys[int(raw) - 1]
    if tftp.linux_iso_destination(distro_key, tftp_root).exists():
        print(f"  {tftp.LINUX_ISO_CATALOG[distro_key]['label']} already present, skipping download.")
    else:
        print(f"  Downloading {tftp.LINUX_ISO_CATALOG[distro_key]['label']} ...")
    destination = tftp.download_linux_iso(distro_key, tftp_root)
    print(f"  Added {destination}")


def run() -> None:
    """Run the interactive configure/build/deploy flow end to end."""
    print("BootWright - iPXE Boot Environment Builder")

    dependencies.ensure_dependencies_installed()

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
    build_results = pxe.build_targets(target_keys)
    produced_images = pxe.list_build_outputs(build_results)

    tftp_root = resolve_tftp_root()
    if tftp_root is None:
        print("No TFTP root available, leaving built images in place.")
        return
    print(f"\nUsing TFTP root: {tftp_root}")

    images_to_deploy = select_images_to_deploy(produced_images)
    deployed = tftp.deploy_images(images_to_deploy, tftp_root)
    for path in deployed:
        print(f"  Deployed {path}")

    offer_custom_iso(tftp_root)
    offer_linux_iso_download(tftp_root)


if __name__ == "__main__":
    run()
