# Current implementation notes

Reviewed October 28, 2026. These notes describe the working feature set; they are not a tagged-release guarantee. Use the **System** tab or `/assets/build-info.json` for the deployed revision, branch, source fingerprint and publication time.

- Public configuration is split into `ark.yaml`, collection definitions, catalogues and generated version/order snapshots. The folder-based editor supports syntax coloring, section navigation, search, validation, full-snapshot History and an unsaved-changes indicator. Reads require no caretaker password.
- Caretaker authorization uses an optional fixed 1–120 minute, tab-scoped cache. A red floating unlocked padlock displays remaining minutes and locks on tap. Credential changes require the fresh-authentication helper; there is no browser password-change form yet.
- System details use System, Library and Usage tabs. Manage Library is on Library; system administration actions are on System. Network and display controls use slider switches; Help and Developer API open directly.
- All 24 collection cards have distinct artwork. Installed national and Caribbean street maps, Gutenberg, Khan Academy, and offline Communicate tools are represented in the library. The live inventory, not an old count, determines availability.
- The banner supports Markdown, date/greeting variables, variable syntax coloring, appearance controls and optional broadcast to open clients. The community board supports nested replies, author removal links, caretaker editing and backup/restore.
- Home Assistant health, bug-out controls and collection/configuration events are configured. Phone notifications and physical-device actions require explicit household automations.
- File distribution includes HTTP, read-only SMB and anonymous read-only FTP. SSH/SFTP, rsync and the browser terminal use their own account authorization.

## Still incomplete

Public Send to the Ark suggestions and caretaker approval are not implemented. Specialized GIS datasets do not all have browser viewers; street-map search and routing are absent. Fresh/spare-media acceptance remains required for dependable recovery. Broad client/offline tests, household-source/encryption acceptance and UPS/shutdown policies retain their specific acceptance requirements. See [Acceptance tests](AcceptanceTests.md), [Recovery queue](RecoveryQueue.md) and [Home Assistant](HomeAssistant.md).
