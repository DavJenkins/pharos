# Bootstrap release publishing

Large bootstrap downloads live in GitHub Releases. The DEJ website provides the stable entry page, download links and a small `bootstrap-release.json` record; it does not proxy or store the large kit.

`tools/build_bootstrap_release.py` accepts a checksum-verified input kit and a committed source revision. It compares the existing executable files against the clean-replay kit, replaces the combined source manifest with the exported public manifest, retains the public configuration mirror and includes only the named bootstrap tool/license files. Device radio preferences, appliance inventories and private household configuration are omitted.

The resulting tarball includes `START-ARK.sh`, a short README and an internal per-file `MANIFEST.json`. The public release also carries `SHA256SUMS` and `release-manifest.json`. Verify the internal checksums and archive paths, then exercise the coordinator's static validation on Linux before publishing.

Use a versioned tag on the feature branch, initially a GitHub prerelease. Upload as a draft, verify the hosted asset checksum, then publish and update the website's bootstrap entry page. Never replace an already published version with different bytes: issue another version instead. Preserve earlier public document editions and download links.

Only small generated pages, PDFs and release metadata are sent by FTPS. Publication of a preview does not change the recovery branch's merge policy.
