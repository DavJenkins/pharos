/* Offline lexical YAML coloring over a native textarea. Only visible lines get DOM. */
(() => {
    'use strict';
    const escape=text=>text.replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    function colorLine(line){
        const tokens=/"(?:\\.|[^"\\])*"|'(?:''|[^'])*'|(?:^|[ \t])#[^\r\n]*|[A-Za-z_][\w .-]*(?=:\s|:$)|[&*!][\w.-]+|\b(?:true|false|yes|no|on|off|null)\b|~(?=\s|$)|-?\b(?:0x[\da-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b|[{}\[\],]|:(?=\s|$)|[|>][+-]?(?=\s|$)/g;
        let output='',at=0;
        for(const match of line.matchAll(tokens)){
            const value=match[0],tail=line.slice(match.index+value.length);
            let kind;
            if(/^\s*#/.test(value))kind='comment';
            else if(/^["']/.test(value))kind=/^\s*:/.test(tail)?'key':'string';
            else if(/^:/.test(tail))kind='key';
            else if(/^[&*!]/.test(value))kind='anchor';
            else if(/^(true|false|yes|no|on|off|null|~)$/.test(value))kind='literal';
            else if(/^-?\d/.test(value))kind='number';
            else kind='punctuation';
            output+=escape(line.slice(at,match.index))+'<span class="yaml-'+kind+'">'+escape(value)+'</span>';
            at=match.index+value.length;
        }
        return output+escape(line.slice(at));
    }
    if(typeof module!=='undefined'&&module.exports)module.exports={colorLine};
    if(typeof document==='undefined')return;
    const editor=document.getElementById('configuration-text');
    if(!editor)return;
    const shell=document.createElement('div');shell.className='yaml-editor';
    const viewport=document.createElement('div');viewport.className='yaml-colors';viewport.setAttribute('aria-hidden','true');
    const layer=document.createElement('pre');viewport.append(layer);
    editor.parentNode.insertBefore(shell,editor);shell.append(viewport,editor);
    editor.wrap='off';editor.classList.add('yaml-colored');
    let value=null,lines=[],scheduled=false;
    function render(){
        scheduled=false;
        if(value!==editor.value){value=editor.value;lines=value.split('\n');}
        const style=getComputedStyle(editor),height=parseFloat(style.lineHeight)||21;
        const paddingTop=parseFloat(style.paddingTop)||0,paddingLeft=parseFloat(style.paddingLeft)||0;
        const start=Math.max(0,Math.floor((editor.scrollTop-paddingTop)/height)-1);
        const end=Math.min(lines.length,start+Math.ceil(editor.clientHeight/height)+4);
        viewport.style.top=editor.clientTop+'px';viewport.style.left=editor.clientLeft+'px';
        viewport.style.width=editor.clientWidth+'px';viewport.style.height=editor.clientHeight+'px';
        layer.style.top=(paddingTop+start*height-editor.scrollTop)+'px';
        layer.style.left=(paddingLeft-editor.scrollLeft)+'px';
        layer.innerHTML=lines.slice(start,end).map(colorLine).join('\n')+'\n';
    }
    function refresh(){if(!scheduled){scheduled=true;requestAnimationFrame(render);}}
    editor.addEventListener('input',refresh);editor.addEventListener('scroll',refresh);
    window.addEventListener('resize',refresh);
    if(typeof ResizeObserver!=='undefined')new ResizeObserver(refresh).observe(editor);
    window.ArkYamlHighlight=Object.freeze({refresh});refresh();
})();
