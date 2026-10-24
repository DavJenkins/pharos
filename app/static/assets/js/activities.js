(() => {
  'use strict';
  const el=id=>document.getElementById(id),shuffle=a=>{for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;};
  let generation=0;
  function memory(){
    const gen=++generation,values=shuffle(['★','●','▲','■','◆','♥','☀','☂'].flatMap(x=>[x,x]));let open=[],found=new Set(),moves=0,locked=false;
    el('memory').replaceChildren();el('memory-status').textContent='0 of 8 pairs';
    values.forEach((v,i)=>{const b=document.createElement('button');b.textContent='?';b.setAttribute('aria-label','Hidden card '+(i+1));el('memory').append(b);b.onclick=()=>{
      if(locked||found.has(i)||open.includes(i))return;b.textContent=v;b.setAttribute('aria-label',v);open.push(i);
      if(open.length===2){moves++;const [a,c]=open;if(values[a]===values[c]){found.add(a);found.add(c);for(const n of open)el('memory').children[n].classList.add('matched');open=[];}else{locked=true;setTimeout(()=>{if(gen!==generation)return;for(const n of open){const button=el('memory').children[n];button.textContent='?';button.setAttribute('aria-label','Hidden card '+(n+1));}open=[];locked=false;},850);}
        el('memory-status').textContent=`${found.size/2} of 8 pairs · ${moves} ${moves===1?'turn':'turns'}`+(found.size===16?' — All found!':'');}
    };});
  }
  function ttt(){let cells=Array(9).fill(''),turn='X',done=false;el('ttt').replaceChildren();el('ttt-status').textContent='X goes first';
    cells.forEach((_,i)=>{const b=document.createElement('button');b.innerHTML='&nbsp;';b.setAttribute('aria-label','Empty square '+(i+1));el('ttt').append(b);b.onclick=()=>{if(done||cells[i])return;cells[i]=turn;b.textContent=turn;b.setAttribute('aria-label',turn+' square '+(i+1));const won=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]].some(a=>a.every(n=>cells[n]===turn));done=won||cells.every(Boolean);el('ttt-status').textContent=won?turn+' wins!':done?'A draw — try again!':(turn==='X'?'O':'X')+' to play';turn=turn==='X'?'O':'X';};});
  }
  function slide(){let a=Array.from({length:16},(_,i)=>(i+1)%16),moves=0,prev=-1;
    const near=i=>[i-4,i+4,...(i%4?[i-1]:[]),...(i%4<3?[i+1]:[])].filter(n=>n>=0&&n<16);
    for(let k=0;k<220;k++){const z=a.indexOf(0),opts=near(z).filter(n=>n!==prev),n=opts[Math.floor(Math.random()*opts.length)];[a[z],a[n]]=[a[n],a[z]];prev=z;}
    function draw(){el('slide').replaceChildren();a.forEach((v,i)=>{const b=document.createElement('button');b.textContent=v||' ';b.disabled=!v;b.className=v?'':'secondary';b.setAttribute('aria-label',v?'Tile '+v:'Empty space');b.onclick=()=>{const z=a.indexOf(0);if(!near(z).includes(i))return;[a[z],a[i]]=[a[i],a[z]];moves++;draw();};el('slide').append(b);});el('slide-status').textContent=a.every((v,i)=>v===(i+1)%16)?`Solved in ${moves} moves!`:`${moves} ${moves===1?"move":"moves"}`;}
    draw();
  }
  function words(){const names=['TREE','BIRD','MOON','RAIN','STAR'],board=Array(64).fill(''),paths={},found=new Set();let first=null;
    for(const name of names){let placed=false;for(let tries=0;tries<300&&!placed;tries++){const r=Math.floor(Math.random()*8),c=Math.floor(Math.random()*8),[dr,dc]=[[0,1],[1,0],[1,1]][Math.floor(Math.random()*3)],path=[];for(let i=0;i<name.length;i++){const rr=r+dr*i,cc=c+dc*i;if(rr>7||cc>7)break;path.push(rr*8+cc);}if(path.length===name.length&&path.every((p,i)=>!board[p]||board[p]===name[i])){path.forEach((p,i)=>board[p]=name[i]);paths[name]=path;placed=true;}}if(!placed){words();return;}}
    board.forEach((v,i)=>{if(!v)board[i]='ABCDEFGHIJKLMNOPQRSTUVWXYZ'[Math.floor(Math.random()*26)];});el('words').replaceChildren();
    const status=()=>el('word-status').textContent=names.map(n=>found.has(n)?'✓ '+n:n).join(' · ')+(found.size===names.length?' — All found!':'');
    board.forEach((v,i)=>{const b=document.createElement('button');b.textContent=v;b.style.cssText='font-size:1rem;padding:0;min-height:36px';b.setAttribute('aria-label',v+' row '+(Math.floor(i/8)+1)+' column '+(i%8+1));b.onclick=()=>{if(first===null){first=i;b.style.outline='3px solid #cc7900';return;}for(const name of names){const p=paths[name];if((p[0]===first&&p.at(-1)===i)||(p[0]===i&&p.at(-1)===first)){found.add(name);p.forEach(n=>el('words').children[n].classList.add('matched'));}}el('words').children[first].style.outline='';first=null;status();};el('words').append(b);});status();
  }
  for(const [id,fn] of [['memory',memory],['ttt',ttt],['slide',slide],['word',words]]){el(id+'-new').onclick=fn;fn();}
})();
