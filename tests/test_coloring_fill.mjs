import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../app/static/assets/js/coloring-fill.js',import.meta.url),'utf8');
const {fillRegion}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const W=61,H=41;
function picture(gap){
 const p=new Uint8ClampedArray(W*H*4);
 for(let y=0;y<H;y++)for(let x=0;x<W;x++){
  const black=x===0||x===W-1||y===0||y===H-1||(x===30&&Math.abs(y-20)>gap/2);
  p.set(black?[0,0,0,255]:[255,255,255,255],(y*W+x)*4);
 }return p;
}
function run(p,size,x=15,y=20){const out=new Uint8ClampedArray(p.length);const count=fillRegion(p,out,W,H,x,y,[230,120,20],size);for(let n=0;n<W*H;n++)if(p[n*4]===0)assert.equal(out[n*4+3],0,'Dark outline must remain untouched');return {out,count};}
let p=picture(5),small=run(p,2),large=run(p,14);
assert.equal(small.out[(20*W+45)*4+3],255,'Narrow brush must pass through the small gap');
assert.equal(large.out[(20*W+45)*4+3],0,'Wide brush must not flood the far chamber');
assert.equal(large.out[(20*W+15)*4+3],255,'Wide brush must fill the tapped chamber');
assert(small.count>large.count);
p=picture(21);assert.equal(run(p,14).out[(20*W+45)*4+3],255,'Wide brush must pass a sufficiently wide opening');
p=picture(-1);assert.equal(run(p,2).out[(20*W+45)*4+3],0,'Closed borders must never be crossed');
assert.equal(run(p,14,30,20).count,0,'Tapping a dark border must not paint');
const narrow=new Uint8ClampedArray(W*H*4);for(let y=0;y<H;y++)for(let x=0;x<W;x++)narrow.set(x>=29&&x<=31?[255,255,255,255]:[0,0,0,255],(y*W+x)*4);
assert.equal(run(narrow,14,30,20).count,0,'A brush that cannot fit must decline the fill');
assert.equal(fillRegion(p,new Uint8ClampedArray(p.length),W,H,-1,20,[1,2,3],14),0);
const big=new Uint8ClampedArray(800*1000*4).fill(255),out=new Uint8ClampedArray(big.length);
const started=performance.now();assert.equal(fillRegion(big,out,800,1000,400,500,[1,2,3],14),800000);
console.log('PASS: narrow/wide gaps, closed outlines, dark seeds, too-narrow regions, edge coordinates, full-page fill ('+Math.round(performance.now()-started)+' ms)');
