import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const script=fs.readFileSync(new URL('../app/static/assets/js/dashboard.js',import.meta.url),'utf8');
function setup(stored){
    const scheduled=[],cancelled=[],saved=[];
    const button={classList:{remove(){},toggle(){}},setAttribute(){},title:''};
    const context={window:{addEventListener(){}},document:{getElementById(){return button;}},
        localStorage:{getItem(){return stored;},setItem(k,v){saved.push([k,v]);}},
        setInterval(fn,ms){scheduled.push(ms);return scheduled.length;},clearInterval(id){cancelled.push(id);},console};
    vm.createContext(context);vm.runInContext(script+';this.subject=Dashboard;',context);
    return {d:context.subject,scheduled,cancelled,saved,button};
}
test('stored interval sets the real timer and hover label',()=>{
    const {d,scheduled,button}=setup('30');d.loadRefreshInterval();d.startTimer();d.updateRefreshButton();
    assert.deepEqual(scheduled,[30000]);assert.match(button.title,/30 seconds/);
});
test('changing an active interval cancels and replaces its timer',()=>{
    const {d,scheduled,cancelled,saved}=setup();d.startTimer();d.setRefreshInterval(12);
    assert.deepEqual(scheduled,[5000,12000]);assert.deepEqual(cancelled,[1]);assert.equal(saved[0][1],'12');
});
test('changing interval while paused saves it without restarting polling',()=>{
    const {d,scheduled}=setup();d.refreshEnabled=false;d.setRefreshInterval(60);assert.deepEqual(scheduled,[]);
    d.toggleRefresh();assert.deepEqual(scheduled,[60000]);
});
test('invalid intervals do not change or persist the active setting',()=>{
    const {d,scheduled,saved}=setup();
    for(const value of [0,1,4,301,5.5,NaN,Infinity,'30'])assert.throws(()=>d.setRefreshInterval(value));
    assert.equal(d.refreshIntervalSeconds,5);assert.deepEqual(scheduled,[]);assert.deepEqual(saved,[]);
});
test('bad stored values fall back to five seconds',()=>{
    for(const value of [null,'wrong','-1','99999','5.2']){const {d}=setup(value);d.loadRefreshInterval();assert.equal(d.refreshIntervalSeconds,5);}
});
