"use strict";

/*
 * Data Ark Dashboard Controller
 */

const Dashboard = {

    refreshEnabled: true,
    refreshTimer: null,

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
            (eth.connected ? "on" : "off");

        this.byId("wifi-button").className =
            "status-button " +
            (wifi.connected ? "on" : "off");

        this.byId("ap-button").className =
            "status-button " +
            ((ap.client_count || 0) > 0
                ? "on"
                : "off");

        this.byId("system-button").className =
            "status-button " +
            (DataArkStatus.state === "ok"
                ? "on"
                : "off");

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

        try {

            await DataArkStatus.refresh();

            this.updateIcons();

            this.updateDebugButton();

            this.updateRefreshButton();

            this.byId("sync-status").textContent =
                DataArkStatus.sync;

        }
        catch (err) {

            console.error(err);

        }

    },

    //------------------------------------------------------------------
    // Startup
    //------------------------------------------------------------------

    async initialize() {

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
