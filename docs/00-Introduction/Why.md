# Why Data Ark?

## Preserve access before it is needed

An internet outage should not make an already collected manual, reference work, or repair guide inaccessible. Data Ark keeps useful copies on local storage and serves them over a local network. Its hotspot remains useful when the upstream network is unavailable.

## Offline first is a working requirement

The main library should emphasize installed content. Online reference links must identify themselves as requiring internet access. A queued download is not an installed collection: the updater checks it, activates the reader, and publishes it before declaring it ready.

The library drive also contains portable orientation files. With the Pi shut down cleanly, the SSD can be attached to another computer. A compatible reader may still be needed for ZIM archives or specialized data formats.

## Equal access to the public library

Everyone can read and copy public content without a caretaker account. A shared caretaker password protects operations that change the common library. It is a stewardship role, not a separate tier of knowledge access. Public requests for new collections and storage-sensitive approval rules are agreed design goals, not implemented features yet.

## Separate public knowledge from private material

The Ark also supports configured household backups. Credentials and staging areas are not public library content. A caretaker must review what is published before adding personal files or exposing a backup snapshot to other users. Configuration captures are private recovery material and do not belong in the public documentation or repository.

## Be honest about resilience

Offline access still needs power, working storage, a working reader, and a reachable local network. Captive-portal pop-ups vary by client. A running server is not proof that every article, image, map, or copied reader works on every device. Checksums detect corruption; they do not establish that information is correct, current, or suitable for a particular situation.

## Favor maintainable parts

The implementation uses Apache for web access, FastAPI for local APIs, Kiwix for ZIM reading, Samba and FTP for file distribution, and systemd for workers. The central manifest identifies collections and their sources. Source code, tests, installers, and documentation should be enough for another maintainer to understand the system; a complete disaster-recovery restore still requires independent testing.
