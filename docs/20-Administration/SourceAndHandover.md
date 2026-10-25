# Source repository, backups and handover

## Find the source

The [GitHub repository](https://github.com/DavJenkins/pharos) is DavJenkins/pharos, also known as Project Pharos/Data Ark. The working checkout on the appliance is /opt/dataark. The local Samba development share is \\dataark\dataark; use smb://dataark/dataark from a compatible file manager. Those are references to the existing source share, not anonymous FTP paths.

The deployed development branch was feature/readme-foundation at the October 22 review. Determine the current branch and committed revision before acting:

```sh
cd /opt/dataark
git branch --show-current
git rev-parse HEAD
git status --short
git remote -v
```

Use the checkout's owning account, normally admin. Do not run routine Git commands as root or recursively change repository permissions to conceal an ownership problem. Review content diffs separately from mode-only differences introduced through the SMB share.

## What is authoritative

- Source behavior: tracked Python, browser code, installers and tests in the appliance checkout, compared with the deployed revision and installed helper copies.
- Current collection selection and site policy: live dataark.yaml. Some legitimate management changes may be uncommitted.
- Effective system configuration: installed files plus runtime inspection; an installer template alone does not prove it was applied.
- Running state and failures: API state, worker status, journals, common events and service journals.
- Rebuild identity and secrets: protected configuration snapshots and separately held credentials/keys.
- Knowledge content: the actual SSD, publisher provenance and checksums. Git is not an archive backup.

Keep these distinctions when a maintainer says a change is committed, deployed, activated or tested. They mean different things.

## Backup classes

### Repository and local changes

Push intended commits to GitHub, and preserve the current checkout's uncommitted/ignored operational files separately before replacing media. Do not blindly commit all changes: a credential, private capture or real content archive does not belong in public history. A source bundle or separate copy should preserve useful work if GitHub is unreachable.

### Private configuration

From /opt/dataark run:

```sh
sudo venv/bin/python tools/capture_config.py
```

The output is a timestamped root-only directory below /var/backups/dataark, containing configuration.tar.gz and inventory.json. Both are private. The capture records missing commands/files and errors; inspect its summary. A capture was made during the October 22 handover review with zero file-capture errors, but that is not a tested restore.

Copy a private snapshot to separately protected storage. Keeping the only copy on the Pi is not disk-failure recovery. The captured settings can contain network credentials, host keys and Samba account state. Restrict custody and do not put them on anonymous FTP, public shares, GitHub or public issue trackers.

### Content SSD

Copy the actual content, portable readers, orientation files, metadata and necessary household snapshots to independent storage according to the collection's policy. A list of URLs or checksums alone cannot reconstruct a publisher archive that later disappears. A captured /etc/fstab is not a copy of the disk it names.

Stop or quiesce mutations before taking a consistency-sensitive copy. The current exFAT layout is portable but has no documented snapshot mechanism. Do not unplug a live drive. Do not discard an old content file until replacement/backup needs have been reviewed.

### Credentials and integrations

Hand over the caretaker credential through an appropriate private channel, along with a way to reset it locally. Record who may administer the Pi, which SSH keys they control, Samba accounts, upstream/AP credentials and any source/encryption/HA tokens. The public handbook must describe their locations and roles without containing their values. SSH account private keys may live off the Ark and are not covered by its configuration capture.

## Transfer responsibility

- Have the successor connect to the hotspot and manually open the landing page.
- Have them find both local source and GitHub and identify the deployed revision/dirty state.
- Review installed collections, pending jobs, removed sources and free storage together.
- Demonstrate public reading/copying and a safe management action using disposable content or fixtures.
- Explain the difference between caretaker, Wi-Fi, Linux, SSH, Samba and household-source credentials.
- Locate the private backups without exposing them through the public interface.
- Review the configuration reference, outstanding acceptance results and incident history.
- Exercise a restore on spare media before relying on the successor's ability to recover the original appliance.

## Restore cautiously

A configuration tar is an inspection/reconstruction input, not a command to overwrite a running /etc tree. Review the new disk identifiers, account IDs, interface roles, network overlap, SSH host identity and package versions first. Restore private settings deliberately, install source-controlled helpers, validate candidate configs, then start services in dependency order. See [Configuration reference](Configuration.md) and [Bootstrap plan](../30-Developer/BootstrapPlan.md).

A successful spare-media rebuild should prove independent access to real articles/images, files, maps, docs, public transfer methods and protected management; it should also demonstrate recovery from an interrupted transaction. Update the acceptance record with the actual result and date.

## Community messages

The community board is live user data, separate from the content catalogue and source recovery kit. Its private SQLite database is `/var/lib/dataark/community/board.sqlite3`; daily private snapshots are in `/var/backups/dataark-community`. They are on the same system card. Use the board’s caretaker backup download to keep a copy on another device. See [Community board](CommunityBoard.md) for limits, retention, and restore instructions. Never commit messages or publish the private database in the shared library.
