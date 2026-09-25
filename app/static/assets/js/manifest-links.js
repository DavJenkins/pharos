"use strict";
document.querySelectorAll("[data-manifest-kiwix-port]").forEach(link => {
    const destination = new URL(location.href);
    destination.protocol = "http:";
    destination.port = link.dataset.manifestKiwixPort;
    const path = new URL(link.dataset.manifestKiwixPath, destination.origin);
    destination.pathname = path.pathname;
    destination.search = path.search;
    destination.hash = path.hash;
    link.href = destination.href;
});
