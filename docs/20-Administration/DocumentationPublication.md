# Public and offline documentation

`config/documentation.yaml` registers the collection catalogue, feature catalogue, engineering chapter, bootstrap status, installation guide and handbook. The complete handbook is published online at `/data-ark/docs/`, with all Markdown pages, public document attachments, attribution and file-access guides. `/data-ark/api/` presents the exported API contract as a read-only reference. Repository Markdown and existing PDFs are authoritative inputs. Help starts with Welcome and groups the reference links under About and maintain the Ark. Installed overview documents retain their stable `/about/<document>/` addresses.

`tools/build_public_documents.py` generates the offline pages during software deployment. `--website /path/to/website` additionally builds matching public editions under `/data-ark/<document>/`, preserves a dated, content-fingerprinted edition and copies the two catalogue PDFs. `publication.json` records input checksums, repository HEAD at generation and the update policy. Its SHA-256 map defines the exact inputs even when the authoring checkout is modified.

These are bundled software documents. They are not independently downloaded, removed or updated by the publication/content queue. A software upgrade regenerates the installed edition; an internet failure does not remove the instructions. Public website editions are supplemental. The current public edition includes the complete handbook and API reference; local editions link to the installed handbook.

The website publisher uploads only generated HTML, PDFs and publication metadata from the public folder. Public handbook JSON attachments and the exported API schema are included. Raw appliance configuration, private appliance state, household files, credentials and development logs are not part of that file set. Existing `/data-ark-collection.html` and its PDF remain compatible with previously distributed links.

Versioned bootstrap downloads are hosted on GitHub Releases. The website entry page links the kit, release notes and checksums; `/data-ark/bootstrap-release.json` provides a small current-download record from `config/bootstrap-release.json`. Preview 2 carries its exact tested source revision and a bundled release-audit record. Earlier clean-system replay evidence remains separate. The FTP site stores no large bootstrap archive. Physical spare-media acceptance remains separate from the web/deployment audit.

The Git repository remains the source of truth. Online and offline versions are built from the same sources; the public website is a publication target, not an upstream copy that older appliances silently fetch. Internal handbook links stay within the handbook. Links to controls, library files and appliance-specific certificates are identified as belonging to the reader’s Ark. Each software edition preserves its own sources and schema.


## Download storage

The current readable handbook stays on the DEJ Software website. Catalogue PDFs and self-contained archived handbook ZIPs are GitHub Release assets, described by `config/document-downloads.json` and the public `/data-ark/downloads.json`. Website edition addresses are small download landing pages. They do not duplicate the full historical handbook or its PDFs on the limited FTP account.

A website build stages the complete rendered edition under `output/document-download-staging` and packages release files under `output/document-downloads`. Each ZIP includes a start page and stylesheet and rewrites its internal navigation for extracted offline use. PDF filenames include their checksum prefix; new handbook ZIP names include their content hash. Already published assets must not be overwritten with different bytes.

Publish and verify the staged assets on the configured GitHub release before publishing the website. The website publisher checks asset availability before uploading any site files. It reuses FTPS connections, retries bounded transient failures, and compares every deployed file with its local source. The verifier reverses only known Cloudflare email-protection transformations.


Public handbook builds reject absolute desktop drive paths and user-profile paths. Desktop-only procedures identify their host context and use a reader-chosen workspace with relative commands. Ark service paths remain explicit where they are part of the supported installation layout. Network addresses and certificate identities must come from the reader’s own device.
