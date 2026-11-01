# Clean demo-library bootstrap acceptance

**1 November 2026 — passed on fresh Debian 13 ARM64 QEMU.**

The actual installer CLI completed all ten phases in one invocation on a clean system disk with no external content disk. A 4 GiB demo library was allocated on the system disk, populated and verified. The appliance remained functional after reboot, without rerunning setup.

## Frozen inputs

- Source: `22bc0fdce5ef469355ae62340873a1c4a1b137e3` on `feature/readme-foundation`.
- Source archive SHA-256: `a4df937f864d79d8a493f7b55de22316a8b2570915caaff42d091ae073a19d45`.
- Platform: `debian13-arm64-lan`; demo allocation: 4 GiB.
- The Debian backing image matched its retained official SHA-512 manifest. A new OS overlay and guest identity were created. No installed Ark files, Python environment, service state or content disk were inherited.
- The test used the normal preview, plan acceptance, INSTALL confirmation and private password prompts through a real terminal. No installer guards or phases were bypassed. Installation took 987 seconds.
- Kit checksums were unchanged before and after the run. There were no source patches, phase retries or journal corrections during this invocation. This candidate has not replaced the published bootstrap download.

## Verified behavior

- All ten phases completed: packages, source, storage, Python, platform settings, base services, content access, network, content and finish.
- Dashboard, API, Help, Manage Library, Community, Recovery and API documentation responded successfully.
- The demo filesystem mounted from its owned, fixed-size image. Repeating setup reused the same image without reformatting it.
- The 333,429,922-byte Wikipedia 100-article sample matched its pinned SHA-256. Both bundled catalogue PDFs matched their source files and downloaded through HTTP.
- A real article and its image opened in Kiwix. Dashboard, status, a PDF, that article and its image remained accessible with the guest's external route removed. The original route was restored afterward.
- All 29 configured repositories remained represented, and the full desired source profile stayed byte-for-byte unchanged.
- Correct caretaker authentication succeeded; unauthenticated unlock was rejected.
- All 63 focused demo, stock-setup, platform, reader, library, manifest and shell-archive regression tests passed.
- After reboot, the demo volume, services, sample hashes, article/image reads and caretaker authentication passed again. Health reported OK with no issues.

## Failure found and corrected

An earlier, separately retained guest exposed Windows line-ending conversion in the candidate archive: the reader's Linux shell script contained CRLF and the container could not start. Shell files are now explicitly LF in Git attributes; drive-kit archives disable checkout conversion and generated launchers use LF. A regression test builds an archive with Windows conversion enabled and checks the shell bytes.

The successful run used a second fresh disk after this fix. The failed guest was not patched or resumed and is not counted as an uninterrupted success.

## Evidence and scope

The [machine-readable result](CleanDemoBootstrap.json) records the checked source and outcomes. Reproduction fixtures are `deploy/emulator/run_demo_bootstrap_test.py` and `deploy/emulator/verify_demo_bootstrap_test.py`. Guest logs, previews and before/after-reboot evidence are under `/var/lib/dataark/acceptance/clean-demo-20261101/`; copies are retained outside the guest. Credentials are excluded from the published result.

This establishes a clean, complete generic ARM64 demo installation and reboot. The separate [physical no-content-mount boot](RecoveryValidation.md) passed on the reference Pi. A second uninterrupted installation on fresh physical Raspberry Pi OS still requires another card preparation and swap; the virtual test does not establish radio or physical-media behavior. Keep the recovery branch unmerged until the complete physical acceptance matrix passes.
