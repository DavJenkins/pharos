# Shell welcome and administration guide

Every new interactive Bash terminal gets a short Data Ark orientation: the live source checkout, content drive, configuration file, GitHub repository, installed tools and local documentation. It is intended to give someone a starting point without turning each login into a tutorial.

`ark-help` is available from any directory. It prints guidance; it does not run maintenance commands, change services, access the network or inspect private configuration.

| Command | Guidance |
| --- | --- |
| `ark-help` | Places to know, available tools and useful administration tasks |
| `ark-help status` | Read-only health, logs, disk, memory and network checks |
| `ark-help library` | Shared library management, editions, sources and privacy |
| `ark-help develop` | Repository layout, editors, Python environment, tests, Git and deployment |
| `ark-help recovery` | Configuration backups, network access and recovery limits |
| `ark-help basics` | Optional shell navigation and command help |

The welcome identifies this as the live appliance, recommends the admin account for routine source work and explains when sudo is appropriate. Graphical tools are identified as requiring a desktop. Codex requires the user's own sign-in and internet; an installed CLI is not an offline model. IntelliJ's memory limitations remain documented.

## Implementation and reproduction

Source is `tools/ark_help.py`; installer is `deploy/install_shell_welcome.py`, both in `/opt/dataark` and the [GitHub repository](https://github.com/DavJenkins/pharos).

```sh
sudo /usr/bin/python3 /opt/dataark/deploy/install_shell_welcome.py
```

The installer copies the helper to `/usr/local/bin/ark-help`, installs `/etc/profile.d/dataark-welcome.sh`, and adds one marked source block to `/etc/bash.bashrc`. The first original bashrc is backed up to `/etc/bash.bashrc.before-dataark-welcome`. Reinstallation replaces the marked block and does not duplicate it. Existing individual bashrc files, authentication, permissions and service access remain unchanged. New shells see the welcome; an already open terminal can run `ark-help` immediately.

The hook requires an interactive shell and terminal output. An unexported per-shell guard prevents duplicate printing when a login shell reads both system bashrc and profile.d. No banner is added to non-interactive commands, SCP, SFTP or scripts. The pre-existing Wi-Fi startup scripts may still emit their own notices; this change does not alter them. Interactive login and non-login Bash, a non-interactive login shell, and repeat installation were checked on the Ark. Different shell startup paths and a fresh web-terminal login have not been separately acceptance-tested.

The configuration capture utility now includes the system bashrc, profile hook and installed helper. To disable the welcome, remove the marked block from `/etc/bash.bashrc` and remove `/etc/profile.d/dataark-welcome.sh`; `ark-help` can remain installed. To change wording, edit the repository source and rerun the installer. Ordinary web deployment alone does not install shell changes.
