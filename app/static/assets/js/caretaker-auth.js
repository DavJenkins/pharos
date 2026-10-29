/* One on-demand caretaker prompt. Opt-in credentials expire at a fixed time. */
(() => {
    "use strict";
    const key = "dataark.caretaker.session.v1";
    let memory = null, pending = null, dialog, expiryTimer, indicator, indicatorTimer, floatingLock;
    function forget() {
        memory = null; clearTimeout(expiryTimer);
        try { sessionStorage.removeItem(key); } catch (_) {}
        window.dispatchEvent(new Event("caretaker-auth-changed"));
    }
    function cached() {
        try {
            const record = memory || JSON.parse(sessionStorage.getItem(key) || "null");
            if (record && typeof record.password === "string" && Number.isFinite(record.until) && record.until > Date.now() && record.until <= Date.now()+120*60000) {
                memory = record;
                clearTimeout(expiryTimer); expiryTimer = setTimeout(forget, Math.max(1,record.until-Date.now()));
                return record;
            }
        } catch (_) {}
        memory = null;
        try { sessionStorage.removeItem(key); } catch (_) {}
        return null;
    }
    function refreshIndicator() {
        clearTimeout(indicatorTimer);
        const record = cached();
        if (!record) { if (indicator) indicator.hidden = true; if (floatingLock) floatingLock.hidden = true; return; }
        if (!indicator) {
            indicator = document.createElement("div");
            indicator.id = "caretaker-auth-status";
            indicator.setAttribute("aria-label", "Cached caretaker authorization");
            indicator.innerHTML = '<span id="caretaker-auth-remaining"></span><button type="button" id="caretaker-auth-lock">Lock now</button>';
            indicator.querySelector("#caretaker-auth-lock").onclick = forget;
            const popupDescription = document.querySelector("#status-dialog-description");
            const nav = document.querySelector("main nav");
            if (popupDescription) popupDescription.insertAdjacentElement("afterend", indicator);
            else if (nav) nav.insertAdjacentElement("afterend", indicator);
            else (document.querySelector("main") || document.body).prepend(indicator);
        }
        if (!floatingLock) {
            floatingLock = document.createElement("button");
            floatingLock.id = "caretaker-auth-floating-lock";
            floatingLock.type = "button";
            floatingLock.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="11" width="16" height="11" rx="2"/><path d="M8 11V6a4 4 0 0 1 8 0"/><path d="M12 15v3"/></svg>';
            floatingLock.onclick = forget;
            document.body.append(floatingLock);
        }
        const remaining = Math.max(1, Math.ceil((record.until-Date.now())/60000));
        indicator.querySelector("#caretaker-auth-remaining").textContent = "Caretaker unlocked · "+remaining+" min remaining";
        indicator.hidden = false;
        floatingLock.hidden = false;
        floatingLock.title = "Caretaker unlocked · "+remaining+" min remaining. Lock now.";
        floatingLock.setAttribute("aria-label", floatingLock.title);
        indicatorTimer = setTimeout(refreshIndicator, Math.min(15000, Math.max(1,record.until-Date.now())));
    }
    function basic(password) {
        return "Basic " + btoa(Array.from(new TextEncoder().encode("admin:"+password), b => String.fromCharCode(b)).join(""));
    }
    function makeDialog() {
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "caretaker-auth-dialog";
        dialog.setAttribute("aria-labelledby", "caretaker-auth-title");
        dialog.innerHTML = '<form><h2 id="caretaker-auth-title">Caretaker password</h2><p id="caretaker-auth-purpose"></p><label for="caretaker-auth-password">Password</label><input id="caretaker-auth-password" type="password" autocomplete="current-password" maxlength="256" required><div class="caretaker-auth-remember"><label class="caretaker-auth-switch"><input id="caretaker-auth-remember" type="checkbox" role="switch"><span aria-hidden="true" class="caretaker-auth-track"></span><span>Don’t prompt again for</span></label><label class="caretaker-auth-duration"><input id="caretaker-auth-minutes" type="number" min="1" max="120" step="1" value="10" aria-label="Remember caretaker password for minutes" disabled> minutes</label></div><p class="caretaker-auth-scope">Applies to this browser tab on this Ark address. Leaving the switch off authorizes only this action.</p><p id="caretaker-auth-error" role="status" aria-live="polite"></p><div class="caretaker-auth-actions"><button type="submit">Continue</button><button type="button" id="caretaker-auth-close">Close</button></div></form>';
        document.body.append(dialog);
        return dialog;
    }
    async function password(purpose = "Authorize this caretaker action.") {
        const saved = cached();
        if (saved) return saved.password;
        if (pending) return pending;
        const popup = makeDialog(), form = popup.querySelector("form");
        const input = popup.querySelector("#caretaker-auth-password");
        const remember = popup.querySelector("#caretaker-auth-remember");
        const minutes = popup.querySelector("#caretaker-auth-minutes");
        const error = popup.querySelector("#caretaker-auth-error");
        const submit = form.querySelector('[type="submit"]');
        popup.querySelector("#caretaker-auth-purpose").textContent = purpose;
        form.reset(); popup.querySelectorAll("button").forEach(button => button.disabled = false); input.value = ""; minutes.disabled = true; error.textContent = "";
        pending = new Promise((resolve, reject) => {
            let accepted = false, checking = false;
            remember.onchange = () => { minutes.disabled = !remember.checked; };
            popup.querySelector("#caretaker-auth-close").onclick = () => popup.close();
            let controller = new AbortController();
            form.onsubmit = async event => {
                event.preventDefault();
                if (checking || !form.reportValidity()) return;
                controller = new AbortController();
                checking = true; submit.disabled = true; error.textContent = "Checking password…";
                const candidate = input.value;
                const timeout = setTimeout(() => controller.abort(),15000);
                try {
                    const response = await fetch("/api/library/unlock", {method:"POST", cache:"no-store", signal:controller.signal, headers:{Authorization:basic(candidate)}});
                    if (!response.ok) {
                        if (response.status === 401) { forget(); throw new Error("Password not accepted. Try again."); }
                        throw new Error("The Ark could not verify the password. Please try again.");
                    }
                    if (!popup.open) return;
                    if (remember.checked) {
                        const duration = Number(minutes.value);
                        if (!Number.isInteger(duration) || duration < 1 || duration > 120) throw new Error("Choose a whole number from 1 to 120 minutes.");
                        memory = {password:candidate, until:Date.now()+duration*60000};
                        try { sessionStorage.setItem(key, JSON.stringify(memory)); } catch (_) {}
                        clearTimeout(expiryTimer); expiryTimer = setTimeout(forget, duration*60000);
                        window.dispatchEvent(new Event("caretaker-auth-changed"));
                    }
                    accepted = true;
                    popup.close();
                    resolve(candidate);
                } catch (failure) {
                    if (popup.open) { error.textContent = failure.name === "AbortError" ? "Password check cancelled." : failure.message; input.focus(); input.select(); }
                } finally { clearTimeout(timeout); checking = false; submit.disabled = false; }
            };
            popup.addEventListener("close", () => {
                controller.abort(); input.value = ""; form.onsubmit = null;
                if (!accepted) { const failure = new Error("Action cancelled."); failure.name = "AbortError"; reject(failure); }
            }, {once:true});
            popup.showModal(); input.focus();
        });
        try { return await pending; } finally { pending = null; }
    }
    window.addEventListener("caretaker-auth-changed", refreshIndicator);
    window.addEventListener("pageshow", refreshIndicator);
    window.addEventListener("focus", refreshIndicator);
    refreshIndicator();
    window.CaretakerAuth = Object.freeze({password, authorization:async purpose => basic(await password(purpose)),
        cachedAuthorization:() => { const value = cached(); return value ? basic(value.password) : null; },
        isRemembered:() => !!cached(), forget,
        rejected:response => { if (response.status === 401) forget(); return response; }});
})();
