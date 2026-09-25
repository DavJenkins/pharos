"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname,"../app/static/assets/js/portal.js"),"utf8");
async function scenario(hostname, state, postOk = true) {
    const calls = [];
    const box = {hidden:true};
    const message = {textContent:"Welcome"};
    const button = {disabled:false, hidden:false, addEventListener: (_,fn) => button.click=fn};
    const elements = {"portal-welcome":box,"portal-continue":button,"portal-message":message};
    await vm.runInNewContext(source, {
        location:{hostname}, document:{getElementById:id=>elements[id]},
        fetch:async (url,options) => {
            calls.push([url,options]);
            if (url.endsWith("/state")) return {ok:state !== null,json:async()=>state};
            return {ok:postOk};
        }
    });
    return {calls,box,button,message};
}
(async () => {
    const lan = await scenario("192.168.40.123",false);
    assert.equal(lan.calls.length,0);
    assert.equal(lan.box.hidden,true);
    assert.equal((await scenario("192.168.4.1",true)).box.hidden,true);
    assert.equal((await scenario("192.168.4.1",null)).box.hidden,true);
    const ap = await scenario("192.168.4.1",false);
    assert.equal(ap.box.hidden,false);
    assert.equal(ap.calls.length,1); // Viewing the page does not acknowledge automatically.
    await ap.button.click();
    assert.equal(ap.calls[1][1].method,"POST");
    assert.equal(ap.button.hidden,true);
    assert.match(ap.message.textContent,/Bookmark/);
    const failed = await scenario("192.168.4.1",false,false);
    await failed.button.click();
    assert.equal(failed.button.disabled,false);
    assert.equal(failed.button.hidden,false);
    assert.match(failed.message.textContent,/try again/);
    console.log("Portal UI checks passed: LAN, acknowledged, unavailable, continue, and retry.");
})().catch(error => {console.error(error);process.exitCode=1;});
