import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const dir=new URL('../',import.meta.url);const read=n=>fs.readFileSync(new URL(n,dir),'utf8');
const slides=JSON.parse(read('slides.json'));assert.equal(slides.length,17);assert.equal(slides.reduce((a,s)=>a+s.time,0),635);
assert.equal((read('script.md').match(/\*\*\[→\]\*\*/g)||[]).length,slides.reduce((a,s)=>a+s.notes.length,0));
slides.forEach((s,i)=>{for(const m of s.body.matchAll(/data-in="(\d+)"/g))assert(+m[1]<=s.notes.length,`slide ${i+1}`)});
const src=read('deck.js');const context=vm.createContext({window:{}});vm.runInContext(read('data.js'),context);context.FORECAST=context.window.FORECAST;
vm.runInContext(src.slice(src.indexOf('function weather'),src.indexOf('function chart')),context);
assert.equal(context.FORECAST.length,24);assert.deepEqual(Array.from(context.FORECAST,r=>r.hour),Array.from({length:24},(_,i)=>i));
for(let duration=1;duration<=24;duration++)for(let start=0;start<24;start++)for(let end=start+1;end<=24;end++){
 const b=context.cheapest(duration,start,end);if(end-start<duration){assert.equal(b,null);continue}
 assert(b.start>=start&&b.end<=end&&b.end-b.start===duration);
 const all=[];for(let s=start;s+duration<=end;s++)all.push(context.FORECAST.slice(s,s+duration).reduce((a,r)=>a+r.price,0)/duration);
 assert(Math.abs(b.avg-Math.min(...all))<1e-9);
}
assert.equal(Math.ceil(60*(80-35)/100/7),4);assert.equal(Math.ceil(60*(90-35)/100/7),5);
for(const [p,q,w] of [[124.9,.19,0],[125,0,1],[150,0,2],[170,0,3],[200,0,4],[0,.2,1],[0,.4,2],[0,.55,3],[0,.75,4]])assert.equal(context.weather(p,q),w);
console.log(JSON.stringify({slides:17,steps:slides.reduce((a,s)=>a+s.notes.length,0),seconds:635,default4h:context.cheapest(4,0,16),changed5h:context.cheapest(5,0,16),checks:'source/notes, all feasible windows, weather boundaries passed'},null,2));
