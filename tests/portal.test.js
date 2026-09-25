"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname,"../app/static/assets/js/portal.js"),"utf8");
async function scenario(hostname, enabled, online, postOk=true, available=true) {
    const calls=[];
    const box={hidden:true};
    const message={textContent:""};
    const indicator={textContent:"--"};
    const attrs={};
    const button={classList:{toggle(){},remove(){},add(){}},disabled:false, hidden:false, setAttribute:(key,value)=>attrs[key]=value,
        removeAttribute:key=>delete attrs[key],addEventListener:(_,fn)=>button.click=fn};
    const elements={"portal-welcome":box,"portal-continue":button,"portal-message":message,"portal-state":indicator};
    const state={enabled,upstream_online:online};
    const timers=[];
    let checks=0;
    await vm.runInNewContext(source,{
        location:{hostname},document:{hidden:false,getElementById:id=>elements[id],addEventListener:()=>{}},
        setInterval:fn=>timers.push(fn),DataArkConnectivity:{check:()=>checks++},
        fetch:async (url,options)=>{
            calls.push([url,options]);
            if(url.endsWith('/state')) return {ok:available,json:async()=>({...state})};
            if(postOk) state.enabled=url.endsWith('/on');
            return {ok:postOk};
        }
    });
    return {calls,box,button,message,indicator,attrs,state,timers,checks:()=>checks};
}
(async()=>{
    const lan=await scenario('192.168.40.123',false,true);
    assert.equal(lan.calls.length,0);
    assert.equal(lan.box.hidden,true);
    const ap=await scenario('192.168.4.1',false,true);
    assert.equal(ap.indicator.textContent,"OFF");
    assert.equal(ap.attrs['aria-pressed'],'false');
    assert.equal(ap.attrs["aria-disabled"],"false");
    assert.match(ap.message.textContent,/Ark is online/);
    await ap.button.click();
    assert.equal(ap.calls[1][0],'/api/portal/pass-through/on');
    assert.equal(ap.attrs['aria-pressed'],'true');
    assert.equal(ap.button.hidden,false);
    await ap.button.click();
    assert.equal(ap.attrs['aria-pressed'],'false');
    assert.equal(ap.checks(),2);
    const offline=await scenario('192.168.4.1',false,false);
    assert.equal(offline.attrs["aria-disabled"],"true");
    const offlineOn=await scenario('192.168.4.1',true,false);
    assert.equal(offlineOn.attrs["aria-disabled"],"false"); // Turning off must always remain possible.
    await offlineOn.button.click();
    assert.equal(offlineOn.attrs['aria-pressed'],'false');
    const failed=await scenario('192.168.4.1',false,true,false);
    await failed.button.click();
    assert.equal(failed.attrs['aria-pressed'],'false');
    assert.match(failed.message.textContent,/Could not confirm/);
    const unavailable=await scenario('192.168.4.1',false,true,true,false);
    assert.equal(unavailable.attrs["aria-disabled"],"true");
    assert.equal(unavailable.attrs['aria-pressed'],undefined);
    assert.equal(unavailable.indicator.textContent,"?");
    console.log('Pass-through UI checks passed: default off, toggle both ways, offline, failure, and LAN isolation.');
})().catch(error=>{console.error(error);process.exitCode=1;});
