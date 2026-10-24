"use strict";
(() => {
    const items = {
        "eth-button": {name:"Ethernet", description:"The Ark's wired upstream connection. Disabling it preserves its configuration and leaves the DataArk hotspot available. A restart can reconnect it.", toggle:true},
        "wifi-button": {name:"Wi-Fi", description:"The Ark’s upstream Wi-Fi. Disabling it retains saved networks and leaves the DataArk hotspot available. A restart can reconnect it.", settings:"/config/wifi.html", settingsLabel:"Choose a Wi-Fi network", toggle:true},
        "ap-button": {name:"Hotspot", description:"The DataArk Wi-Fi network your devices join to use the Ark.", settings:"/config/system.html", settingsLabel:"Change hotspot settings"},
        "portal-continue": {name:"Internet pass-through", description:"Allow this device to reach the internet through the Ark. This does not change access for other devices. Permission lasts up to six hours and resets when the Ark restarts.", toggle:true},
        "system-button": {name:"System", description:"The Ark's health, running time, and library storage.", settings:"/library.html", settingsLabel:"Manage Library"},
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
        const terminalLink = document.createElement("a");
        terminalLink.textContent = "Terminal";
        terminalLink.hidden = true;
        terminalLink.target = "_blank";
        terminalLink.rel = "noopener noreferrer";
        const terminalUrl = new URL(window.location.href);
        terminalUrl.protocol = "https:";
        terminalUrl.port = "4200";
        terminalUrl.pathname = "/";
        terminalUrl.search = "";
        terminalUrl.hash = "";
        terminalLink.href = terminalUrl.href;
        terminalLink.title = "Linux admin login required";
        link.after(terminalLink);

        const wifiMessage = document.createElement("p");
        wifiMessage.setAttribute("role", "status");
        wifiMessage.className = "wifi-action-message";
        document.getElementById("status-dialog-toggle-row").after(wifiMessage);
        const passwordDialog = document.createElement("dialog");
        passwordDialog.className = "caretaker-dialog";
        passwordDialog.innerHTML = '<form method="dialog"><h2>Caretaker password</h2><p>Authorize the network change.</p><label>Password<input type="password" name="password" autocomplete="off" required></label><p class="dialog-actions"><button value="cancel" type="button">Cancel</button><button value="apply" type="submit">Apply</button></p></form>';
        document.body.append(passwordDialog);
        passwordDialog.querySelector('[value="cancel"]').addEventListener("click", () => passwordDialog.close("cancel"));
        function askPassword() {
            const input = passwordDialog.querySelector("input");
            input.value = "";
            passwordDialog.returnValue = "cancel";
            return new Promise(resolve => {
                passwordDialog.addEventListener("close", () => {
                    const password = passwordDialog.returnValue === "apply" ? input.value : null;
                    input.value = "";
                    resolve(password);
                }, {once:true});
                passwordDialog.showModal();
                input.focus();
            });
        }
        let wifiBusy = false;
        let selected = null;
        let libraryInfo = null;
        let libraryBusy = false;
        async function refreshLibrary(){
            if(libraryBusy||selected!=="system-button"||!dialog.open)return;
            libraryBusy=true;
            const controller=new AbortController();
            const timer=setTimeout(()=>controller.abort(),6000);
            try{
                const response=await fetch("/api/library",{cache:"no-store",signal:controller.signal});
                if(!response.ok)throw new Error("Library unavailable");
                libraryInfo=await response.json();
            }catch(_){libraryInfo={unavailable:true};}
            finally{clearTimeout(timer);libraryBusy=false;if(selected==="system-button"&&dialog.open)render();}
        }
        setInterval(refreshLibrary,5000);
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
            if(selected==="system-button"){
                const title=document.createElement("h3");title.className="library-summary-heading";title.textContent="Library";value.append(title);
                const summary=document.createElement("dl");summary.className="status-details-list";
                const row=(label,text)=>{const dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=label;dd.textContent=text;summary.append(dt,dd);};
                const gib=n=>(n/1024**3).toFixed(1)+" GiB";
                if(!libraryInfo){row("Status","Loading…");}
                else if(libraryInfo.unavailable){row("Status","Unavailable — reconnect and reopen System.");}
                else{
                    row("Installed",libraryInfo.installed.length+(libraryInfo.installed.length===1?" registered item":" registered items"));
                    row("Pending",libraryInfo.pending.length+(libraryInfo.pending.length===1?" download":" downloads"));
                    row("Not installed",libraryInfo.removed.length+(libraryInfo.removed.length===1?" removed item":" removed items"));
                    row("Storage",libraryInfo.storage_ready?gib(libraryInfo.free_bytes)+" free of "+gib(libraryInfo.total_bytes):"Content SSD not mounted");
                    row("Activity",libraryInfo.progress?.label||"Unavailable");
                    if(libraryInfo.progress?.detail)row("Details",libraryInfo.progress.detail);
                }
                value.append(summary);
            }
        }
        function render() {
            if (!selected) return;
            const item = items[selected], original = document.getElementById(selected);
            heading.textContent = item.name;
            description.textContent = item.description;
            renderDetails(item, original.title);
            value.hidden = !!item.url || (!!item.toggle && !["wifi-button", "eth-button"].includes(selected));
            wifiMessage.hidden = !["wifi-button", "eth-button"].includes(selected);
            document.getElementById("status-dialog-toggle-row").hidden = !item.toggle;
            if (item.toggle) {
                const enabled = ["wifi-button", "eth-button"].includes(selected) ? ((selected === "eth-button" ? DataArkStatus.ethernet : DataArkStatus.wifi).enabled ?? (selected === "eth-button" ? DataArkStatus.ethernet : DataArkStatus.wifi).connected) === true : original.classList.contains("on");
                const unavailable = original.getAttribute("data-action-disabled") === "true" || original.classList.contains("error");
                if (pending && pending.id === selected && enabled === pending.checked) {
                    pending = null;
                    clearTimeout(pendingTimer);
                }
                action.disabled = wifiBusy || unavailable || original.getAttribute("aria-busy") === "true" || !!pending;
                action.checked = pending && pending.id === selected ? pending.checked : enabled;
                document.getElementById("status-dialog-toggle-label").textContent = selected === "eth-button" ? "Enable Ethernet" : selected === "wifi-button" ? "Enable upstream Wi-Fi" : selected === "debug-button" ? "Enable debug diagnostics" : selected === "refresh-button" ? "Update status automatically" : "Use the Ark's internet connection on this device";
            }
            terminalLink.hidden = selected !== "system-button";
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
                if(id==="system-button")refreshLibrary();
                close.focus();
            }, true);
            new MutationObserver(render).observe(original, {attributes:true, attributeFilter:["title","class","data-action-disabled","aria-busy"], childList:true,subtree:true,characterData:true});
        }
        action.addEventListener("change", async () => {
            if (!selected || action.disabled) return;
            if (["wifi-button", "eth-button"].includes(selected)) {
                const wired = selected === "eth-button";
                const networkName = wired ? "Ethernet" : "upstream Wi-Fi";
                const enabled = action.checked;
                wifiBusy = true;
                action.disabled = true;
                try {
                    const password = await askPassword();
                    if (password === null) return;
                    wifiMessage.textContent = (enabled ? "Connecting " : "Disconnecting ") + networkName + "…";
                    const controller = new AbortController();
                    const timeout = setTimeout(() => controller.abort(), 45000);
                    let response;
                    try {
                        const bytes = new TextEncoder().encode("admin:" + password);
                        response = await fetch("/api/network/admin/" + (wired ? "ethernet" : "uplink"), {
                            method:"POST", cache:"no-store", signal:controller.signal,
                            headers:{"Content-Type":"application/json", "Authorization":"Basic " + btoa(Array.from(bytes, b => String.fromCharCode(b)).join(""))},
                            body:JSON.stringify({enabled})
                        });
                    } finally { clearTimeout(timeout); }
                    const result = await response.json();
                    if (!response.ok) throw new Error(response.status === 401 ? "Incorrect caretaker password. The connection was not changed." : result.detail || "Network change failed.");
                    wifiMessage.textContent = result.message;
                    await DataArkStatus.refresh();
                } catch (error) {
                    wifiMessage.textContent = error.name === "AbortError" || error instanceof TypeError ? "Connection lost. Reopen the dashboard at http://192.168.4.1 and check connection status." : error.message;
                } finally { wifiBusy = false; render(); }
                return;
            }
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
