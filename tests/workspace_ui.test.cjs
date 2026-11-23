const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),{webcrypto}=require('node:crypto'),{test}=require('node:test');
const source=fs.readFileSync(require('node:path').join(__dirname,'../inbox_ui/index.html'),'utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 const elements=new Map(),tags=[],posts=[],listeners={};
 class Element{
  constructor(tag){this.tag=tag;this.children=[];this.style={};this.dataset={};this.value='';this.scrollTop=0;this.scrollHeight=500;this.clientHeight=500;this.classList={toggle(){},add(){},remove(){}};}
  append(...values){this.children.push(...values)}appendChild(value){this.children.push(value)}replaceChildren(...values){this.children=values}setAttribute(){}focus(){}
 }
 const get=id=>{if(!elements.has(id))elements.set(id,new Element('div'));return elements.get(id)};
 const filters=['ALL','WHATSAPP','SMS'].map(channel=>{const e=new Element('button');e.dataset.channel=channel;return e});
 const document={getElementById:get,querySelectorAll:()=>filters,body:new Element('body'),createElement:tag=>{tags.push(tag);return new Element(tag)}};
 const parent={postMessage:message=>posts.push(message)},window={parent,addEventListener:(name,fn)=>listeners[name]=fn};
 get('days').value='90';get('view').value='all';
 vm.runInNewContext(source,{document,window,crypto:webcrypto,Uint8Array,Intl,Date,JSON,Map,Number,String,Math,confirm:()=>true});
 const a={channel:'SMS',phone:'+13055550123',sender:'+13055550124',name:'Ana Example',patient_names:['Ana Example'],paused:false,messages:[{direction:'inbound',message:'<img src=x onerror=alert(1)>',timestamp:'2026-11-23T10:00:00Z'}]};
 const b={...a,channel:'WHATSAPP',sender:'app-id',name:'Luis Example',patient_names:['Luis Example'],messages:[]};
 const render=result=>listeners.message({source:parent,data:{type:'streamlit:render',args:{conversations:[a,b],filters:{channel:'ALL',days:90},result}}});
 const latest=()=>posts.filter(p=>p.type==='streamlit:setComponentValue').slice(-1)[0]?.value;
 const ack=()=>{const p=latest();render({id:p.id,type:p.type,ok:true,message:''})};
 render();return {get,posts,tags,render,latest,ack,document,a,b};
}
test('conversation selection sends through its own channel and business sender',()=>{const s=setup();s.get('list').children[0].onclick();s.ack();s.get('reply').value='Staff reply';s.get('send').onclick();const send=s.latest();assert.equal(send.type,'send');assert.equal(send.channel,'SMS');assert.equal(send.phone,'+13055550123');assert.equal(send.sender,'+13055550124');assert.equal(send.text,'Staff reply');assert.match(send.request_id,/^[a-f0-9]{32}$/)});
test('patient messages are text, never interpreted as HTML',()=>{const s=setup();s.get('list').children[0].onclick();assert.equal(s.tags.includes('img'),false);const rows=s.get('messages').children.filter(e=>e.className?.startsWith('bubble-row'));assert.equal(rows[0].children[0].children[0].textContent,'<img src=x onerror=alert(1)>')});
test('drafts remain scoped to each conversation',()=>{const s=setup();s.get('list').children[0].onclick();s.ack();s.get('reply').value='Draft A';s.get('list').children[1].onclick();s.ack();assert.equal(s.get('reply').value,'');s.get('reply').value='Draft B';s.get('list').children[0].onclick();s.ack();assert.equal(s.get('reply').value,'Draft A')});
test('refresh and acknowledgements never send a reply automatically',()=>{const s=setup();s.get('list').children[0].onclick();s.ack();s.get('reply').value='Reply';s.get('send').onclick();const send=s.latest();const before=s.posts.filter(p=>p.type==='streamlit:setComponentValue'&&p.value.type==='send').length;s.render({id:send.id,type:'send',ok:true,channel:send.channel,phone:send.phone,sender:send.sender,message:'Accepted'});s.render();assert.equal(s.get('reply').value,'');assert.equal(s.posts.filter(p=>p.type==='streamlit:setComponentValue'&&p.value.type==='send').length,before)});

test('search finds another patient on a shared number without exact accents',()=>{const s=setup();s.a.patient_names=['Ana Example','Carlos García'];s.render();s.get('search').value='garcia';s.get('search').oninput();assert.equal(s.get('list').children.length,1);assert.equal(s.get('list').children[0].tag,'button')});
