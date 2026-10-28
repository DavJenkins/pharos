"use strict";
(() => {
    const el = id => document.getElementById(id);
    const panel = el("bugout-panel");
    if (!panel) return;
    let state = null, busy = false, polling = false, task = null, requestId = null, action = "trigger", cancelId = null, formVersion = 0;
    const start = el("bugout-start"), dialog = el("bugout-dialog");
    // Retain the UUID after an uncertain response; retries refer to the same operation.
    function operationId() {
        const bytes = crypto.getRandomValues(new Uint8Array(16));
        bytes[6] = (bytes[6] & 15) | 64;
        bytes[8] = (bytes[8] & 63) | 128;
        const hex = Array.from(bytes, x => x.toString(16).padStart(2,"0")).join("");
        return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
    }
    function localTime(value) {
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? "unknown time" : date.toLocaleString(undefined, {
            year:"numeric",month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZoneName:"short"
        });
    }
    function openForm(selected = null, requested = "trigger") {
        formVersion++;
        if (action !== requested) requestId = null;
        action = requested;
        cancelId = state?.operation?.id;
        task = selected;
        el("bugout-form").reset();
        el("bugout-form-result").textContent = "";
        el("bugout-credential-fields").hidden = !task;
        el("bugout-dialog-title").textContent = task ? "Credentials for " + task.title : action === "sync" ? "Sync household sources now" : action.startsWith("cancel") ? "Cancel bugout" : "Start household backup";
        el("bugout-submit").textContent = task ? "Save credentials" : action === "sync" ? "Sync now" : action === "cancel-continue" ? "Cancel and continue updates" : action === "cancel" ? "Cancel bugout" : "Start backup";
        dialog.showModal();
    }
    async function refresh() {
        if (polling) return;
        polling = true;
        try {
            const response = await fetch("/api/bugout/state", {cache:"no-store",signal:AbortSignal.timeout(40000)});
            if (!response.ok) throw new Error();
            state = await response.json();
            panel.hidden = !state.configured;
            start.disabled = busy || !state.ready;
            start.hidden = state.bugout_configured === false;
            if (el("bugout-sync")) el("bugout-sync").disabled = busy || !state.sync_ready;
            for (const id of ["bugout-stop","bugout-continue"]) {
                if (el(id)) {
                    el(id).hidden = !["queued","running"].includes(state.operation?.state);
                    el(id).disabled = busy;
                }
            }
            const failures = state.tasks.filter(t => t.cache && (t.cache.missing_file || ["failed","unavailable","interrupted"].includes(t.cache.state)));
            const warning = el("bugout-warning");
            if (warning) {
                warning.hidden = failures.length === 0;
                warning.textContent = failures.length ? "Backup needs attention: " + failures.map(t => t.title).join(", ") + ". Source availability does not mean the backup succeeded." : "";
            }
            const ready = state.tasks.filter(t => t.bugout_ready ?? t.ready).length;
            el("bugout-readiness").textContent = state.ready ? `${ready} of ${state.tasks.length} sources ready` : state.reason;
            start.title = state.ready ? "Copy ready household sources onto this Ark" : state.reason;
            const background = state.prefetch_operation;
            const op = state.operation;
            if (op?.id === requestId) requestId = null;
            el("bugout-operation").textContent = op ? `Backup ${op.state} · ${new Date(op.updated).toLocaleString()}` : "";
            if (background) el("bugout-operation").textContent += " · Background prefetch " + background.state + " (bugout takes priority)";
            if (state.home_assistant?.error) el("bugout-operation").textContent += " · " + state.home_assistant.error;
            const list = el("bugout-tasks");
            list.replaceChildren();
            state.tasks.forEach(item => {
                const row = document.createElement("li");
                const result = op?.results?.find(r => r.id === item.id);
                row.textContent = `${item.title}: ${item.reason} · Priority ${item.priority ?? 100} · ${item.prefetch ? "Normal sync: " + (item.normal_sync || "scheduled") : "No normal sync"}`;
                row.append(document.createTextNode(item.include_in_bugout === false ? " · Excluded from bugout" : " · Included in bugout"));
                const notice = document.createElement("span");
                notice.className = "manifest-upstream";
                notice.textContent = item.checked
                    ? `${item.ready ? "Source available" : "Source unavailable"} at last check · checked ${localTime(item.checked)}`
                    : "Source availability not checked";
                row.append(notice);
                const activeCopy = background?.results?.find(r => r.id === item.id);
                const localCopy = document.createElement("span");
                localCopy.className = "household-copy-status";
                localCopy.textContent = item.cache?.file ? "Prefetched copy available on this Ark" : "No completed prefetched copy on this Ark";
                if (activeCopy) {
                    localCopy.textContent += ` · Prefetch ${activeCopy.state}`;
                    if (activeCopy.bytes_written != null) localCopy.textContent += ` · ${(activeCopy.bytes_written / 1024**2).toFixed(1)} MiB received`;
                }
                row.append(localCopy);
                if (item.cache) {
                    const cache = item.cache;
                    if (cache.last_success) row.append(document.createTextNode(" · Last prefetched " + localTime(cache.last_success)));
                    if (cache.state !== "completed") row.append(document.createTextNode(" · Last prefetch attempt: " + cache.message + (cache.checked ? " · " + localTime(cache.checked) : "")));
                    if (cache.missing_file || ["failed","unavailable","interrupted"].includes(cache.state)) {
                        const problem = document.createElement("strong");
                        problem.className = "household-warning";
                        problem.textContent = cache.missing_file ? "Saved copy is missing." : "Backup unsuccessful: " + cache.message;
                        if (cache.failure_count) problem.textContent += ` · ${cache.failure_count} consecutive failed attempts`;
                        if (cache.next_attempt) problem.textContent += " · Next automatic attempt no earlier than " + localTime(cache.next_attempt);
                        if (cache.file) problem.textContent += " · Previous successful copy is still available.";
                        row.append(problem);
                    }
                    if (cache.file) {
                        const link = document.createElement("a");
                        link.href = "/library-files/bugout-backups/" + encodeURIComponent(cache.file);
                        link.textContent = " Download prefetched copy";
                        row.append(link);
                    }
                }
                if (result) {
                    row.append(document.createTextNode(` · Last operation: ${result.state} — ${result.message}`));
                    if (result.bytes_written != null) row.append(document.createTextNode(` (${(result.bytes_written / 1024**2).toFixed(1)} MiB)`));
                    if (result.state === "completed" && result.file) {
                        const link = document.createElement("a");
                        link.href = "/library-files/bugout-backups/" + encodeURIComponent(result.file);
                        link.textContent = " Download snapshot";
                        row.append(link);
                    }
                }
                if (item.credential_configured) {
                    const button = document.createElement("button");
                    button.type = "button"; button.textContent = item.credentials_saved ? "Update credentials" : "Set credentials";
                    button.disabled = busy || !!background || ["queued","running"].includes(op?.state);
                    button.addEventListener("click", () => openForm(item));
                    row.append(document.createTextNode(" "), button);
                }
                list.append(row);
            });
        } catch (_) {
            start.disabled = true;
            for (const id of ["bugout-sync","bugout-stop","bugout-continue"]) if (el(id)) el(id).disabled = true;
            if (!panel.hidden) el("bugout-readiness").textContent = "Unable to check backup readiness";
        } finally { polling = false; }
    }
    start.addEventListener("click", () => { if (!start.disabled) openForm(); });
    for (const [id, requested] of [["bugout-sync","sync"],["bugout-stop","cancel"],["bugout-continue","cancel-continue"]]) {
        el(id)?.addEventListener("click", () => { if (!el(id).disabled) openForm(null, requested); });
    }
    el("bugout-cancel").addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => { formVersion++; el("bugout-form").reset(); });
    el("bugout-form").addEventListener("input", () => {
        formVersion++;
        el("bugout-form-result").textContent = "";
    });
    el("bugout-test-credentials")?.addEventListener("click", async () => {
        if (busy || !task || !el("bugout-form").reportValidity()) return;
        const selected = task, version = formVersion;
        const button = el("bugout-test-credentials");
        const payload = {username:el("bugout-username").value,password:el("bugout-password").value,
            domain:el("bugout-domain").value,remember:el("bugout-remember").checked};
        busy = true; button.disabled = true; el("bugout-submit").disabled = true;
        el("bugout-form-result").textContent = "Testing share access…";
        try {
            const authorization = await window.CaretakerAuth.authorization("Authorize this bug-out action.");
            const response = await fetch("/api/bugout/credentials/" + encodeURIComponent(selected.id) + "/test", {
                method:"POST",cache:"no-store",signal:AbortSignal.timeout(15000),
                headers:{"Content-Type":"application/json","Authorization":authorization},body:JSON.stringify(payload)});
            window.CaretakerAuth.rejected(response);
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || "Credential test failed");
            if (version === formVersion) el("bugout-form-result").textContent = result.ok ? result.message : "Test failed: " + result.message;
        } catch (error) {
            if (version === formVersion) el("bugout-form-result").textContent = error.message || "Unable to test share access";
        } finally {
            busy = false; button.disabled = false; el("bugout-submit").disabled = false;
        }
    });
    el("bugout-form").addEventListener("submit", async event => {
        event.preventDefault();
        if (busy) return;
        busy = true; start.disabled = true; el("bugout-submit").disabled = true;
        const selected = task;
        if (!selected && !action.startsWith("cancel") && !requestId) requestId = operationId();
        const payload = selected ? {username:el("bugout-username").value,password:el("bugout-password").value,
            domain:el("bugout-domain").value,remember:el("bugout-remember").checked} : action.startsWith("cancel") ? {operation_id:cancelId,continue_updates:action === "cancel-continue"} : {operation_id:requestId};
        try {
            const authorization = await window.CaretakerAuth.authorization("Authorize this bug-out action.");
            const response = await fetch("/api/bugout/" + (selected ? "credentials/" + encodeURIComponent(selected.id) : action.startsWith("cancel") ? "cancel" : action), {
                method:"POST",cache:"no-store",signal:AbortSignal.timeout(45000),
                headers:{"Content-Type":"application/json","Authorization":authorization},body:JSON.stringify(payload)});
            window.CaretakerAuth.rejected(response);
            const value = await response.json();
            if (!response.ok) {
                if (response.status < 500) requestId = null;
                throw new Error(value.detail || "Backup request failed");
            }
            requestId = null;
            dialog.close();
        } catch (error) {
            el("bugout-form-result").textContent = error.message || "Unable to reach Ark; refresh status before retrying";
        } finally {
            el("bugout-admin").value = ""; el("bugout-password").value = "";
            busy = false; el("bugout-submit").disabled = false;
            await refresh();
        }
    });
    refresh();
    setInterval(() => { if (!document.hidden) refresh(); }, 15000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
})();
