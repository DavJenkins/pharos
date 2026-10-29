# Developing and maintaining the Ark on the Ark

Inventory checked October 23, 2026. Source is /opt/dataark; the additional remote copy is [DavJenkins/pharos](https://github.com/DavJenkins/pharos). Use the admin Linux account for development, not root. This is the live working checkout; make Git checkpoints and review changes before deploying.

New terminal sessions provide a brief orientation. Run `ark-help` anywhere, or choose `ark-help status`, `library`, `develop`, `recovery` or `basics`. See [shell welcome and administration guide](../20-Administration/ShellWelcome.md).

## Available tools

- VS Code 1.143.1 ARM64: desktop application menu or `code /opt/dataark`.
- IntelliJ IDEA 2026.2.3 ARM64: desktop application menu or `idea`. Installed under /opt/jetbrains with /opt/idea as the stable link. First launch may require license/setup choices; these are left to the user. Free core features and optional paid features have different licensing.
- GHex 46.2: graphical binary/hex file editor, application menu or `ghex`. Work on a copy before editing an archive or system binary.
- OpenJDK 21: `java`, `javac`, and standard JDK diagnostics. IntelliJ also has a separate bundled runtime.
- Python 3.13, venv/pip, the existing /opt/dataark/venv environment and pinned requirements.txt; GCC, make and development headers.
- Git and local history; SSH/SFTP, rsync, curl, archive utilities, Docker, systemd and Apache administration tools.
- Chromium for manual local browser verification. No Node/npm, browser automation framework, or JavaScript lint tool was found in this audit; the current Ark serves ordinary JavaScript without a Node build step.
- Codex CLI: official ARM64 standalone release, launched with `codex` from the source directory. The user must sign in separately. Do not copy another machine's authentication files or put credentials in the repository. Normal hosted-model use requires internet and an eligible account; installation does not provide an offline AI model.

## Local workflow

Run the Python tests from a terminal on the Ark:

```sh
cd /opt/dataark
venv/bin/python -m unittest discover -s tests
```

 They use Python unittest rather than pytest. Use the same virtual environment for application dependencies. Docs are rendered by tools/publish_docs.py without a separate Markdown toolchain. The existing deploy/deploy-web.sh validates/renders the dashboard and publishes the static site and documentation. Deployment and system service changes need the existing administrative privileges; editing code alone does not restart the API.

Use Chromium to check the actual landing page, library manager, maps, pop-ups and documentation. A passing unit suite is not proof that every reader, network route or recovery scenario works. Consult the acceptance tests and the source/handover guide before changing running services.

## Memory and recovery limits

This Ark is a Raspberry Pi 4 Model B with 2 GB soldered RAM and about 2 GB swap. Its RAM is not an ordinary replaceable module. IntelliJ is below the vendor's published 8 GB total RAM requirement; installation is not a promise of usable performance. Keep heavy IDEs closed when not needed and avoid running both together. IDE graphical first-run and project indexing have not been acceptance-tested. No new resource quotas have been introduced.

Vendor archives, checksums and provenance for standalone tools are retained in /var/cache/dataark/ide. APT-installed packages come from the configured signed Debian/Raspberry Pi repositories. This cache is not a complete offline package mirror. Existing Python packages and Docker images support the current installation, but all wheels, OS packages, plugin dependencies and build artifacts needed for a fresh offline rebuild have not been collected and tested. Java/Maven/Gradle projects may need further dependencies.

The current installation can edit, test, document and deploy its source locally. A verified one-script clean-image bootstrap and a completely offline rebuild remain unfinished goals. See [bootstrap plan](BootstrapPlan.md).
