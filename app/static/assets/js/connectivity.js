"use strict";

// Check the reader's internet path, independently of the Ark's network adapters.
// These small HTTPS resources test reachability, not individual source availability.
const DataArkConnectivity = {
    probes: ["https://www.gstatic.com/generate_204", "https://en.wikipedia.org/favicon.ico"],
    generation: 0,
    controller: null,
    links: [],

    setState(state) {
        const enabled = state === "online";
        document.getElementById("sync-status")?.classList.toggle("internet-unavailable", state === "offline");
        const status = document.getElementById("internet-status");
        if (status) status.textContent = enabled ? "Internet available" :
            state === "checking" ? "Checking internet..." : "Internet unavailable";
        for (const saved of this.links) {
            const link = saved.element;
            if (enabled) {
                link.setAttribute("href", saved.href);
                link.removeAttribute("aria-disabled");
                if (saved.title === null) link.removeAttribute("title");
                else link.setAttribute("title", saved.title);
            } else {
                // Removing href also prevents keyboard, middle-click and context-menu navigation.
                link.removeAttribute("href");
                link.setAttribute("aria-disabled", "true");
                link.setAttribute("title", state === "checking" ? "Checking internet access" :
                    "Internet check failed. Local content remains available. Use Check internet to retry.");
            }
        }
    },

    async check() {
        const generation = ++this.generation;
        this.controller?.abort();
        this.setState(navigator.onLine === false ? "offline" : "checking");
        if (navigator.onLine === false) return;
        for (const address of this.probes) {
            if (generation !== this.generation) return;
            const controller = new AbortController();
            this.controller = controller;
            const timeout = setTimeout(() => controller.abort(), 4000);
            let reachable = false;
            try {
                await fetch(address, {mode: "no-cors", credentials: "omit", cache: "no-store",
                    referrerPolicy: "no-referrer", signal: controller.signal});
                reachable = true;
            } catch (_) {
                // A blocked probe is not proof that a content source has disappeared.
            } finally {
                clearTimeout(timeout);
            }
            if (generation !== this.generation) return;
            if (reachable) {
                this.setState("online");
                return;
            }
        }
        this.setState("offline");
    },

    initialize() {
        this.links = Array.from(document.querySelectorAll('[data-requires-internet="true"]'))
            .map(element => ({element, href: element.getAttribute("href"), title: element.getAttribute("title")}));
        document.getElementById("internet-retry")?.addEventListener("click", () => this.check());
        window.addEventListener("online", () => this.check());
        window.addEventListener("offline", () => this.check());
        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) this.check();
        });
        setInterval(() => { if (!document.hidden) this.check(); }, 60000);
        this.check();
    }
};

DataArkConnectivity.initialize();