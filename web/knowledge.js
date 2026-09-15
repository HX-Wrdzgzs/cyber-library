const kForm=document.querySelector('#knowledge-form');
if(kForm){
  const out=document.querySelector('#knowledge-output');
  const status=document.querySelector('#knowledge-status');
  const setOutput=value=>{out.textContent=JSON.stringify(value,null,2)};
  kForm.addEventListener('submit',async ev=>{
    ev.preventDefault();
    const mode=document.querySelector('#knowledge-mode').value;
    const q=document.querySelector('#knowledge-query').value.trim();
    if(!q)return;
    status.textContent='正在构建知识空间…';
    const params=new URLSearchParams();
    let url='';
    if(mode==='concept'){params.set('subject',q);url='/api/knowledge/concept'}
    else if(mode==='author'){params.set('name',q);url='/api/knowledge/author'}
    else{params.set('name',q);url='/api/knowledge/publisher'}
    try{
      const response=await fetch(`${url}?${params}`);
      const data=await response.json();
      if(!response.ok)throw Error(data.detail||data.error||`HTTP ${response.status}`);
      setOutput(data);
      const n=data.nodes?.length??data.entries?.length??data.editions?.length??0;
      status.textContent=`完成 · ${n} 个主要节点/条目`;
    }catch(error){status.textContent=`失败：${error.message}`;out.textContent=''}
  });
}
