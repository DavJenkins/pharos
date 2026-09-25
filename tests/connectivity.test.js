"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "../app/static/assets/js/connectivity.js"), "utf8");
function link(href) {
    const attrs = {href};
    return {getAttribute: key => attrs[key] ?? null, setAttribute: (key,value) => {attrs[key]=value;},
        removeAttribute: key => {delete attrs[key];}};
}
async function run() {
    const external = link("https://example.org/");
    const local = link("/library-files/book.pdf");
    const status = {textContent:"Ark online"};
    const context = {navigator: {onLine: false}, AbortController, setTimeout, clearTimeout,
        setInterval: () => {}, window: {addEventListener() {}},
        document: {hidden: false, querySelectorAll: () => [external], addEventListener() {},
            getElementById: id => id === "internet-status" ? status : null},
        fetch: async () => {throw new Error("offline");}};
    vm.createContext(context);
    vm.runInContext(source,context);
    const model = vm.runInContext("DataArkConnectivity",context);
    assert.equal(external.getAttribute("href"),null);
    assert.equal(external.getAttribute("aria-disabled"),"true");
    assert.equal(local.getAttribute("href"),"/library-files/book.pdf");
    context.navigator.onLine=true;
    let count=0;
    context.fetch=async (_,options) => {
        assert.equal(options.credentials,"omit");
        assert.equal(options.referrerPolicy,"no-referrer");
        if (++count===1) throw Error("first probe blocked");
        return {};
    };
    await model.check();
    assert.equal(count,2);
    assert.equal(external.getAttribute("href"),"https://example.org/");
    assert.equal(external.getAttribute("aria-disabled"),null);
    context.fetch=async () => {throw Error("no internet");};
    await model.check();
    assert.equal(external.getAttribute("href"),null);
    assert.equal(status.textContent,"Ark online", "Browser connectivity must not overwrite Ark status");
    let finish;
    context.fetch=() => new Promise(resolve => {finish=resolve;});
    const pending=model.check();
    context.navigator.onLine=false;
    await model.check();
    finish({});
    await pending;
    assert.equal(external.getAttribute("href"),null,"stale response must not reenable offline links");
    assert.equal(local.getAttribute("href"),"/library-files/book.pdf");
    console.log("Connectivity checks passed: offline, fallback, recovery, stale response, and local links.");
}
run().catch(error => {console.error(error);process.exitCode=1;});