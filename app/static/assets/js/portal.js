"use strict";
(async () => {
    if (location.hostname !== "192.168.4.1") return;
    const box = document.getElementById("portal-welcome");
    const button = document.getElementById("portal-continue");
    if (!box || !button) return;
    try {
        const response = await fetch("/api/portal/state", {cache: "no-store"});
        if (!response.ok || await response.json()) return;
    } catch (_) { return; }
    box.hidden = false;
    button.addEventListener("click", async () => {
        button.disabled = true;
        try {
            const response = await fetch("/api/portal/continue", {method: "POST"});
            if (!response.ok) throw new Error("Portal acknowledgement failed");
            document.getElementById("portal-message").textContent =
                "You can use the internet when available. Bookmark http://192.168.4.1/ to return to the Ark.";
            button.hidden = true;
        } catch (_) {
            document.getElementById("portal-message").textContent = "Please try again. The local library remains available.";
        } finally { button.disabled = false; }
    });
})();
