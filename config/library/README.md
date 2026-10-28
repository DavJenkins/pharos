# Public Data Ark configuration

Start with `ark.yaml`. Collection definitions live in `collections/`, detailed
asset definitions in `catalogues/`, and generated checksums/order in `state/`.
The shared type registry is `../content-types.yaml`.

The web editor assembles and publishes changes with caretaker authorization.
For hand-edited files, compile and review first, then use the explicit local-root
publisher. Never infer desired selections from an empty or replacement drive.

See `../../docs/20-Administration/ModularConfiguration.md` in the repository or
http://dataark/docs/20-Administration/ModularConfiguration.html on the Ark.
