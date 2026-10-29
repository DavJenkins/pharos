# Landing-page collections

The landing page groups installed content by purpose. `config/library/ark.yaml` contains the public `dashboard` presentation section, compiled into `dataark.yaml`; the portable `config/content/public-manifest.yaml` includes it for recovery. Underlying collection IDs, installed files, update recipes and ownership remain unchanged.

Custom cards use stable repository anchors, repository and asset IDs, labeled local link groups, and existing artwork. Explicitly assigned assets appear on their chosen card rather than twice. Individual-file lists can be collapsed. Maps combine street maps and clearly scoped Massachusetts reference layers. Learning is separate from activities; wilderness skills from energy; repairs and vehicle manuals share a card with labeled subsections; radio combines emergency communications, exam practice, callsigns and Part 97.

The current layout has 24 collection cards. Registered-item totals are generated in [Content sources](../10-User/ContentSources.md); Manage Library supplies live installation and update state. WikiMed remains separate from first aid, with a cross-link. Manage Library continues to operate on original collections.

The header uses a local transparent PHAROS / DATA ARK wordmark, with an accessible heading and responsive dimensions. Asset: `app/static/assets/pharos-data-ark-flat.png`. Built-in image generation extracted and flattened the supplied gold/blue reference, removing the stone backdrop and cylindrical perspective. Blue A letters have separate oval dots matching the blue lettering. No network font or image dependency is required.

## Card artwork

Every collection card has distinct artwork. Source logos remain recognizable. Learning uses an open book, Games dice/crayon, Wilderness a tent/tree, Power solar/lightning and Food a cookbook/preserving jar. Original pictograms can be rebuilt with `tools/build_collection_icons.py`. Artwork paths live in collection configuration; split cards choose their collection artwork using `dashboard.cards[].artwork_from`. This is presentation configuration, not Python card-specific behavior. The Community service is separate from these collection cards.

Grouped local links (including Radio, Maps and Repairs) use the same button styling as ordinary card links. Subsection headings preserve grouping; plain-text dot separators are not used between those action links.
