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

// Show observation times in the reader's locale and time zone.
document.querySelectorAll("time[data-local-time]").forEach(element => {
    const date = new Date(element.getAttribute("datetime"));
    if (Number.isNaN(date.getTime())) return;
    element.title = new Intl.DateTimeFormat(undefined, {
        dateStyle: "full", timeStyle: "long"
    }).format(date);
    element.textContent = new Intl.DateTimeFormat(undefined, {
        year: "2-digit", month: "numeric", day: "numeric",
        hour: "2-digit", minute: "2-digit"
    }).format(date);
});
