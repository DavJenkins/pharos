/* Every action is caretaker-authorized; reading progress and comparisons is public. */
let publisherReviewItem=null,publisherReviewJob=null,publisherReviewBusy=false,publisherReviewActionError=false;
const publisherDialog=document.createElement('dialog');
publisherDialog.className='publisher-review-dialog ark-dialog-layout';
publisherDialog.innerHTML='<header class="ark-dialog-header"><h2>Review publisher change</h2><h3 class="ark-dialog-subtitle" data-review-title></h3></header><div class="ark-dialog-body"><p data-review-status role="status" aria-live="polite"></p><p data-review-summary></p><details data-review-comparison hidden><summary>Text comparison: installed → publisher candidate</summary><pre></pre></details><p data-review-error role="alert" hidden></p><div class="publisher-review-actions"><button type="button" data-review-prepare>Prepare verified comparison</button><button type="button" data-review-install hidden>Install verified candidate</button><button type="button" data-review-keep hidden>Keep installed edition</button></div></div><footer class="ark-dialog-footer"><button type="button" data-review-close>Close</button></footer>';
document.body.append(publisherDialog);
const reviewEl=s=>publisherDialog.querySelector('[data-review-'+s+']');
function publisherReviewElapsed(job,now=Date.now()/1000){
 const start=job.operation_started_at||(job.state==='installing'?job.updated_at:job.started_at);
 return Number.isFinite(start)?Math.max(0,Math.floor(now-start)):Math.max(0,Math.floor(job.telemetry?.elapsed_seconds||0));
}
let publisherRateSample=null;
function publisherReviewETA(job,t,now=Date.now()/1000){
 if(t.unit==='tasks')return null;
 const bytes=Number.isFinite(t.total_bytes)&&t.total_bytes>0&&Number.isFinite(t.bytes_processed);
 const total=bytes?t.total_bytes:100,done=bytes?t.bytes_processed:t.percent;
 if(!Number.isFinite(done)||done<0||done>total)return null;
 const key=[job.job,job.state,t.phase,total,bytes].join('|');
 if(!publisherRateSample||publisherRateSample.key!==key||done<publisherRateSample.done)publisherRateSample={key,done,advanced:now,points:[]};
 const sample=publisherRateSample;
 if(done>sample.done){sample.advanced=now;sample.done=done;}
 sample.points.push({at:now,done});
 while(sample.points.length>2&&now-sample.points[1].at>=30)sample.points.shift();
 if(done===total)return 'Finishing this phase…';
 const first=sample.points[0],seconds=now-first.at;
 if(seconds<8)return 'Calculating…';
 if(now-sample.advanced>15||done===first.done)return 'Waiting for progress…';
 const remaining=(total-done)*seconds/(done-first.done);
 if(remaining<60)return 'Less than a minute';
 const minutes=Math.ceil(remaining/60);
 return minutes<60?'About '+minutes+' min':'About '+Math.floor(minutes/60)+' hr '+(minutes%60)+' min';
}
reviewEl('close').onclick=()=>publisherDialog.close();
publisherDialog.addEventListener('close',()=>refresh());
function renderPublisherReview(job){
 publisherReviewJob=job;
 const loading=job.state==='loading',active=loading||['queued','preparing','installing'].includes(job.state),ready=job.state==='ready';
 reviewEl('status').textContent=job.message||'Prepare a candidate on the Ark. Downloaded files are verified before you choose what to install. Existing copies remain available.';
 reviewEl('status').className='operation-state state-'+(job.state==='failed'?'error':['installed','kept'].includes(job.state)?'success':active?'working':'confirm');
 reviewEl('summary').textContent=job.summary||'';
 let metrics=publisherDialog.querySelector('.publisher-review-metrics');
 if(!metrics){metrics=document.createElement('dl');metrics.className='publisher-review-metrics';reviewEl('status').after(metrics);}
 metrics.replaceChildren();
 const t=job.state==='installing'?(job.install_telemetry||{}):(job.telemetry||{}),elapsed=publisherReviewElapsed(job);
 const percent=Number.isFinite(t.percent)&&t.percent>=0&&t.percent<=100?Math.round(t.percent):null;
 const eta=active?publisherReviewETA(job,t):null;
 const processed=Number.isFinite(t.bytes_processed)?(t.total_bytes?(t.bytes_processed/1024**3).toFixed(2)+' of '+(t.total_bytes/1024**3).toFixed(2)+' GiB':(t.bytes_processed/1024**2).toFixed(1)+' MiB'):null;
 if(active&&!loading){for(const [label,value] of [['Candidate edition',job.candidate_edition||job.edition?.edition],['Phase',t.phase||(job.state==='installing'?'Verifying and installing the candidate':null)],['Elapsed',Math.floor(elapsed/60)+' min '+(elapsed%60)+' sec'],[Number.isFinite(t.bytes_downloaded)?'Data downloaded':'Data processed',Number.isFinite(t.bytes_downloaded)?(t.bytes_downloaded/1024**2).toFixed(1)+' MiB':processed],['Publishing tasks',t.unit==='tasks'?t.units_processed+' of '+t.total_units+' completed':null],['Progress',percent!==null?percent+'% of this phase':null],['Estimated remaining (this phase)',eta]]){if(!value)continue;const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;metrics.append(dt,dd);}}
 metrics.hidden=!metrics.children.length;
 let bar=publisherDialog.querySelector('.publisher-review-progress');
 if(!bar){bar=document.createElement('progress');bar.className='publisher-review-progress';bar.max=100;bar.setAttribute('aria-label','Current installation phase progress');metrics.after(bar);}
 bar.hidden=!active||percent===null;bar.value=percent||0;
 reviewEl('prepare').hidden=active||ready;reviewEl('prepare').textContent=job.state==='idle'?'Prepare verified comparison':'Prepare again';
 reviewEl('install').hidden=!ready;reviewEl('install').textContent=job.edition&&job.kind==='document'?'Add '+job.edition.edition+' edition':'Install verified candidate';
 reviewEl('keep').hidden=!ready;
 reviewEl('comparison').hidden=!ready||!('diff' in job);
 reviewEl('comparison').querySelector('pre').textContent=job.identical?'No text differences found.':(job.diff||'')+(job.diff_truncated?'\n[Comparison shortened for display]':'');
 for(const b of publisherDialog.querySelectorAll('.publisher-review-actions button'))b.disabled=publisherReviewBusy;
}
async function openPublisherReview(item){publisherReviewItem=item;publisherReviewJob=null;publisherReviewActionError=false;reviewEl('title').textContent=item.title;reviewEl('error').hidden=true;renderPublisherReview({state:'loading',message:'Loading current progress…'});publisherDialog.showModal();await pollPublisherReview();}
async function pollPublisherReview(){if(!publisherDialog.open||!publisherReviewItem||publisherReviewBusy)return;try{const job=await request('/api/library/publisher-review/'+encodeURIComponent(publisherReviewItem.id));if(publisherDialog.open){renderPublisherReview(job);if(!publisherReviewActionError){reviewEl('error').hidden=true;reviewEl('error').textContent='';}}}catch(error){if(!publisherReviewActionError){reviewEl('error').hidden=false;reviewEl('error').textContent=error.message;}}}
async function decidePublisherReview(decision){
 if(publisherReviewBusy||!publisherReviewItem)return;
 publisherReviewBusy=true;publisherReviewActionError=false;reviewEl('error').hidden=true;renderPublisherReview(publisherReviewJob||{state:'idle'});
 try{const authorization=await window.CaretakerAuth.authorization(decision==='prepare'?'Authorize preparing this publisher comparison.':'Authorize this publisher review decision.');const job=await request('/api/library/publisher-review',{method:'POST',headers:{'Content-Type':'application/json',Authorization:authorization},body:JSON.stringify({asset_id:publisherReviewItem.id,decision,job:publisherReviewJob?.job||''})});renderPublisherReview(job);}
 catch(error){if(error.name!=='AbortError'){publisherReviewActionError=true;reviewEl('error').hidden=false;reviewEl('error').textContent='Action not accepted: '+error.message;}}
 finally{publisherReviewBusy=false;renderPublisherReview(publisherReviewJob||{state:'idle'});}
}
for(const decision of ['prepare','install','keep'])reviewEl(decision).onclick=()=>decidePublisherReview(decision);
setInterval(pollPublisherReview,2500);
setInterval(()=>{if(publisherDialog.open&&publisherReviewJob&&['queued','preparing','installing'].includes(publisherReviewJob.state))renderPublisherReview(publisherReviewJob);},1000);
