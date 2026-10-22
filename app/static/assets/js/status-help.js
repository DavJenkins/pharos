"use strict";
(() => {
    const descriptions = {
        "eth-button": "The Ark's wired network connection. This indicator does not switch Ethernet on or off.",
        "wifi-button": "The Ark's connection to another Wi-Fi network for internet access. Change it under Network settings.",
        "ap-button": "The DataArk hotspot that your phone or laptop joins to reach local content.",
        "system-button": "Overall health of the Ark and its local services."
    };
    let selected = null;
    function render() {
        if (!selected) return;
        const button = document.getElementById(selected);
        const lines = button.title.split("\n");
        document.getElementById("status-detail-heading").textContent = lines[0];
        document.getElementById("status-detail-description").textContent = descriptions[selected];
        document.getElementById("status-detail-value").textContent = lines.slice(1).join("\n").trim();
    }
    window.addEventListener("DOMContentLoaded", () => {
        const panel = document.getElementById("status-detail");
        for (const [id, description] of Object.entries(descriptions)) {
            const button = document.getElementById(id);
            button.setAttribute("aria-label", button.title + " details");
            button.setAttribute("aria-controls", "status-detail");
            button.setAttribute("aria-expanded", "false");
            button.addEventListener("click", () => {
                if (selected) document.getElementById(selected).setAttribute("aria-expanded", "false");
                selected = id;
                panel.hidden = false;
                button.setAttribute("aria-expanded", "true");
                render();
            });
            new MutationObserver(render).observe(button, {attributes:true, attributeFilter:["title"]});
        }
        document.getElementById("status-detail-close").addEventListener("click", () => {
            const button = document.getElementById(selected);
            button.setAttribute("aria-expanded", "false");
            selected = null;
            panel.hidden = true;
            button.focus();
        });
    });
})();
