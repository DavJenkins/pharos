"use strict";

/*
 * Data Ark Dashboard Controller
 */

const Dashboard = {

    refreshEnabled: true,
    refreshTimer: null,
    refreshing: false,

    //------------------------------------------------------------------
    // Utility
    //------------------------------------------------------------------

    byId(id) {
        return document.getElementById(id);
    },

    //------------------------------------------------------------------
    // Refresh Timer
    //------------------------------------------------------------------

    startTimer() {

        if (this.refreshTimer)
            return;

        this.refreshTimer = setInterval(
            () => this.refresh(),
            5000
        );
    },

    stopTimer() {

        if (!this.refreshTimer)
            return;

        clearInterval(this.refreshTimer);

        this.refreshTimer = null;
    },

    toggleRefresh() {

        this.refreshEnabled = !this.refreshEnabled;

        if (this.refreshEnabled)
            this.startTimer();
        else
            this.stopTimer();

        this.updateRefreshButton();
    },

    //------------------------------------------------------------------
    // Buttons
    //------------------------------------------------------------------

    updateRefreshButton() {

        const b = this.byId("refresh-button");

        if (!b)
            return;

        b.classList.remove("error");
        b.setAttribute("aria-pressed", String(this.refreshEnabled));
        b.classList.toggle("on", this.refreshEnabled);
        b.classList.toggle("off", !this.refreshEnabled);

        b.title =
            "Auto Refresh\n\n" +
            (this.refreshEnabled
                ? "Enabled (5 seconds)"
                : "Paused");
    },

    updateDebugButton() {

        const b = this.byId("debug-button");

        if (!b)
            return;

        b.classList.remove("error");
        b.setAttribute("aria-pressed", String(DataArkStatus.debug));
        b.classList.toggle("on", DataArkStatus.debug);
        b.classList.toggle("off", !DataArkStatus.debug);

        b.title =
            "Debug\n\n" +
            (DataArkStatus.debug
                ? "Enabled"
                : "Disabled");
    },

    //------------------------------------------------------------------
    // Status Icons
    //------------------------------------------------------------------

    updateIcons() {

        const eth = DataArkStatus.ethernet;
        const wifi = DataArkStatus.wifi;
        const ap = DataArkStatus.accessPoint;

        this.byId("eth-button").className =
            "status-button " +
            (eth.connected === true ? "on" : eth.connected === false ? "off" : "error");

        this.byId("wifi-button").className =
            "status-button " +
            (wifi.connected === true ? "on" : wifi.connected === false ? "off" : "error");

        this.byId("ap-button").className =
            "status-button " +
            (ap.active === true ? "on" : ap.active === false ? "off" : "error");

        this.byId("system-button").className =
            "status-button " +
            (DataArkStatus.state === "ok"
                ? "on"
                : "error");

        //------------------------------------------------------------------
        // Rich hover text
        //------------------------------------------------------------------

        this.byId("eth-button").title =
            DataArkStatus.ethernetTooltip();

        this.byId("wifi-button").title =
            DataArkStatus.wifiTooltip();

        this.byId("ap-button").title =
            DataArkStatus.apTooltip();

        this.byId("system-button").title =
            DataArkStatus.systemTooltip();
    },

    //------------------------------------------------------------------
    // Main Refresh
    //------------------------------------------------------------------

    async refresh() {

        if (this.refreshing) return;
        this.refreshing = true;
        try {

            await DataArkStatus.refresh();

            this.updateIcons();

            this.updateDebugButton();

            this.updateRefreshButton();

            this.byId("sync-status").textContent =
                DataArkStatus.sync;
            this.byId("sync-status").title = typeof DataArkStatus.syncTooltip === "function"
                ? DataArkStatus.syncTooltip()
                : (DataArkStatus.data?.status?.update?.detail || DataArkStatus.sync);

        }
        catch (err) {

            console.error(err);
            DataArkStatus.data = null;
            this.byId("debug-button").removeAttribute("aria-pressed");
            this.byId("sync-status").textContent = "Unavailable";
            this.byId("sync-status").title = "Status unavailable; the last worker state could not be refreshed.";
            for (const id of ["eth-button", "wifi-button", "ap-button", "system-button", "debug-button"]) {
                this.byId(id).className = "status-button error";
                this.byId(id).title = "Status unavailable; retrying automatically";
            }
        } finally {
            this.refreshing = false;
        }

    },

    //------------------------------------------------------------------
    // Startup
    //------------------------------------------------------------------

    async initialize() {

        this.updateRefreshButton();

        this.byId("refresh-button")
            ?.addEventListener(
                "click",
                () => this.toggleRefresh()
            );

        this.byId("debug-button")
            ?.addEventListener(
                "click",
                async () => {

                    await DataArkAPI.setDebug(
                        !DataArkStatus.debug
                    );

                    await this.refresh();

                }
            );

        await this.refresh();

        this.startTimer();

    }

};

window.addEventListener(
    "DOMContentLoaded",
    () => Dashboard.initialize()
);
