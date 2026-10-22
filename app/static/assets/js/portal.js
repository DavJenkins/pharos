"use strict";
(async () => {
    const button = document.getElementById("portal-continue");
    const message = document.getElementById("portal-message");
    const indicator = document.getElementById("portal-state");
    if (!button || !message || !indicator) return;
    if (location.hostname !== "192.168.4.1") {
        button.title = "Connect to the Ark Wi-Fi and open 192.168.4.1 to control internet access for this device.";
        button.setAttribute("aria-label", button.title);
        return;
    }
    let state = null;
    let busy = false;
    async function refresh() {
        const response = await fetch("/api/portal/state", {cache:"no-store"});
        if (!response.ok) throw new Error("State unavailable");
        const current = await response.json();
        if (typeof current.enabled !== "boolean" || typeof current.upstream_online !== "boolean")
            throw new Error("Invalid state");
        state = current;
        indicator.textContent = state.enabled ? "ON" : "OFF";
        button.classList.toggle("on", state.enabled);
        button.classList.toggle("off", !state.enabled);
        button.classList.remove("error");
        button.title = state.enabled ? "Internet access for this device is on. Tap to turn off." :
            state.upstream_online ? "Enable internet access for this device (up to six hours)." : "No upstream internet connection.";
        button.setAttribute("aria-label", "Internet access " + indicator.textContent + ". " + button.title);
        button.setAttribute("aria-pressed",String(state.enabled));
        button.setAttribute("aria-disabled", String(!state.enabled && !state.upstream_online));
        message.textContent = state.upstream_online ?
            (state.enabled ? "Using the Ark's internet connection." : "The Ark is online. Enable access for this device if needed.") :
            "The Ark is offline. Local content remains available.";
    }
    function unavailable() {
        state = null;
        button.setAttribute("aria-disabled", "true");
        indicator.textContent = "?";
        button.classList.remove("on", "off");
        button.classList.add("error");
        button.title = "Internet access status unavailable. Local content remains available.";
        button.setAttribute("aria-label", button.title);
        button.removeAttribute("aria-pressed");
        message.textContent = "Could not read internet access status. Local content remains available.";
    }
    async function update() {
        if (busy) return;
        busy = true;
        try { await refresh(); } catch (_) { unavailable(); }
        finally { busy = false; }
    }
    button.addEventListener("click", async () => {
        if (busy || !state || (!state.enabled && !state.upstream_online)) return;
        busy = true;
        button.setAttribute("aria-busy", "true");
        try {
            const response = await fetch("/api/portal/pass-through/" + (state.enabled ? "off" : "on"), {method:"POST"});
            if (!response.ok) throw new Error("Switch failed");
            await refresh();
            if (typeof DataArkConnectivity !== "undefined") DataArkConnectivity.check();
        } catch (_) {
            try { await refresh(); } catch (_) { unavailable(); }
            message.textContent = "Could not confirm the change. Check the displayed state and try again.";
        } finally { busy = false; button.removeAttribute("aria-busy"); }
    });
    await update();
    setInterval(() => { if (!document.hidden) update(); },30000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) update(); });
})();
