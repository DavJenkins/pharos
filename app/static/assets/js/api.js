"use strict";

/*
 * Data Ark API
 *
 * All communication with the FastAPI backend goes through this module.
 */

const DataArkAPI = {

    async request(url, options = {}) {

        const response = await fetch(url, {
            cache: "no-store",
            signal: AbortSignal.timeout(30000),
            ...options
        });

        if (!response.ok) {
            throw new Error(
                `${response.status} ${response.statusText}`
            );
        }

        return await response.json();
    },

    //----------------------------------------------------------------------
    // Status
    //----------------------------------------------------------------------

    async getStatus() {
        return await this.request(
            `/api/status?_=${Date.now()}`
        );
    },

    //----------------------------------------------------------------------
    // Debug
    //----------------------------------------------------------------------

    async getDebug() {
        return await this.request("/api/debug");
    },

    async setDebug(enabled) {

        return await this.request(
            `/api/debug/${enabled ? "on" : "off"}`,
            {
                method: "POST"
            }
        );
    },

    //----------------------------------------------------------------------
    // Events
    //----------------------------------------------------------------------

    async getEvents(limit = 25) {

        return await this.request(
            `/api/events?limit=${limit}`
        );
    },

    //----------------------------------------------------------------------
    // About
    //----------------------------------------------------------------------

    async getAbout() {

        return await this.request(
            "/api/about"
        );
    }

};

Object.freeze(DataArkAPI);
