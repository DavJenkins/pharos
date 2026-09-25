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

    ethernetTooltip() {

        const e = this.ethernet;

        return [
            "Ethernet",
            "",
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
            `Uptime    : ${s.uptime ?? "-"}`
        ].join("\n");
    }

};

Object.seal(DataArkStatus);
