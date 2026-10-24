/* Original Data Ark vector patterns. No network, fonts or third-party assets. */
(() => {
  'use strict';
  const patterns = [
    ['square','Square grid'],['engineering','Engineering grid (5 subdivisions)'],['dots','Dot grid'],['cross','Cross grid'],
    ['isometric','Isometric / triangular'],['iso-dots','Isometric dots'],['hex','Hexagonal'],['polar','Polar coordinates'],
    ['log','Logarithmic (both axes)'],['semi-log','Semi-logarithmic'],['lined','Ruled lines'],['wide','Wide ruled (8.7 mm)'],
    ['narrow','Narrow ruled (6.35 mm)'],['handwriting','Handwriting guides'],['double','Double-line handwriting'],
    ['cornell-lines','Cornell lined notes'],['cornell-grid','Cornell grid notes'],['cornell-dots','Cornell dot notes'],
    ['music','Music staves'],['tablature','Guitar tablature'],['bass-tab','Bass tablature'],['calligraphy','Calligraphy guides'],
    ['genkou','Character-writing squares'],['chess','Chess / checkers board'],['go','Go board (19 × 19)'],['calendar','Undated monthly calendar'],['story','Story & drawing page'],['blank','Blank page']
  ];
  function geometry(type, w, h, step=5, margin=12) {
    const lines=[],dots=[],rects=[],texts=[];
    const x=margin,y=margin,W=w-2*margin,H=h-2*margin;
    const line=(a,b,c,d,strong=false,dash=false)=>lines.push([a,b,c,d,strong,dash]);
    const grid=(left,top,width,height,dotted=false,spacing=step)=>{
      for(let a=left;a<=left+width+.001;a+=spacing){
        if(dotted){for(let b=top;b<=top+height+.001;b+=spacing)dots.push([a,b]);}
        else line(a,top,a,top+height);
      }
      if(!dotted)for(let b=top;b<=top+height+.001;b+=spacing)line(left,b,left+width,b);
    };
    if(['square','dots','cross','engineering','isometric','iso-dots','hex','polar','log','semi-log'].includes(type)) {
      if(type==='square'||type==='dots')grid(x,y,W,H,type==='dots');
      if(type==='engineering'){
        grid(x,y,W,H,false,step/5);
        for(let a=x;a<=x+W;a+=step)line(a,y,a,y+H,true);
        for(let b=y;b<=y+H;b+=step)line(x,b,x+W,b,true);
      }
      if(type==='cross')for(let a=x;a<=x+W;a+=step)for(let b=y;b<=y+H;b+=step){line(a-.5,b,a+.5,b);line(a,b-.5,a,b+.5);}
      if(type==='isometric'||type==='iso-dots'){
        const dy=step*Math.sqrt(3)/2;
        for(let row=0,b=y;b<=y+H;b+=dy,row++)for(let a=x+(row%2)*step/2;a<=x+W;a+=step){
          if(type==='iso-dots')dots.push([a,b]);
          else {if(a+step<=x+W)line(a,b,a+step,b);if(b+dy<=y+H){if(a+step/2<=x+W)line(a,b,a+step/2,b+dy);if(a-step/2>=x)line(a,b,a-step/2,b+dy);}}
        }
      }
      if(type==='hex'){
        const r=step/Math.sqrt(3),dy=Math.sqrt(3)*r;
        for(let col=0,cx=x+r;cx+r<=x+W;cx+=1.5*r,col++)for(let cy=y+dy/2+(col%2)*dy/2;cy+dy/2<=y+H;cy+=dy){
          const p=Array.from({length:6},(_,i)=>[cx+r*Math.cos(i*Math.PI/3),cy+r*Math.sin(i*Math.PI/3)]);
          p.forEach((v,i)=>line(...v,...p[(i+1)%6]));
        }
      }
      if(type==='polar'){
        const cx=w/2,cy=h/2,R=Math.min(W,H)/2;
        for(let r=step;r<=R;r+=step)rects.push(['circle',cx,cy,r]);
        for(let a=0;a<360;a+=15)line(cx,cy,cx+R*Math.cos(a*Math.PI/180),cy+R*Math.sin(a*Math.PI/180));
      }
      if(type==='log'||type==='semi-log'){
        for(let decade=0;decade<3;decade++)for(let v=1;v<10;v++){
          const a=x+(decade+Math.log10(v))*W/3;line(a,y,a,y+H,v===1);
          if(type==='log'){const b=y+(decade+Math.log10(v))*H/3;line(x,b,x+W,b,v===1);}
        }
        if(type==='semi-log')for(let b=y;b<=y+H;b+=step)line(x,b,x+W,b);
        rects.push(['rect',x,y,W,H]);texts.push([x,y-2,'Three decades; label axes to suit your scale',3]);
      }
    } else if(['lined','wide','narrow'].includes(type)) {
      const gap=type==='wide'?8.7:type==='narrow'?6.35:step;
      for(let b=y;b<=y+H;b+=gap)line(x,b,x+W,b);
    } else if(type==='handwriting'||type==='double'||type==='calligraphy'){
      const gap=Math.max(4,step);
      for(let b=y;b+gap*2<=y+H;b+=gap*3){line(x,b,x+W,b);line(x,b+gap,x+W,b+gap,false,type!=='double');line(x,b+gap*2,x+W,b+gap*2);}
      if(type==='calligraphy')for(let a=x-80;a<x+W;a+=step*2)line(a,y,a+H/Math.tan(Math.PI/3),y+H,false,true);
    } else if(type.startsWith('cornell')){
      const cue=x+W*.24,bottom=y+H-35;rects.push(['rect',x,y,W,H]);line(cue,y,cue,bottom,true);line(x,bottom,x+W,bottom,true);
      if(type==='cornell-grid'||type==='cornell-dots')grid(cue+3,y+8,W*.76-6,bottom-y-10,type==='cornell-dots');
      else for(let b=y+12;b<bottom;b+=step)line(cue+3,b,x+W-3,b);
      texts.push([x+3,y+5,'Cues',3],[cue+3,y+5,'Notes',3],[x+3,bottom+5,'Summary',3]);
    } else if(['music','tablature','bass-tab'].includes(type)){
      const count=type==='music'?5:type==='bass-tab'?4:6,gap=Math.max(2,step/2);
      for(let b=y;b+(count-1)*gap<=y+H;b+=count*gap+gap*4)for(let i=0;i<count;i++)line(x,b+i*gap,x+W,b+i*gap);
    } else if(type==='genkou'){
      const side=Math.max(8,step*2);grid(x,y,W,H,false,side);
      for(let a=x+side/2;a<=x+W;a+=side)line(a,y,a,y+H,false,true);
      for(let b=y+side/2;b<=y+H;b+=side)line(x,b,x+W,b,false,true);
    } else if(type==='chess'||type==='go'){
      const side=Math.min(W,H),top=(h-side)/2,left=(w-side)/2,n=type==='chess'?8:18,d=side/n;
      grid(left,top,side,side,false,d);
      if(type==='chess')for(let a=0;a<8;a++)for(let b=0;b<8;b++)if((a+b)%2)rects.push(['shade',left+a*d,top+b*d,d,d]);
      else for(const a of [3,9,15])for(const b of [3,9,15])dots.push([left+a*d,top+b*d,1]);
    } else if(type==='calendar'){
      texts.push([x,y+5,'Month: ____________________    Year: __________',4]);
      const top=y+18,cellW=W/7,cellH=(H-18)/6;
      for(let i=0;i<=7;i++)line(x+i*cellW,top,x+i*cellW,y+H);
      for(let i=0;i<=6;i++)line(x,top+i*cellH,x+W,top+i*cellH);
      ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach((s,i)=>texts.push([x+i*cellW+2,top-2,s,3]));
    } else if(type==='story'){
      rects.push(['rect',x,y,W,H*.55]);for(let b=y+H*.6;b<y+H;b+=step*1.5)line(x,b,x+W,b);
    }
    return {lines,dots,rects,texts};
  }
  function svg(type,w,h,step,margin,color,weight) {
    const g=geometry(type,w,h,step,margin),esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;');
    let s=`<svg xmlns="http://www.w3.org/2000/svg" width="${w}mm" height="${h}mm" viewBox="0 0 ${w} ${h}" role="img" aria-label="Printable paper"><defs><clipPath id="paper-clip"><rect x="${margin}" y="${margin}" width="${w-2*margin}" height="${h-2*margin}"/></clipPath></defs><rect width="${w}" height="${h}" fill="white"/><g clip-path="url(#paper-clip)" stroke="${color}" stroke-width="${weight}" fill="none">`;
    for(const [a,b,c,d,strong,dash] of g.lines)s+=`<path d="M${a},${b}L${c},${d}"${strong?' stroke-width="'+weight*2+'"':''}${dash?' stroke-dasharray="1,1"':''}/>`;
    for(const [cx,cy,r=.3] of g.dots)s+=`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${color}" stroke="none"/>`;
    for(const [kind,a,b,c,d] of g.rects)s+=kind==='circle'?`<circle cx="${a}" cy="${b}" r="${c}"/>`:`<rect x="${a}" y="${b}" width="${c}" height="${d}"${kind==='shade'?' fill="'+color+'" fill-opacity=".16" stroke="none"':''}/>`;
    s+='</g>';for(const [a,b,t,size] of g.texts)s+=`<text x="${a}" y="${b}" font-size="${size}" font-family="sans-serif" fill="${color}">${esc(t)}</text>`;
    return s+'</svg>';
  }
  globalThis.ArkPaper={patterns,geometry,svg};
})();
