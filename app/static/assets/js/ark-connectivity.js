"use strict";
(async () => {
    const status = document.getElementById("internet-status");
    if (!status) return;
    let busy = false;
    async function refresh() {
        if (busy) return;
        busy = true;
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(),8000);
        let online = false;
        try {
            const response = await fetch("/api/portal/upstream", {cache:"no-store",signal:controller.signal});
            if (!response.ok) throw new Error("Status unavailable");
            const state = await response.json();
            if (typeof state.online !== "boolean") throw new Error("Invalid state");
            online = state.online;
            status.textContent = online ? "Ark online" : "Ark offline";
            status.title = "The Ark's upstream internet connection; pass-through is controlled separately.";
        } catch (_) {
            status.textContent = "Ark connection unknown";
            status.title = "Unable to check the Ark's internet connection.";
        } finally {
            document.getElementById("sync-status")?.classList.toggle("internet-unavailable", !online);
            status.dataset.online = String(online);
            window.dispatchEvent(new Event("dataark:connectivity-refreshed"));
            clearTimeout(timeout);
            busy = false;
        }
    }
    await refresh();
    setInterval(() => { if (!document.hidden) refresh(); },30000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
})();
