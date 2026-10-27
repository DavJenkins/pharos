"use strict";
(() => {
    const items = {
        "eth-button": {name:"Ethernet", description:"The Ark's wired upstream connection. Disabling it preserves its configuration and leaves the DataArk hotspot available. A restart can reconnect it.", toggle:true},
        "wifi-button": {name:"Wi-Fi", description:"The Ark’s upstream Wi-Fi. Disabling it retains saved networks and leaves the DataArk hotspot available. A restart can reconnect it.", settings:"/config/wifi.html", settingsLabel:"Choose a Wi-Fi network", toggle:true},
        "ap-button": {name:"Hotspot", description:"The DataArk Wi-Fi network your devices join to use the Ark.", settings:"/config/system.html", settingsLabel:"Change hotspot settings", toggle:true},
        "portal-continue": {name:"Internet pass-through", description:"Allow this device to reach the internet through the Ark. This does not change access for other devices. Permission lasts up to six hours and resets when the Ark restarts.", toggle:true},
        "system-button": {name:"System", description:"The Ark's health, running time, connected devices, and library storage.", settings:"/library.html", settingsLabel:"Manage Library"},
        "refresh-button": {name:"Auto refresh", description:"Update the displayed dashboard status at your chosen interval. Pausing this does not stop the Ark's services.", toggle:true},
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
        const toggleRow = document.getElementById("status-dialog-toggle-row");
        const toggleHome = toggleRow.parentElement;
        const popupHeader = document.createElement("div");
        popupHeader.className = "status-dialog-heading-row";
        heading.before(popupHeader);
        popupHeader.append(heading);
        const switchTrack = document.createElement("span");
        switchTrack.className = "network-switch-track";
        switchTrack.setAttribute("aria-hidden", "true");
        switchTrack.hidden = true;
        action.after(switchTrack);
        const switchState = document.createElement("span");
        switchState.className = "network-switch-state";
        switchState.setAttribute("aria-hidden", "true");
        switchState.hidden = true;
        toggleRow.append(switchState);
        const intervalPanel = document.createElement("div");
        intervalPanel.className = "refresh-interval-panel";
        intervalPanel.hidden = true;
        const intervalLabel = document.createElement("label");
        intervalLabel.htmlFor = "status-refresh-interval";
        intervalLabel.textContent = "Refresh interval (seconds)";
        const intervalInput = document.createElement("input");
        intervalInput.id = "status-refresh-interval";
        intervalInput.type = "number";
        intervalInput.min = "5"; intervalInput.max = "300"; intervalInput.step = "1";
        intervalInput.inputMode = "numeric";
        intervalInput.setAttribute("aria-describedby", "status-refresh-interval-help");
        const intervalHelp = document.createElement("p");
        intervalHelp.id = "status-refresh-interval-help";
        intervalHelp.textContent = "5–300 seconds. Apply to save the interval for this browser.";
        const intervalApply = document.createElement("button");
        intervalApply.type = "button";
        intervalApply.textContent = "Apply interval";
        const intervalResult = document.createElement("p");
        intervalResult.className = "refresh-interval-result";
        intervalResult.setAttribute("role", "status");
        intervalPanel.append(intervalLabel, intervalInput, intervalApply, intervalHelp, intervalResult);
        description.after(intervalPanel);
        let intervalDirty = false;
        intervalInput.addEventListener("input", () => { intervalInput.setCustomValidity(""); intervalDirty = true; });
        function applyInterval() {
            try {
                Dashboard.setRefreshInterval(Number(intervalInput.value));
                intervalDirty = false;
                intervalInput.setCustomValidity("");
                intervalResult.textContent = Dashboard.refreshEnabled ? "Checking every " + Dashboard.refreshIntervalSeconds + " seconds." : "Saved. Checks resume at this interval when Auto refresh is on.";
            } catch (error) {
                intervalInput.setCustomValidity(error.message);
                intervalInput.reportValidity();
            }
        }
        intervalApply.addEventListener("click", applyInterval);
        intervalInput.addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); applyInterval(); } });
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
        const httpsLink = document.createElement("a");
        httpsLink.href = "/config/https.html";
        httpsLink.textContent = "Optional HTTPS";
        httpsLink.hidden = true;
        terminalLink.after(httpsLink);
        const bannerButton=document.createElement("button");
        bannerButton.id="status-banner-admin";bannerButton.type="button";bannerButton.textContent="Ark banner…";
        bannerButton.hidden=true;bannerButton.setAttribute("aria-haspopup","dialog");bannerButton.setAttribute("aria-controls","notice-dialog");
        terminalLink.before(bannerButton);
        bannerButton.addEventListener("click",()=>{dialog.close();window.ArkBannerAdmin.open();});


        const wifiMessage = document.createElement("p");
        wifiMessage.setAttribute("role", "status");
        wifiMessage.className = "wifi-action-message";
        document.getElementById("status-dialog-toggle-row").after(wifiMessage);
        const passwordDialog = document.createElement("dialog");
        passwordDialog.className = "caretaker-dialog";
        passwordDialog.innerHTML = '<form method="dialog"><h2>Caretaker password</h2><p>Authorize the network change.</p><label>Password<input type="password" name="password" autocomplete="off" required></label><label class="caretaker-remember-switch"><input type="checkbox" role="switch" name="remember"><span class="network-switch-track" aria-hidden="true"></span><span>Remember for 10 minutes</span></label><p class="dialog-actions"><button value="cancel" type="button">Cancel</button><button value="apply" type="submit">Apply</button></p></form>';
        document.body.append(passwordDialog);
        passwordDialog.querySelector('[value="cancel"]').addEventListener("click", () => passwordDialog.close("cancel"));
        let cachedPassword = null;
        let passwordExpires = 0;
        let passwordTimer;
        function forgetPassword() { cachedPassword = null; passwordExpires = 0; clearTimeout(passwordTimer); }
        function askPassword() {
            if (cachedPassword && Date.now() < passwordExpires) return Promise.resolve(cachedPassword);
            forgetPassword();
            const input = passwordDialog.querySelector("input");
            input.value = "";
            passwordDialog.querySelector("[name=remember]").checked = false;
            passwordDialog.returnValue = "cancel";
            return new Promise(resolve => {
                passwordDialog.addEventListener("close", () => {
                    const password = passwordDialog.returnValue === "apply" ? input.value : null;
                    if (password && passwordDialog.querySelector("[name=remember]").checked) {
                        cachedPassword = password;
                        passwordExpires = Date.now() + 600000;
                        passwordTimer = setTimeout(forgetPassword, 600000);
                    }
                    input.value = "";
                    resolve(password);
                }, {once:true});
                passwordDialog.showModal();
                input.focus();
            });
        }
        let access = {known:false, protected:[]};
        async function refreshAccess() {
            try { const response = await fetch("/api/network/admin/access", {cache:"no-store"});
                if (!response.ok) throw new Error(); access = await response.json();
            } catch (_) { access = {known:false, protected:[]}; }
            render();
        }
        let wifiBusy = false;
        let selected = null;
        let libraryInfo = null;
        let httpsInfo = null;
        let usageInfo = null;
        let libraryBusy = false;
        async function refreshLibrary(prefetch=false){
            if(libraryBusy||(!prefetch&&(selected!=="system-button"||!dialog.open)))return;
            libraryBusy=true;
            const controller=new AbortController();
            const timer=setTimeout(()=>controller.abort(),15000);
            try{
                const [response,httpsResponse,usageResponse]=await Promise.all([
                    fetch("/api/library",{cache:"no-store",signal:controller.signal}),
                    fetch("/api/https/status",{cache:"no-store",signal:controller.signal}).catch(()=>null),
                    fetch("/library-files/usage.json",{cache:"no-store",signal:controller.signal}).catch(()=>null)
                ]);
                if(httpsResponse?.ok)httpsInfo=await httpsResponse.json();
                if(usageResponse?.ok)usageInfo=await usageResponse.json();
                if(!response.ok)throw new Error("Library unavailable");
                libraryInfo=await response.json();
            }catch(_){if(!libraryInfo)libraryInfo={unavailable:true};}
            finally{clearTimeout(timer);libraryBusy=false;if(selected==="system-button"&&dialog.open)render();}
        }
        refreshLibrary(true);
        window.addEventListener("dataark:dashboard-refreshed", () => refreshLibrary());
        let allowAction = false;
        let pending = null;
        let pendingTimer = null;
        let systemTab="system";
        function renderDetails(item, title) {
            const focusedTab=document.activeElement?.getAttribute("role")==="tab"?document.activeElement.id:null;
            value.replaceChildren();
            const list = document.createElement("dl");
            list.className = "status-details-list";
            const lines = (title || "—").split("\n").map(line => line.trim()).filter(Boolean);
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
                const httpsLabel=document.createElement("dt"),httpsValue=document.createElement("dd");
                httpsLabel.textContent="HTTPS";
                httpsValue.textContent=!httpsInfo?"—":!httpsInfo.enabled?"Optional · Not configured":httpsInfo.certificate_health==="expired"?"Certificate expired · HTTP available":httpsInfo.domain+(httpsInfo.days_remaining!==undefined?" · "+httpsInfo.days_remaining+" days remaining":"");
                list.append(httpsLabel,httpsValue);
                const tabs=document.createElement("div");tabs.className="system-tabs";tabs.setAttribute("role","tablist");tabs.setAttribute("aria-label","System information");
                const systemPanel=document.createElement("div"),devicesPanel=document.createElement("div"),libraryPanel=document.createElement("div");
                systemPanel.append(list);
                const panels=[systemPanel,devicesPanel,libraryPanel],keys=["system","devices","library"],labels=["System","Connected devices","Library"],buttons=[];
                function selectTab(index,focus=false){
                    systemTab=keys[index];
                    panels.forEach((panel,i)=>{panel.hidden=i!==index;buttons[i].setAttribute("aria-selected",String(i===index));buttons[i].tabIndex=i===index?0:-1;});
                    if(focus)buttons[index].focus();
                }
                panels.forEach((panel,i)=>{
                    panel.id="system-panel-"+keys[i];panel.setAttribute("role","tabpanel");panel.setAttribute("aria-labelledby","system-tab-"+keys[i]);
                    const button=document.createElement("button");button.type="button";button.id="system-tab-"+keys[i];button.textContent=labels[i];button.setAttribute("role","tab");button.setAttribute("aria-controls",panel.id);buttons.push(button);tabs.append(button);
                    button.addEventListener("click",()=>selectTab(i));
                    button.addEventListener("keydown",event=>{let next;if(event.key==="ArrowRight")next=(i+1)%3;else if(event.key==="ArrowLeft")next=(i+2)%3;else if(event.key==="Home")next=0;else if(event.key==="End")next=2;else return;event.preventDefault();selectTab(next,true);});
                });
                value.append(tabs,...panels);
                const clientsHeading=document.createElement("h3");clientsHeading.className="library-summary-heading";clientsHeading.textContent="Connected devices";devicesPanel.append(clientsHeading);
                const clientsList=document.createElement("dl");clientsList.className="status-details-list";
                const clientsLabel=document.createElement("dt"),clientsValue=document.createElement("dd");
                clientsLabel.textContent="Hotspot";
                const ap=DataArkStatus.accessPoint;
                clientsValue.textContent=ap.active===false?"Off":ap.active!==true||!Number.isInteger(ap.client_count)?"—":ap.client_count+" connected "+(ap.client_count===1?"device":"devices");
                clientsList.append(clientsLabel,clientsValue);devicesPanel.append(clientsList);
                const clientsNote=document.createElement("p");clientsNote.className="status-details-note";clientsNote.textContent="Live hotspot connections, not a count of people. Other LAN devices are not counted; remote-access connection totals are on the Usage page.";devicesPanel.append(clientsNote);
                if(usageInfo){
                    const mini=document.createElement("div");mini.style.cssText="display:flex;align-items:end;gap:5px;height:52px;margin:12px 0";mini.setAttribute("role","img");mini.setAttribute("aria-label","Document requests over seven days; UTC daily buckets");
                    const days=[];for(let i=6;i>=0;i--){const date=new Date();date.setUTCDate(date.getUTCDate()-i);const key=date.toISOString().slice(0,10);days.push([key,usageInfo.daily[key]]);}
                    const max=Math.max(1,...days.map(([,v])=>v?.opens||0));
                    for(const [day,bucket] of days){const bar=document.createElement("span");bar.style.cssText="flex:1;background:#315b78;border-radius:3px 3px 0 0;height:"+(bucket?Math.max(2,bucket.opens/max*48):2)+"px";bar.title=day+": "+(bucket?bucket.opens+" document requests":"No observations");mini.append(bar);}devicesPanel.append(mini);
                    if(usageInfo.all_time){const total=document.createElement("p");total.textContent="Estimated visitors, all time: "+usageInfo.all_time.estimated_visitors;total.title="Since "+new Date(usageInfo.all_time.started_at).toLocaleString()+"; counts client addresses, not identified people";devicesPanel.append(total);}
                    const today=days[6][1],note=document.createElement("p");note.textContent="Today (UTC): "+(today?(today.unique_visitors??"—")+" estimated visitors · "+today.opens+" document requests · peak "+(today.hotspot_peak??"—")+" hotspot devices":"—");devicesPanel.append(note);
                }
                const usageLink=document.createElement("a");usageLink.href="/usage.html";usageLink.textContent="Usage history and seven-day chart";const usageRow=document.createElement("p");usageRow.append(usageLink);devicesPanel.append(usageRow);
                const title=document.createElement("h3");title.className="library-summary-heading";title.textContent="Library";libraryPanel.append(title);
                const summary=document.createElement("dl");summary.className="status-details-list";
                const row=(label,text)=>{const dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=label;dd.textContent=text;summary.append(dt,dd);};
                const gib=n=>(n/1024**3).toFixed(1)+" GiB";
                if(!libraryInfo || libraryInfo.unavailable){
                    for(const label of ["Installed","Pending","Not installed","Storage","Activity"])row(label,"—");
                }
                else{
                    row("Installed",libraryInfo.installed.length+(libraryInfo.installed.length===1?" registered item":" registered items"));
                    row("Pending",libraryInfo.pending.length+(libraryInfo.pending.length===1?" download":" downloads"));
                    row("Not installed",libraryInfo.removed.length+(libraryInfo.removed.length===1?" removed item":" removed items"));
                    row("Storage",libraryInfo.storage_ready?gib(libraryInfo.free_bytes)+" free of "+gib(libraryInfo.total_bytes):"Content SSD not mounted");
                    row("Activity",libraryInfo.progress?.label||"—");
                    if(libraryInfo.progress?.detail)row("Details",libraryInfo.progress.detail);
                }
                libraryPanel.append(summary);
                selectTab(Math.max(0,keys.indexOf(systemTab)));
                if(focusedTab)document.getElementById(focusedTab)?.focus({preventScroll:true});
            }
        }
        function render() {
            if (!selected) return;
            const item = items[selected], original = document.getElementById(selected);
            heading.textContent = item.name;
            const networkSwitch = !!item.toggle;
            dialog.classList.toggle("network-popup", networkSwitch);
            toggleRow.classList.toggle("network-enable-switch", networkSwitch);
            const toggleParent = networkSwitch ? popupHeader : toggleHome;
            if (toggleRow.parentElement !== toggleParent) {
                if (networkSwitch) toggleParent.append(toggleRow);
                else toggleParent.prepend(toggleRow);
            }
            switchTrack.hidden = !networkSwitch;
            switchState.hidden = !networkSwitch;
            if (networkSwitch) action.setAttribute("role", "switch");
            else action.removeAttribute("role");
            description.textContent = selected === "refresh-button" ? "Update the displayed dashboard status every " + Dashboard.refreshIntervalSeconds + " seconds. Pausing this does not stop the Ark's services." : item.description;
            intervalPanel.hidden = selected !== "refresh-button";
            if (selected === "refresh-button" && !intervalDirty && document.activeElement !== intervalInput) intervalInput.value = String(Dashboard.refreshIntervalSeconds);
            if (selected === "refresh-button" && intervalResult.textContent) intervalResult.textContent = Dashboard.refreshEnabled ? "Checking every " + Dashboard.refreshIntervalSeconds + " seconds." : "Paused. Checks resume at this interval when Auto refresh is on.";
            renderDetails(item, original.title);
            value.hidden = !!item.url || (!!item.toggle && !["wifi-button", "eth-button", "ap-button"].includes(selected));
            wifiMessage.hidden = !["wifi-button", "eth-button", "ap-button"].includes(selected);
            document.getElementById("status-dialog-toggle-row").hidden = !item.toggle;
            if (item.toggle) {
                const enabled = ["wifi-button", "eth-button", "ap-button"].includes(selected) ? ((selected === "ap-button" ? DataArkStatus.accessPoint : selected === "eth-button" ? DataArkStatus.ethernet : DataArkStatus.wifi).enabled ?? (selected === "ap-button" ? DataArkStatus.accessPoint.active : selected === "eth-button" ? DataArkStatus.ethernet.connected : DataArkStatus.wifi.connected)) === true : original.classList.contains("on");
                const unavailable = original.getAttribute("data-action-disabled") === "true" || original.classList.contains("error");
                if (pending && pending.id === selected && enabled === pending.checked) {
                    pending = null;
                    clearTimeout(pendingTimer);
                }
                const interfaceName = {"ap-button":"wlan0", "wifi-button":"wlan1", "eth-button":"eth0"}[selected];
                const protectedPath = interfaceName && enabled && (!access.known || access.protected.includes(interfaceName));
                if (interfaceName && !wifiBusy && protectedPath) wifiMessage.textContent = protectedPath ? (access.known ? "This is your current access path. Connect through another interface to disable it." : "Checking your access path; disabling is blocked until it can be verified.") : "";
                if (interfaceName && !wifiBusy && !protectedPath && (wifiMessage.textContent.startsWith("Checking your access path") || wifiMessage.textContent.startsWith("This is your current access path"))) wifiMessage.textContent = "";
                action.disabled = !!protectedPath || wifiBusy || unavailable || original.getAttribute("aria-busy") === "true" || !!pending;
                action.checked = pending && pending.id === selected ? pending.checked : enabled;
                switchState.textContent = action.checked ? "On" : "Off";
                document.getElementById("status-dialog-toggle-label").textContent = selected === "ap-button" ? "Enable hotspot" : selected === "eth-button" ? "Enable Ethernet" : selected === "wifi-button" ? "Enable upstream Wi-Fi" : selected === "debug-button" ? "Enable debug diagnostics" : selected === "refresh-button" ? "Update status automatically" : "Use the Ark's internet connection on this device";
            }
            terminalLink.hidden = selected !== "system-button";
            httpsLink.hidden = selected !== "system-button";
            bannerButton.hidden = selected !== "system-button" || !window.ArkBannerAdmin;
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
                if (selected !== id) wifiMessage.textContent = "";
                selected = id;
                render();
                if (["ap-button","wifi-button","eth-button"].includes(id)) refreshAccess();
                if (!dialog.open) dialog.showModal();
                if(id==="system-button")refreshLibrary();
                close.focus();
            }, true);
            new MutationObserver(render).observe(original, {attributes:true, attributeFilter:["title","class","data-action-disabled","aria-busy"], childList:true,subtree:true,characterData:true});
        }
        action.addEventListener("change", async () => {
            if (!selected || action.disabled) return;
            if (["wifi-button", "eth-button", "ap-button"].includes(selected)) {
                const wired = selected === "eth-button";
                const hotspot = selected === "ap-button";
                const networkName = hotspot ? "hotspot" : wired ? "Ethernet" : "upstream Wi-Fi";
                const enabled = action.checked;
                switchState.textContent = enabled ? "On" : "Off";
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
                        response = await fetch("/api/network/admin/" + (hotspot ? "hotspot" : wired ? "ethernet" : "uplink"), {
                            method:"POST", cache:"no-store", signal:controller.signal,
                            headers:{"Content-Type":"application/json", "Authorization":"Basic " + btoa(Array.from(bytes, b => String.fromCharCode(b)).join(""))},
                            body:JSON.stringify({enabled})
                        });
                    } finally { clearTimeout(timeout); }
                    const result = await response.json();
                    if (response.status === 401) forgetPassword();
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
            intervalDirty = false;
            intervalResult.textContent = "";
            if (selected) document.getElementById(selected).focus();
        });
    });
})();
