"use strict";

/*
 * Data Ark Status Model
 *
 * This module owns the current system status and provides helper
 * functions so the UI never needs to know the raw API schema.
 */

const DataArkStatus = {

    data: null,

    //------------------------------------------------------------------
    // Refresh from API
    //------------------------------------------------------------------

    async refresh() {

        this.data = await DataArkAPI.getStatus();
        const links = document.getElementById("upstream-links");
        if (links) {
            links.replaceChildren();
            const paths = {
                ethernet: "M3 4h18v13h-5v4H8v-4H3V4zm2 2v9h5v4h4v-4h5V6H5zm2 2h2v4H7V8zm4 0h2v4h-2V8zm4 0h2v4h-2V8z",
                wifi: "M2 8a16 16 0 0 1 20 0l-2 2a13 13 0 0 0-16 0L2 8zm4 4a10 10 0 0 1 12 0l-2 2a7 7 0 0 0-8 0l-2-2zm4 4a3 3 0 0 1 4 0l-2 3-2-3z"
            };
            const active = [];
            for (const [key, label] of [["ethernet", "Ethernet"], ["wifi", "Wi-Fi"]]) {
                const network = this.data?.network?.[key];
                const disabled = network?.enabled === false;
                if (network?.connected !== true && !disabled) continue;
                active.push(label + (disabled ? " disabled" : " connected"));
                const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                icon.classList.toggle("upstream-disabled", disabled);
                icon.setAttribute("viewBox", "0 0 24 24");
                icon.setAttribute("role", "img");
                icon.setAttribute("aria-label", label + (disabled ? " disabled" : " connected"));
                const title = document.createElementNS(icon.namespaceURI, "title");
                title.textContent = label + (disabled ? " disabled" : " connected (upstream link)");
                const path = document.createElementNS(icon.namespaceURI, "path");
                path.setAttribute("d", paths[key]);
                icon.append(title, path);
                links.append(icon);
            }
            links.setAttribute("aria-label", active.length ? "Upstream links: " + active.join(" and ") : "No connected upstream links reported");
        }

        return this.data;
    },

    //------------------------------------------------------------------
    // General
    //------------------------------------------------------------------

    get state() {

        return this.data?.status?.state ?? "unknown";
    },

    get debug() {

        return !!this.data?.status?.debug;
    },

    get sync() {

        return this.data?.status?.sync ?? "";
    },

    get updated() {

        return this.data?.status?.updated ?? "";
    },

    //------------------------------------------------------------------
    // Ethernet
    //------------------------------------------------------------------

    get ethernet() {

        return this.data?.network?.ethernet ?? {};
    },

    //------------------------------------------------------------------
    // Wi-Fi
    //------------------------------------------------------------------

    get wifi() {

        return this.data?.network?.wifi ?? {};
    },

    //------------------------------------------------------------------
    // Access Point
    //------------------------------------------------------------------

    get accessPoint() {

        return this.data?.network?.access_point ?? {};
    },

    //------------------------------------------------------------------
    // System
    //------------------------------------------------------------------

    get system() {

        return this.data?.system ?? {};
    },

    //------------------------------------------------------------------
    // Resources
    //------------------------------------------------------------------

    get resources() {

        return this.data?.resources ?? {};
    },

    //------------------------------------------------------------------
    // Services
    //------------------------------------------------------------------

    get services() {

        return this.data?.services ?? {};
    },

    //------------------------------------------------------------------
    // Tooltip helpers
    //------------------------------------------------------------------

    syncTooltip() {
        const update = this.data?.status?.update;
        const lines = [this.sync || "Sync status unavailable"];
        if (update?.detail) lines.push("", update.detail);
        else if (update?.state === "waiting") lines.push("", "The worker has not reported a waiting reason.");
        if (update?.asset) lines.push("Asset: " + update.asset);
        if (update?.updated) {
            const date = new Date(update.updated);
            if (!Number.isNaN(date.getTime())) lines.push("Last worker update: " + date.toLocaleString());
        }
        return lines.join("\n");
    },

    ethernetTooltip() {

        const e = this.ethernet;

        return [
            "Ethernet",
            "",
            `Enabled   : ${e.enabled === false ? "No — disabled" : e.enabled === true ? "Yes" : "Unknown"}`,
            `Cable link: ${e.carrier === true ? "Connected" : e.carrier === false ? "Disconnected" : "Unknown"}`,
            `Connected : ${e.connected === true ? "Yes" : e.connected === false ? "No" : "Unavailable"}`,
            `IP        : ${e.ip ?? "-"}`,
            `Gateway   : ${e.gateway ?? "-"}`
        ].join("\n");
    },

    wifiTooltip() {

        const w = this.wifi;

        return [
            "Wi-Fi",
            "",
            `Enabled   : ${w.enabled === false ? "No — disabled" : w.enabled === true ? "Yes" : "Unknown"}`,
            `SSID      : ${w.ssid ?? "-"}`,
            `Connected : ${w.connected === true ? "Yes" : w.connected === false ? "No" : "Unavailable"}`,
            `Signal    : ${w.signal?.dbm ?? "-"} dBm`,
            `Strength  : ${w.signal?.percent ?? "-"} %`,
            `Rate      : ${w.rate ?? "-"}`,
            `IP        : ${w.ip ?? "-"}`,
            `Gateway   : ${w.gateway ?? "-"}`
        ].join("\n");
    },

    apTooltip() {

        const ap = this.accessPoint;

        return [
            "Access Point",
            "",
            `Active    : ${ap.active === true ? "Yes" : ap.active === false ? "No" : "Unavailable"}`,
            `IP        : ${ap.ip || "-"}`,
            `SSID      : ${ap.ssid ?? "-"}`,
            `Clients   : ${ap.client_count ?? 0}`
        ].join("\n");
    },

    systemTooltip() {

        const s = this.system;

        return [
            "System",
            "",
            `State     : ${this.state}`,
            ...(this.data?.status?.issues ?? []),
            `Hostname  : ${s.hostname ?? "-"}`,
            `Platform  : ${s.platform ?? "-"}`,
            `Uptime    : ${s.uptime ?? "-"}`,
            `Memory used: ${this.resources.memory?.used || "—"}`,
            `Memory available: ${this.resources.memory?.available || "—"}`,
            `Swap used: ${this.resources.memory?.swap_used || "—"}`
        ].join("\n");
    }

};

Object.seal(DataArkStatus);
