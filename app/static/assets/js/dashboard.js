"use strict";

/*
 * Data Ark Dashboard Controller
 */

const Dashboard = {

    refreshEnabled: true,
    refreshIntervalSeconds: 5,
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
            this.refreshIntervalSeconds * 1000
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

    loadRefreshInterval() {
        let seconds;
        try { seconds = Number(localStorage.getItem("dataark.dashboard.refreshIntervalSeconds")); }
        catch (_) { return; }
        if (Number.isInteger(seconds) && seconds >= 5 && seconds <= 300)
            this.refreshIntervalSeconds = seconds;
    },

    setRefreshInterval(seconds) {
        if (!Number.isInteger(seconds) || seconds < 5 || seconds > 300)
            throw new RangeError("Choose a whole number from 5 to 300 seconds.");
        this.refreshIntervalSeconds = seconds;
        try { localStorage.setItem("dataark.dashboard.refreshIntervalSeconds", String(seconds)); }
        catch (_) { /* The preference still works for this page if storage is unavailable. */ }
        this.stopTimer();
        if (this.refreshEnabled) this.startTimer();
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
        b.setAttribute("data-enabled", String(this.refreshEnabled));
        b.classList.toggle("on", this.refreshEnabled);
        b.classList.toggle("off", !this.refreshEnabled);

        b.title =
            "Auto Refresh\n\n" +
            (this.refreshEnabled
                ? "Enabled (" + this.refreshIntervalSeconds + " seconds)"
                : "Paused");
    },

    updateDebugButton() {

        const b = this.byId("debug-button");

        if (!b)
            return;

        b.classList.remove("error");
        b.setAttribute("data-enabled", String(DataArkStatus.debug));
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
        const caps=DataArkStatus.data?.network?.capabilities;
        for(const [id,available] of [["wifi-button",caps?.wifi],["ap-button",caps?.hotspot],["portal-continue",caps?.hotspot]]){
            const tile=this.byId(id)?.closest(".status-tile");if(tile)tile.hidden=available===false;
        }

        this.byId("eth-button").className =
            "status-button " +
            (eth.enabled === false ? "disabled" : eth.connected === true ? "on" : eth.connected === false ? "off" : "error");

        this.byId("wifi-button").className =
            "status-button " +
            (wifi.enabled === false ? "disabled" : wifi.connected === true ? "on" : wifi.connected === false ? "off" : "error");

        this.byId("ap-button").className =
            "status-button " +
            (ap.enabled === false ? "disabled" : ap.active === true ? "on" : ap.active === false ? "off" : "error");

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
            window.dispatchEvent(new Event("dataark:dashboard-refreshed"));

        }
        catch (err) {

            console.error(err);
            DataArkStatus.data = null;
            this.byId("debug-button").removeAttribute("data-enabled");
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

        this.loadRefreshInterval();
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
