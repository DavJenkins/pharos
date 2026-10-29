# Public and offline documentation

`config/documentation.yaml` registers the collection catalogue, feature catalogue, engineering chapter, bootstrap status, installation guide and handbook. Repository Markdown and existing PDFs are authoritative inputs. The configured landing-page resource shelf links to stable `/about/<document>/` addresses.

`tools/build_public_documents.py` generates the offline pages during software deployment. `--website /path/to/website` additionally builds matching public editions under `/data-ark/<document>/`, preserves a dated, content-fingerprinted edition and copies the two catalogue PDFs. `publication.json` records input checksums, repository HEAD at generation and the update policy. Its SHA-256 map defines the exact inputs even when the authoring checkout is modified.

These are bundled software documents. They are not independently downloaded, removed or updated by the publication/content queue. A software upgrade regenerates the installed edition; an internet failure does not remove the instructions. Public website editions are supplemental. Public operating-guide links outside the six selected documents point to the recorded repository revision; local editions link to the installed handbook.

The website publisher uploads only generated HTML, PDFs and publication metadata from the public folder. Raw configuration, private appliance state, household files, credentials and development logs are not part of that file set. Existing `/data-ark-collection.html` and its PDF remain compatible with previously distributed links.

Versioned bootstrap downloads are hosted on GitHub Releases. The website entry page links the kit, release notes and checksums; `/data-ark/bootstrap-release.json` provides a small current-download record from `config/bootstrap-release.json`. Preview 1 preserves the executable source from the successful clean replay. The FTP site stores no large bootstrap archive. Physical Pi validation remains the next step for the preview.
