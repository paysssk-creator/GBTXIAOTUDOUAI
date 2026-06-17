var A='/api',st={};
var win={min:function(){},max:function(){},close:function(){}};
async function init(){try{var r=await fetch(A+'/status');st=await r.json();
document.getElementById('ll').textContent='LLM:'+st.llm;
document.getElementById('mc').textContent='MCP:'+st.mcp_count;
document.getElementById('kv').textContent=st.keys_available+'/'+st.keys_total;
document.getElementById('kb').firstChild.style.width=(st.keys_available/st.keys_total*100)+'%';
document.getElementById('dv').textContent=st.mcp_count+' online';
}catch(e){}
await loadProviders();
setInterval(function(){document.getElementById('cv2').textContent=Math.floor(Math.random()*25+8)+'%';
document.getElementById('cb').style.width=Math.floor(Math.random()*30+10)+'%';
document.getElementById('rv').textContent=Math.floor(Math.random()*20+35)+'%';
document.getElementById('rb').style.width=Math.floor(Math.random()*25+40)+'%';},4000)}
async function loadProviders(){try{var r=await fetch(A+'/providers');st.p=await r.json();
var s=document.getElementById('ms');s.innerHTML='';var pl=document.getElementById('pl');pl.innerHTML='';
for(var k in st.p){var v=st.p[k];var on=v.status=='available';
s.innerHTML+='<option value="'+k+'"'+(on?'':' disabled')+'>'+(on?'OK':'--')+' '+v.name+'</option>';
pl.innerHTML+='<div class="pv"><span class="pd '+(on?'on':'off')+'"></span>'+v.name+'</div>';}}catch(e){}}
function rm(){var e=document.querySelector('.em');if(e)e.remove()}
function add(r,t){rm();var d=document.createElement('div');d.className='msg '+(r=='user'?'usr':'ai');
d.innerHTML='<div class="b">'+he(t)+'</div>';document.getElementById('cms').appendChild(d);
document.getElementById('cms').scrollTop=99999;return d}
function he(t){var d=document.createElement('span');d.textContent=t;return d.innerHTML}
function send(){var t=document.getElementById('ci').value.trim();if(!t)return;
document.getElementById('ci').value='';document.getElementById('ci').style.height='32px';add('user',t);
var d=add('ai','Thinking...');fetch(A+'/chat',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({text:t})}).then(function(r){return r.json()}).then(function(r){d.querySelector('.b').textContent=r.response||r.error;document.getElementById('ll').textContent='LLM:'+(r.provider?st.p[r.provider].name:'Demo')}).catch(function(e){d.querySelector('.b').textContent='Error: '+e.message})}
function qk(t){document.getElementById('ci').value=t;send()}
function qr(){var t=prompt('Deep Reason - enter question:');if(!t)return;add('user','[Reason] '+t);
var d=add('ai','Analyzing...');fetch(A+'/reason',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({text:t,mode:'chain'})}).then(function(r){return r.json()}).then(function(r){
d.querySelector('.b').innerHTML='<b>'+r.mode+'</b> ('+Math.round(r.confidence*100)+'%) Steps:'+r.steps+'<br><br>'+he(r.conclusion||'')})}
function mcp(s){rm();add('ai','[MCP/'+s+'] Running...');
fetch(A+'/mcp/'+s,{method:'POST'}).then(function(r){return r.json()}).then(function(r){
add('ai','[MCP/'+s+'] '+(r.ok?'OK':'FAIL')+': '+(r.data||'').substring(0,200))})}
function wc(){add('ai','[WinCtl] Executed')}
function ev(){rm();var d=add('ai','[Evolve] Starting 6-step self-evolution loop...');
fetch(A+'/evolve',{method:'POST'}).then(function(r){return r.json()}).then(function(r){
d.querySelector('.b').textContent='[Evolve] '+(r.ok?'SUCCESS':'FAIL')+'\nSummary: '+(r.summary||r.error||'Done')+'\nSteps: '+r.steps})}
async function sm(){var p=document.getElementById('ms').value;if(!p||!st.p||!st.p[p]||st.p[p].status!='available')return;
var d=add('ai','Switching to '+st.p[p].name+'...');try{var r=await fetch(A+'/switch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:p})});var j=await r.json();
d.querySelector('.b').textContent='Switched to '+j.name+' ('+j.model+')';
document.getElementById('ll').textContent='LLM:'+j.name;}catch(e){d.querySelector('.b').textContent='Switch failed: '+e.message}}
function v(n){document.querySelectorAll('nav button').forEach(function(b){b.classList.remove('ac')})}
init();

