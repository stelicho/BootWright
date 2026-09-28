# Security Policy

Thank you for helping keep BootWright and its users safe.

## Supported versions

BootWright is pre-1.0 and under active development. Only the latest commit
on `main` is supported -- please make sure a reported issue still
reproduces there before reporting it.

## Scope

This policy covers BootWright's own code: the dependency
checker/installer, iPXE build automation, TFTP/HTTP service setup, the
Linux ISO downloader, and the WinPE/Windows-install guidance. Of particular
interest are anything that could turn BootWright's use of `sudo`/elevated
privileges, its package-manager or service-management commands
(`dependencies.py`, `services.py`), or its network downloads
(`tftp.download_linux_iso`) into something an attacker controls -- for
example, command or argument injection, path traversal when writing into
the TFTP root, or an insecure download (e.g. accepting content over an
unauthenticated channel where HTTPS was expected).

The vendored iPXE source under `src/BootWright/vendor/ipxe/` is cloned
from the upstream [iPXE project](https://github.com/ipxe/ipxe) at build
time and is out of scope here -- please report vulnerabilities in iPXE
itself upstream, per [iPXE's own security policy](https://github.com/ipxe/ipxe/security/policy).

## Reporting a vulnerability

Please report suspected vulnerabilities privately using
[GitHub's private vulnerability reporting](https://github.com/stelicho/BootWright/security/advisories/new)
for this repository (under the "Security" tab -> "Report a vulnerability").

Please don't use public GitHub issues or pull requests to report suspected
vulnerabilities.

A good report includes:

- A short description of the issue and its potential impact
- The affected file(s)/function(s), or a commit hash if relevant
- Steps to reproduce, or a minimal example -- a working exploit isn't
  required, but enough detail to confirm the issue is

## What to expect

This is a small open-source project maintained on a best-effort basis --
there's no bug bounty, but every report will get a response, and
confirmed vulnerabilities will get a fix and a credit (in the fixing
commit and/or release notes) unless you ask to remain anonymous.
