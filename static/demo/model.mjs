export const STORAGE_KEY = 'ntub.mid-front.state.v1';
export const PERIODS = [
  ['第一節','08:10','09:00'],['第二節','09:10','10:00'],['第三節','10:10','11:00'],
  ['第四節','11:10','12:00'],['第五節','13:30','14:20'],['第六節','14:25','15:15'],
  ['第七節','15:25','16:15'],['第八節','16:20','17:10'],['第九節','17:15','18:05'],
  ['第十節','18:30','19:15'],['第十一節','19:20','20:05'],['第十二節','20:15','21:00'],['第十三節','21:05','21:50']
];
export const COLORS = {blue:'#3264f4',red:'#dc2626',orange:'#ea580c',yellow:'#a16207',green:'#16a34a',indigo:'#4338ca',purple:'#9333ea'};
export const clone = value => JSON.parse(JSON.stringify(value));
export const uid = () => globalThis.crypto.randomUUID();
export const overlap = (a,b) => Number(a.weekday) === Number(b.weekday) && a.start < b.end && b.start < a.end;
export function validateSlot(row) {
  if (!row || typeof row.title !== 'string' || !row.title.trim() || row.title.length>100) throw Error('請輸入 1–100 字的名稱。');
  if (!Number.isInteger(Number(row.weekday)) || row.weekday<1 || row.weekday>7) throw Error('星期需為 1–7。');
  const valid = t => typeof t==='string' && /^([01]\d|2[0-3]):[0-5]\d$/.test(t);
  if (!valid(row.start)||!valid(row.end)||row.start>=row.end) throw Error('請確認時間格式，結束時間必須晚於開始時間。');
  for (const [key,max] of [['location',60],['note',2000],['period',30]]) if (row[key]!=null && (typeof row[key]!=='string'||row[key].length>max)) throw Error('地點、節次或備註內容過長。');
  return {...row,title:row.title.trim(),weekday:Number(row.weekday),location:row.location||'',note:row.note||'',period:row.period||'',color:COLORS[row.color]?row.color:'blue',visibility:row.visibility||'inherit'};
}
export function initialState() {
  return {version:1,profile:{displayName:'NTUB 展示同學',studentNumber:'ntub',email:'ntub@example.com',classId:'',bio:'',avatar:''},selected:[],customs:[],events:[],batches:[],friends:[{id:'friend-1',name:'展示同學小林',status:'accepted'},{id:'friend-2',name:'展示同學小陳',status:'incoming'}],groups:[{id:'group-1',name:'課表展示小組',description:'本機的模擬群組，邀請與活動只會保存在這個瀏覽器。',members:['ntub','展示同學小林'],events:[],tasks:[],memos:[]}],privacy:{classmates:true,friends:true,groups:false},capacities:{},students:[],roles:[]};
}
export function validateState(value,catalog) {
  if (!value || value.version!==1 || !value.profile || typeof value.profile.displayName!=='string') throw Error('不支援的備份格式。');
  for (const key of ['selected','customs','events','batches','friends','groups','students','roles']) if(!Array.isArray(value[key])||value[key].length>10000) throw Error('備份缺少必要資料或資料過多。');
  if(!value.privacy||typeof value.capacities!=='object'||!value.capacities) throw Error('備份設定格式不正確。');
  const hasText = v => typeof v==='string' && v.length<=2000;
  for (const key of ['studentNumber','email','classId','bio']) if (!hasText(value.profile[key])) throw Error('個人資料格式不正確。');
  if(typeof value.profile.avatar!=='string'||value.profile.avatar.length>300000) throw Error('頭像檔案過大。');
  if(value.profile.avatar && !/^data:image\/(png|jpeg|webp);base64,/.test(value.profile.avatar)) throw Error('頭像格式不正確。');
  for(const item of value.selected) if(!item||!hasText(item.id)||!catalog.offerings.some(o=>o.id===item.offeringId)) throw Error('備份包含不存在的課程。');
  for(const item of value.customs) {if(!hasText(item.id)) throw Error('行程編號不正確。'); validateSlot(item);}
  for(const event of value.events) {if(!hasText(event.id)) throw Error('行程編號不正確。');validateEvent(event);}
  for(const group of value.groups) {
    if(!group||!hasText(group.id)||!hasText(group.name)||!hasText(group.description)) throw Error('群組格式不正確。');
    for(const key of ['members','events','tasks','memos']) if(!Array.isArray(group[key])||group[key].length>10000) throw Error('群組資料不正確。');
    if(!group.members.every(hasText)) throw Error('群組成員格式不正確。');
    for(const e of group.events) validateEvent(e);
    for(const task of group.tasks) if(!task||!hasText(task.id)||!hasText(task.title)||typeof task.done!=='boolean') throw Error('待辦格式不正確。');
    for(const memo of group.memos) if(!memo||!hasText(memo.id)||!hasText(memo.title)||!hasText(memo.body)) throw Error('記事格式不正確。');
  }
  for(const f of value.friends) if(!f||!hasText(f.id)||!hasText(f.name)||!['accepted','incoming','outgoing'].includes(f.status)) throw Error('好友資料不正確。');
  for(const b of value.batches) if(!b||!hasText(b.id)||!hasText(b.label)||!hasText(b.created)) throw Error('匯入紀錄格式不正確。');
  for(const s of value.students) if(!s||!hasText(s.id)||!hasText(s.name)||!hasText(s.email)) throw Error('學生名單格式不正確。');
  for(const r of value.roles) if(!r||!hasText(r.id)||!hasText(r.name)||!['student','school','admin'].includes(r.role)) throw Error('身分格式不正確。');
  for(const [id,capacity] of Object.entries(value.capacities)) if(!catalog.offerings.some(o=>String(o.id)===id)||!Number.isInteger(capacity)||capacity<0||capacity>9999) throw Error('名額格式不正確。');
  return clone(value);
}
export function validateEvent(row) {
  const dateTime = value => typeof value==='string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(value) && Number.isFinite(new Date(value).valueOf());
  if (!row || typeof row.title!=='string'||!row.title.trim()||row.title.length>100||!dateTime(row.start)||!dateTime(row.end)||row.start>=row.end) throw Error('請輸入行程名稱與正確的開始、結束日期時間。');
  return {...row,title:row.title.trim(),color:COLORS[row.color]?row.color:'blue',location:String(row.location||'').slice(0,60),note:String(row.note||'').slice(0,2000)};
}
export function getItems(state,catalog) {
  return [...state.selected.flatMap(s=>{
    const o=catalog.offerings.find(o=>o.id===s.offeringId);
    return o?o.slots.map(slot=>({...slot,id:s.id,offeringId:o.id,title:o.name,location:slot.room,teacher:o.teacher,color:s.color||'blue',note:s.note||'',kind:'course'})):[];
  }),...state.customs.map(s=>({...s,kind:s.source==='excel'?'excel':'custom'}))];
}
export function buildGrid(items,{full=true}={}) {
  const intervals = new Map((full?PERIODS.slice(0,items.some(i=>i.end>'18:05')?13:9):[]).map(p=>[p.slice(1).join('|'),p]));
  for(const item of items) {
    const key=[item.start,item.end].join('|');
    if(!intervals.has(key)) intervals.set(key,PERIODS.find(p=>p[1]===item.start&&p[2]===item.end)||[item.period||'彈性時段',item.start,item.end]);
  }
  return [...intervals.values()].sort((a,b)=>a[1].localeCompare(b[1])||a[2].localeCompare(b[2])).map(period=>({period,days:Array.from({length:7},(_,day)=>items.filter(i=>i.weekday===day+1&&i.start===period[1]&&i.end===period[2]))}));
}
export function createStore(storage,catalog) {
  let current;
  try {
    const raw=storage.getItem(STORAGE_KEY);
    current=raw?validateState(JSON.parse(raw),catalog):initialState();
    if(!raw) storage.setItem(STORAGE_KEY,JSON.stringify(current));
  } catch(error) {throw Error('無法讀取瀏覽器資料。原始資料仍保留，請匯出備份或使用資料復原功能。 '+error.message);}
  function transact(fn) {
    const draft=clone(current), result=fn(draft);
    const validated=validateState(draft,catalog);
    try {storage.setItem(STORAGE_KEY,JSON.stringify(validated));}
    catch {throw Error('瀏覽器儲存空間不足或被封鎖，本次變更尚未儲存。請先匯出備份。');}
    current=validated;
    return result;
  }
  const conflicts=(row,exclude)=>getItems(current,catalog).filter(i=>i.id!==exclude&&overlap(i,row));
  const previewRows = rows => rows.map((row,index)=>{
    const valid=validateSlot(row);
    const duplicate=getItems(current,catalog).some(i=>i.title===valid.title&&i.weekday===valid.weekday&&i.start===valid.start&&i.end===valid.end);
    const clashes=[...conflicts(valid),...rows.slice(0,index).filter(i=>overlap(valid,i))];
    return {...valid,duplicate,conflicts:clashes.map(i=>i.title)};
  });
  const addOffering=(id,batch=null)=>transact(s=>{
    const o=catalog.offerings.find(o=>o.id===Number(id)); if(!o) throw Error('找不到此課程。');
    if(s.selected.some(i=>i.offeringId===o.id)) return 'duplicate';
    const clash=o.slots.flatMap(slot=>getItems(s,catalog).filter(i=>overlap(slot,i)));
    if(clash.length) throw Error('課程衝堂：'+[...new Set(clash.map(i=>i.title))].join('、'));
    s.selected.push({id:uid(),offeringId:o.id,batch,color:'blue',note:''}); return 'added';
  });
  return {
    snapshot:()=>clone(current),transact,conflicts,previewRows,addOffering,
    restore(raw) {const imported=validateState(JSON.parse(raw),catalog);return transact(s=>{Object.assign(s,imported);});},
    reset:()=>transact(s=>Object.assign(s,initialState())),
    removeOffering:id=>transact(s=>{s.selected=s.selected.filter(i=>i.offeringId!==Number(id));}),
    saveCustom:row=>transact(s=>{
      const valid=validateSlot(row), existing=s.customs.find(i=>i.id===valid.id);
      const item={...(existing||{}),...valid,id:existing?.id||uid(),source:existing?.source||'personal'};
      if(existing) s.customs[s.customs.indexOf(existing)]=item; else s.customs.push(item);return item.id;
    }),
    deleteCustom:id=>transact(s=>{s.customs=s.customs.filter(i=>i.id!==id);}),
    saveEvent:(row,groupId)=>transact(s=>{
      const valid=validateEvent(row), group=groupId?s.groups.find(g=>g.id===groupId):null;
      if(groupId&&!group) throw Error('群組不存在。');
      const list=group?group.events:s.events, old=list.find(e=>e.id===valid.id);
      const item={...valid,id:old?.id||uid()}; if(old) list[list.indexOf(old)]=item; else list.push(item);return item.id;
    }),
    deleteEvent:(id,groupId)=>transact(s=>{
      if(groupId) {const g=s.groups.find(g=>g.id===groupId);if(g) g.events=g.events.filter(e=>e.id!==id);}
      else s.events=s.events.filter(e=>e.id!==id);
    }),
    confirmImport:(rows,label,{skipConflicts=true}={})=>transact(s=>{
      if(!rows.length||rows.length>200) throw Error('單次請匯入 1–200 個時段。');
      const batch=uid();let added=0,duplicates=0,conflicts=0;
      for(const row of rows) {
        const valid=validateSlot(row), items=getItems(s,catalog);
        if(items.some(i=>i.title===valid.title&&i.weekday===valid.weekday&&i.start===valid.start&&i.end===valid.end)) {duplicates++;continue;}
        if(skipConflicts&&items.some(i=>overlap(i,valid))) {conflicts++;continue;}
        s.customs.push({...valid,id:uid(),source:'excel',batch});added++;
      }
      if(added) s.batches.push({id:batch,label:String(label).slice(0,120),source:'excel',created:new Date().toISOString()});
      return {added,duplicates,conflicts};
    }),
    importClass:classId=>transact(s=>{
      if(!catalog.classes.some(c=>c.id===classId)) throw Error('請先選擇班級。');
      const batch=uid();let added=0,duplicates=0,conflicts=0;
      for(const o of catalog.offerings.filter(o=>o.classes.includes(classId))) {
        if(s.selected.some(i=>i.offeringId===o.id)) {duplicates++;continue;}
        if(o.slots.some(slot=>getItems(s,catalog).some(i=>overlap(slot,i)))) {conflicts++;continue;}
        s.selected.push({id:uid(),offeringId:o.id,batch,color:'blue',note:''});added++;
      }
      if(added) s.batches.push({id:batch,label:catalog.classes.find(c=>c.id===classId).name,source:'class',created:new Date().toISOString()});
      return {added,duplicates,conflicts};
    }),
    undoBatch:id=>transact(s=>{s.selected=s.selected.filter(i=>i.batch!==id);s.customs=s.customs.filter(i=>i.batch!==id);s.batches=s.batches.filter(i=>i.id!==id);}),
    clearImported:()=>transact(s=>{s.selected=s.selected.filter(i=>!i.batch);s.customs=s.customs.filter(i=>i.source!=='excel');s.batches=[];}),
    clearCourses:()=>transact(s=>{s.selected=[];s.customs=s.customs.filter(i=>i.source!=='excel');s.batches=[];})
  };
}
