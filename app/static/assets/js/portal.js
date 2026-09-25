"use strict";
(async () => {
    if (location.hostname !== "192.168.4.1") return;
    const box = document.getElementById("portal-welcome");
    const button = document.getElementById("portal-continue");
    const message = document.getElementById("portal-message");
    if (!box || !button || !message) return;
    let state = null;
    let busy = false;
    box.hidden = false;
    async function refresh() {
        const response = await fetch("/api/portal/state", {cache:"no-store"});
        if (!response.ok) throw new Error("State unavailable");
        const current = await response.json();
        if (typeof current.enabled !== "boolean" || typeof current.upstream_online !== "boolean")
            throw new Error("Invalid state");
        state = current;
        button.textContent = "Internet pass-through: " + (state.enabled ? "On" : "Off");
        button.setAttribute("aria-pressed",String(state.enabled));
        button.disabled = !state.enabled && !state.upstream_online;
        message.textContent = state.upstream_online ?
            (state.enabled ? "Using the Ark's internet connection." : "The Ark is online. Enable access for this device if needed.") :
            "The Ark is offline. Local content remains available.";
    }
    function unavailable() {
        state = null;
        button.disabled = true;
        button.textContent = "Pass-through: Unavailable";
        button.removeAttribute("aria-pressed");
        message.textContent = "Could not read pass-through state. Local content remains available.";
    }
    async function update() {
        if (busy) return;
        busy = true;
        try { await refresh(); } catch (_) { unavailable(); }
        finally { busy = false; }
    }
    button.addEventListener("click", async () => {
        if (busy || !state) return;
        busy = true;
        button.disabled = true;
        try {
            const response = await fetch("/api/portal/pass-through/" + (state.enabled ? "off" : "on"), {method:"POST"});
            if (!response.ok) throw new Error("Switch failed");
            await refresh();
            if (typeof DataArkConnectivity !== "undefined") DataArkConnectivity.check();
        } catch (_) {
            try { await refresh(); } catch (_) { unavailable(); }
            message.textContent = "Could not confirm the change. Check the displayed state and try again.";
        } finally { busy = false; }
    });
    await update();
    setInterval(() => { if (!document.hidden) update(); },30000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) update(); });
})();
