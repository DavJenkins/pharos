"use strict";
const el = id => document.getElementById(id);
const action = document.body.dataset.action;
let busy = false;

async function adminRequest(operation, payload) {
    const password = el("admin-password").value;
    if (!password) throw new Error("Enter the network administration password.");
    const bytes = new TextEncoder().encode("admin:" + password);
    const authorization = "Basic " + btoa(Array.from(bytes, b => String.fromCharCode(b)).join(""));
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 160000);
    let response;
    try {
        response = await fetch("/api/network/admin/" + operation, {
            method: "POST", cache: "no-store", signal: controller.signal,
            headers: {"Content-Type": "application/json", "Authorization": authorization},
            body: JSON.stringify(payload)
        });
    } catch (error) {
        throw new Error(operation === "scan" ? "Unable to reach the Pi. Reconnect and retry." :
            "The connection was lost or timed out. The change may have completed. Reconnect and check the current network before retrying.");
    } finally {
        clearTimeout(timer);
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Network operation failed.");
    return data;
}

async function operation(name, payload) {
    if (busy) return;
    busy = true;
    document.querySelectorAll("button").forEach(button => button.disabled = true);
    el("result").textContent = name === "scan" ? "Looking for networks on the upstream adapter…" : "Applying change; please wait. This may take up to two minutes…";
    try {
        const data = await adminRequest(name, payload);
        if (name === "scan") {
            const list = el("networks");
            list.replaceChildren();
            data.networks.forEach(ssid => {
                const option = document.createElement("option");
                option.value = ssid;
                list.appendChild(option);
            });
            el("result").textContent = data.networks.length + " networks found. Choose or enter a network name.";
        } else {
            el("result").textContent = data.message + (name === "uplink" ? "" : " Reconnect if needed, then reload this page to verify.");

            if (el("wifi-password")) el("wifi-password").value = "";
        }
    } catch (error) {
        el("result").textContent = error.message;
    } finally {
        busy = false;
        document.querySelectorAll("button").forEach(button => button.disabled = false);
        if (action === "connect") await refreshNetwork();
    }
}

el("scan")?.addEventListener("click", () => operation("scan", {}));
el("security")?.addEventListener("change", () => {
    const open = el("security").value === "open";
    el("wifi-password").disabled = open;
    if (open) el("wifi-password").value = "";
});
el("network-form").addEventListener("submit", event => {
    event.preventDefault();
    const ssid = el("ssid").value;
    if (!ssid || new TextEncoder().encode(ssid).length > 32) {
        el("result").textContent = "Network names must contain 1 to 32 UTF-8 bytes.";
        return;
    }
    const payload = {ssid};
    if (action === "connect") {
        payload.security = el("security").value;
        payload.password = el("wifi-password").value;
    }
    operation(action, payload);
});

async function refreshNetwork() {
return fetch("/api/status", {cache: "no-store"}).then(response => {
    if (!response.ok) throw new Error("Status unavailable");
    return response.json();
}).then(data => {
    if (action === "connect") {
        const wifi = data.network?.wifi;
        el("uplink-disable").disabled = wifi?.enabled === false;
        el("uplink-enable").disabled = wifi?.connected === true;
    }
    const name = action === "rename" ? data.network?.access_point?.ssid : data.network?.wifi?.ssid;
    el("current").textContent = action === "connect" && data.network?.wifi?.enabled === false ? "Upstream Wi-Fi disabled. Saved networks retained." : name ? "Current network: " + name : "Current network unavailable or disconnected.";
    if (!el("ssid").value && name) el("ssid").value = name;
}).catch(() => {el("current").textContent = "Current network unavailable.";});

}
refreshNetwork();
el("uplink-disable")?.addEventListener("click", () => {
    if (confirm("Disable the Ark’s upstream Wi-Fi? Stay connected through the DataArk hotspot at 192.168.4.1. Saved networks will be retained.")) operation("uplink", {enabled: false});
});
el("uplink-enable")?.addEventListener("click", () => operation("uplink", {enabled: true}));
