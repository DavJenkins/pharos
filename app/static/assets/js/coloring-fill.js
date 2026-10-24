// Fill with a virtual round brush: only brush centers that clear the outlines
// can travel. Restore edges from their nearest safe center without flooding
// through a choke point into another region.
export function fillRegion(pixels, output, width, height, x, y, rgb, size) {
  x=Math.floor(x); y=Math.floor(y);
  if(x<0||y<0||x>=width||y>=height)return 0;
  const N=width*height,seed=y*width+x,offset=seed*4;
  const dark=i=>Math.max(pixels[i],pixels[i+1],pixels[i+2])<110;
  if(dark(offset))return 0;
  const value=Number(size),radius=(Number.isFinite(value)?Math.max(2,Math.min(60,value)):14)/2;
  const threshold=radius*3,red=pixels[offset],green=pixels[offset+1],blue=pixels[offset+2];
  const allowed=new Uint8Array(N),clearance=new Uint16Array(N);
  // 3/4 chamfer distances approximate a circular brush in rendered-page pixels.
  for(let n=0;n<N;n++){
    const i=n*4;
    allowed[n]=!dark(i)&&Math.max(Math.abs(red-pixels[i]),Math.abs(green-pixels[i+1]),Math.abs(blue-pixels[i+2]))<=45?1:0;
    const xx=n%width,yy=Math.floor(n/width);
    clearance[n]=allowed[n]?(xx===0||yy===0||xx===width-1||yy===height-1?3:65500):0;
  }
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const n=y*width+x;if(!allowed[n])continue;
    let d=clearance[n];
    if(x)d=Math.min(d,clearance[n-1]+3);
    if(y){d=Math.min(d,clearance[n-width]+3);if(x)d=Math.min(d,clearance[n-width-1]+4);if(x+1<width)d=Math.min(d,clearance[n-width+1]+4);}
    clearance[n]=d;
  }
  for(let y=height-1;y>=0;y--)for(let x=width-1;x>=0;x--){
    const n=y*width+x;if(!allowed[n])continue;
    let d=clearance[n];
    if(x+1<width)d=Math.min(d,clearance[n+1]+3);
    if(y+1<height){d=Math.min(d,clearance[n+width]+3);if(x)d=Math.min(d,clearance[n+width-1]+4);if(x+1<width)d=Math.min(d,clearance[n+width+1]+4);}
    clearance[n]=d;
  }
  const queue=new Int32Array(N),seen=new Uint8Array(N),steps=new Uint16Array(N);
  let head=0,tail=0;
  const neighbors=n=>{const x=n%width,y=Math.floor(n/width);return [x?n-1:-1,x+1<width?n+1:-1,y?n-width:-1,y+1<height?n+width:-1];};
  // A tap near the border can select the nearby interior of the same region.
  queue[tail++]=seed;seen[seed]=1;let start=-1;
  const edgeReach=Math.ceil(radius*2);
  while(head<tail){const n=queue[head++];if(clearance[n]>=threshold){start=n;break;}
    if(steps[n]>=edgeReach)continue;
    for(const m of neighbors(n))if(m>=0&&allowed[m]&&!seen[m]){seen[m]=1;steps[m]=steps[n]+1;queue[tail++]=m;}
  }
  if(start<0)return 0;
  // Flood only positions where the whole brush fits.
  seen.fill(0);head=0;tail=0;queue[tail++]=start;seen[start]=1;
  while(head<tail){const n=queue[head++];for(const m of neighbors(n))if(m>=0&&!seen[m]&&clearance[m]>=threshold){seen[m]=1;queue[tail++]=m;}}
  // Let every safe center claim its nearest edge pixels. Unreachable centers
  // reserve the far side of a narrow opening, preventing a second full flood.
  const owner=new Uint8Array(N);steps.fill(0);head=0;tail=0;
  for(let n=0;n<N;n++)if(allowed[n]&&clearance[n]>=threshold){owner[n]=seen[n]?1:2;queue[tail++]=n;}
  while(head<tail){const n=queue[head++];if(steps[n]>=edgeReach)continue;
    for(const m of neighbors(n))if(m>=0&&allowed[m]&&!owner[m]){owner[m]=owner[n];steps[m]=steps[n]+1;queue[tail++]=m;}
  }
  let count=0;
  for(let n=0;n<N;n++)if(owner[n]===1){const i=n*4;output[i]=rgb[0];output[i+1]=rgb[1];output[i+2]=rgb[2];output[i+3]=255;count++;}
  return count;
}
