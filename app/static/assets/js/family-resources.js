(() => {
 const search=document.getElementById('resource-search'),language=document.getElementById('resource-language'),group=document.getElementById('resource-group');
 function filter(){let count=0;for(const row of document.querySelectorAll('[data-resource]')){const visible=(!search.value||row.dataset.search.includes(search.value.toLowerCase()))&&(!language.value||row.dataset.language===language.value)&&(!group.value||row.dataset.group===group.value);row.hidden=!visible;if(visible)count++;}for(const section of document.querySelectorAll('.resource-section'))section.hidden=![...section.querySelectorAll('[data-resource]')].some(row=>!row.hidden);document.getElementById('resource-count').textContent=count+' resources match';}
 for(const control of [search,language,group])control.addEventListener('input',filter);filter();
})();
