"""Console entry point (`bootwright`) for the interactive BootWright flow."""

import argparse
from pathlib import Path

from . import menu


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bootwright",
        description="Configure, build, and deploy a PXE boot environment on top of iPXE.",
    )
    parser.add_argument(
        "--no-depends",
        action="store_true",
        help="Skip the build-dependency check/install step entirely.",
    )
    parser.add_argument(
        "--tftp-root",
        type=Path,
        default=None,
        help="Use this TFTP root instead of the platform default.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Assume yes for dependency install prompts.",
    )
    args = parser.parse_args()

    menu.run(
        skip_dependencies=args.no_depends,
        tftp_root_override=args.tftp_root,
        assume_yes=args.yes,
    )


if __name__ == "__main__":
    main()
