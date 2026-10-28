"use strict";
(() => {
    const el = id => document.getElementById(id);
    let busy = false, deadline = null, poll = null;
    async function request(action, payload = {}) {
        const password = await window.CaretakerAuth.password("Authorize Wi-Fi adapter assignment.");
        const bytes = new TextEncoder().encode("admin:" + password);
        const authorization = "Basic " + btoa(Array.from(bytes, b => String.fromCharCode(b)).join(""));
        const response = await fetch("/api/network/admin/" + action, {
            method: "POST", cache: "no-store", signal: AbortSignal.timeout(155000),
            headers: {"Content-Type":"application/json", "Authorization":authorization},
            body: JSON.stringify(payload)
        });
        window.CaretakerAuth.rejected(response);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Adapter operation failed.");
        return data;
    }
    function show(data) {
        const select = el("hotspot-adapter");
        select.replaceChildren();
        for (const adapter of data.adapters) {
            const option = document.createElement("option");
            option.value = adapter.id;
            option.textContent = adapter.label + " — " + adapter.interface + (adapter.ap_capable ? "" : " (hotspot unsupported)");
            option.disabled = !adapter.ap_capable;
            option.selected = adapter.interface === data.hotspot;
            select.appendChild(option);
        }
        const hotspot = data.adapters.find(a => a.interface === data.hotspot);
        const upstream = data.adapters.find(a => a.interface !== data.hotspot);
        el("adapter-summary").textContent = "Current hotspot: " + (hotspot?.label || data.hotspot) +
            ". Upstream: " + (upstream?.label || "No second adapter") + ".";
        el("adapter-settings").hidden = false;
        el("adapter-pending").hidden = !data.pending;
        el("apply-adapters").disabled = data.pending;
        deadline = data.deadline;
        el("adapter-result").textContent = data.pending ? data.message : "Current assignment loaded.";
        clearInterval(poll);
        poll = data.pending ? setInterval(() => { if (!busy && window.CaretakerAuth.isRemembered()) perform("adapters", {}, true); }, 10000) : null;
    }
    async function perform(action, payload = {}, quiet = false) {
        if (busy) return;
        busy = true;
        document.querySelectorAll("button").forEach(b => b.disabled = true);
        if (!quiet) el("adapter-result").textContent = action === "assign" ?
            "Changing adapters. If disconnected, reconnect to DataArk and return here to confirm. Automatic rollback is armed." : "Checking the assignment…";
        try {
            show(await request(action, payload));
        } catch (error) {
            el("adapter-result").textContent = error instanceof TypeError || error.name === "TimeoutError" ?
                "Connection interrupted. Reconnect to DataArk, return here and load adapters to confirm. Without confirmation the previous assignment will be restored." : error.message;
        } finally {
            busy = false;
            document.querySelectorAll("button").forEach(b => b.disabled = false);
            el("apply-adapters").disabled = !el("adapter-pending").hidden;
        }
    }
    el("load-adapters").addEventListener("click", () => perform("adapters"));
    el("adapter-form").addEventListener("submit", event => {
        event.preventDefault();
        if (confirm("Change Wi-Fi adapter roles? Wi-Fi clients will disconnect briefly. Reconnect and confirm within four minutes, or the Ark will restore the previous assignment."))
            perform("assign", {adapter:el("hotspot-adapter").value});
    });
    el("confirm-adapters").addEventListener("click", () => perform("confirm-roles"));
    el("revert-adapters").addEventListener("click", () => perform("revert-roles"));
    setInterval(() => {
        if (deadline) el("adapter-countdown").textContent = "Automatic restore in " + Math.max(0,Math.ceil(deadline-Date.now()/1000)) + " seconds unless you keep this assignment.";
    }, 1000);
})();
