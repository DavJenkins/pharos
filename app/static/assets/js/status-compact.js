"use strict";
function arkStatusCanCondense(data, online, refreshing) {
 const status=data?.status, network=data?.network;
 return refreshing && online === true && status?.state === "ok" &&
  /^idle$/i.test((status.sync || "").trim()) && !(status.issues?.length) &&
  network?.ethernet?.enabled !== false && network?.wifi?.enabled !== false &&
  network?.access_point?.active === true;
}
(() => {
 const panel=document.querySelector(".status-bar"),settings=document.getElementById("ark-settings");
 if(!panel || !settings)return;
 const gear=settings.querySelector("summary");let healthySince=null,lastRefresh=0;
 function update() {
  const now=Date.now();
  const fresh=lastRefresh && now-lastRefresh <= (Dashboard.refreshIntervalSeconds+10)*1000;
  const healthy=fresh && !settings.open && arkStatusCanCondense(DataArkStatus.data,
   document.getElementById("internet-status")?.dataset.online === "true",Dashboard.refreshEnabled);
  if(!healthy)healthySince=null;
  else if(healthySince===null)healthySince=now;
  const compact=healthy && now-healthySince>=30000;
  panel.classList.toggle("status-condensed",compact);
  gear.title=compact ? "Ark healthy · sync idle · Settings" : "Settings";
  gear.setAttribute("aria-label",gear.title);
 }
 window.addEventListener("dataark:dashboard-refreshed",()=>{lastRefresh=Date.now();update();});
 window.addEventListener("dataark:connectivity-refreshed",update);
 settings.addEventListener("toggle",()=>{healthySince=null;update();});
 setInterval(update,1000);
})();
