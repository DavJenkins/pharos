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
function updateLocalTimes() {
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
    if (element.closest(".source-check-summary")) {
        const elapsed = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
        const units = [[86400, "day"], [3600, "hour"], [60, "minute"]];
        const unit = units.find(([seconds]) => elapsed >= seconds);
        const age = unit ? Math.floor(elapsed / unit[0]) : 0;
        const relative = unit ? age + " " + unit[1] + (age === 1 ? "" : "s") + " ago" : "just now";
        element.textContent += " (" + relative + ")";
    }
});
}
updateLocalTimes();
setInterval(updateLocalTimes, 60000);
