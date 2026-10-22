"use strict";
(() => {
    const items = {
        "eth-button": {name:"Ethernet", description:"The Ark's wired network connection."},
        "wifi-button": {name:"Wi-Fi", description:"The Wi-Fi network the Ark uses to reach the internet.", settings:"/config/wifi.html", settingsLabel:"Change upstream Wi-Fi"},
        "ap-button": {name:"Hotspot", description:"The DataArk Wi-Fi network your devices join to use the Ark.", settings:"/config/system.html", settingsLabel:"Change hotspot settings"},
        "portal-continue": {name:"Internet pass-through", description:"Allow this device to reach the internet through the Ark. This does not change access for other devices. Permission lasts up to six hours and resets when the Ark restarts.", toggle:true},
        "system-button": {name:"System", description:"The Ark's health, platform, and running time."},
        "refresh-button": {name:"Auto refresh", description:"Update the displayed dashboard status every five seconds. Pausing this does not stop the Ark's services.", toggle:true},
        "debug-button": {name:"Debug", description:"Record diagnostic information for troubleshooting. Portal monitoring runs only while Debug is on. Logs stay on this Ark, rotate automatically, and include known portal-check DNS names.", toggle:true},
    };
    window.addEventListener("DOMContentLoaded", () => {
        const dialog = document.getElementById("status-dialog");
        const heading = document.getElementById("status-dialog-heading");
        const description = document.getElementById("status-dialog-description");
        const value = document.getElementById("status-dialog-value");
        const action = document.getElementById("status-dialog-action");
        const link = document.getElementById("status-dialog-link");
        const close = document.getElementById("status-dialog-close");
        let selected = null;
        let allowAction = false;
        let pending = null;
        let pendingTimer = null;
        function renderDetails(item, title) {
            value.replaceChildren();
            const list = document.createElement("dl");
            list.className = "status-details-list";
            const lines = (title || "Status unavailable").split("\n").map(line => line.trim()).filter(Boolean);
            for (const line of lines.length > 1 ? lines.slice(1) : lines) {
                const field = line.match(/^([^:]+):\s*(.*)$/);
                if (field) {
                    const label = document.createElement("dt");
                    const content = document.createElement("dd");
                    label.textContent = field[1].trim();
                    content.textContent = field[2].trim() || "—";
                    if (label.textContent === "State" && content.textContent === "ok") content.textContent = "Healthy";
                    list.append(label, content);
                } else {
                    const note = document.createElement("dd");
                    note.className = "status-details-note";
                    note.textContent = line;
                    list.append(note);
                }
            }
            value.append(list);
        }
        function render() {
            if (!selected) return;
            const item = items[selected], original = document.getElementById(selected);
            heading.textContent = item.name;
            description.textContent = item.description;
            renderDetails(item, original.title);
            value.hidden = !!item.url || !!item.toggle;
            document.getElementById("status-dialog-toggle-row").hidden = !item.toggle;
            if (item.toggle) {
                const enabled = original.classList.contains("on");
                const unavailable = original.getAttribute("data-action-disabled") === "true" || original.classList.contains("error");
                if (pending && pending.id === selected && enabled === pending.checked) {
                    pending = null;
                    clearTimeout(pendingTimer);
                }
                action.disabled = unavailable || original.getAttribute("aria-busy") === "true" || !!pending;
                action.checked = pending && pending.id === selected ? pending.checked : enabled;
                document.getElementById("status-dialog-toggle-label").textContent = selected === "debug-button" ? "Enable debug diagnostics" : selected === "refresh-button" ? "Update status automatically" : "Use the Ark's internet connection on this device";
            }
            link.hidden = !(item.settings || item.url);
            link.href = item.settings || item.url || "#";
            link.textContent = item.settingsLabel || item.openLabel || "";
        }
        for (const [id,item] of Object.entries(items)) {
            const original = document.getElementById(id);
            original.setAttribute("aria-label", item.name + " details");
            original.setAttribute("aria-haspopup", "dialog");
            original.setAttribute("aria-controls", "status-dialog");
            original.addEventListener("click", event => {
                if (allowAction) return;
                event.preventDefault();
                event.stopImmediatePropagation();
                selected = id;
                render();
                if (!dialog.open) dialog.showModal();
                close.focus();
            }, true);
            new MutationObserver(render).observe(original, {attributes:true, attributeFilter:["title","class","data-action-disabled","aria-busy"], childList:true,subtree:true,characterData:true});
        }
        action.addEventListener("change", () => {
            if (!selected || action.disabled) return;
            pending = {id:selected, checked:action.checked};
            action.disabled = true;
            clearTimeout(pendingTimer);
            pendingTimer = setTimeout(() => { pending = null; render(); }, 5000);
            allowAction = true;
            try { document.getElementById(selected).click(); }
            finally { allowAction = false; }
        });
        close.addEventListener("click", () => dialog.close());
        dialog.addEventListener("close", () => {
            if (selected) document.getElementById(selected).focus();
        });
    });
})();
