import {createStore,initialState,validateState,STORAGE_KEY,PERIODS,COLORS,getItems,buildGrid,uid,validateEvent} from './model.mjs';
import {parseTables,readSpreadsheet} from './import.mjs';
import {resolveRoute} from './routes.mjs';

const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const button=(label,action,id='',className='btn btn-outline')=>`<button type="button" class="${className}" data-action="${action}" data-id="${esc(id)}">${label}</button>`;
const link=(label,url,className='')=>`<a class="${className}" href="${url}">${label}</a>`;
const field=(label,name,value='',type='text',extra='')=>`<label class="demo-field">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const select=(label,name,options,value='')=>`<label class="demo-field">${label}<select name="${name}">${options.map(([v,l])=>`<option value="${esc(v)}" ${String(v)===String(value)?'selected':''}>${esc(l)}</option>`).join('')}</select></label>`;
const textarea=(label,name,value='')=>`<label class="demo-field">${label}<textarea name="${name}" maxlength="2000" rows="3">${esc(value)}</textarea></label>`;
const empty=(title,body='')=>`<div class="workspace-empty"><h3>${esc(title)}</h3><p>${body}</p></div>`;
const panel=(title,body)=>`<section class="panel"><h2 class="panel-title">${title}</h2>${body}</section>`;
const heading=(title,subtitle='',action='')=>`<header class="workspace-page-head"><div><p>NTUB 個人課表 · 前端展示</p><h1>${title}</h1><span>${subtitle}</span></div>${action}</header>`;
const days=['一','二','三','四','五','六','日'];
const dayOptions=days.map((d,i)=>[i+1,'星期'+d]);
const today=()=>new Date().toLocaleDateString('en-CA');
const dateString=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const shiftDate=(text,delta)=>{const d=new Date(text+'T12:00:00');d.setDate(d.getDate()+delta);return dateString(d);};
const AUTH='ntub.mid-front.session',ROLE='ntub.mid-front.role',PREVIEW='ntub.mid-front.preview';
let catalog,store,state,path,query,role='student',busy=false,noticeTimer;
const className=id=>catalog.classes.find(c=>c.id===id)?.name||'未選擇班級';
const offering=id=>catalog.offerings.find(o=>o.id===Number(id));
const selected=id=>state.selected.some(i=>i.offeringId===Number(id));
const items=()=>getItems(state,catalog);
function authenticated() {return sessionStorage.getItem(AUTH)==='ntub'||localStorage.getItem(AUTH)==='ntub';}
function notify(text,error=false) {const n=$('#notice');n.textContent=text;n.className=error?'demo-toast error':'demo-toast';clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>n.className='',6500);}
function navigate(url,replace=false) {if(replace)history.replaceState({},'',url);else history.pushState({},'',url);$('#dialog').close();render();window.scrollTo(0,0);}
function modal(title,body) {const d=$('#dialog');d.innerHTML=`<h2 id="dialog-title">${esc(title)}</h2>${body}<div class="demo-dialog-foot">${button('關閉','close')}</div>`;d.showModal();d.querySelector('input:not([type=hidden]),select,textarea,button')?.focus();}
function confirmAction(title,message,action,id='') {modal(title,`<p>${esc(message)}</p><div class="demo-actions">${button('確定','confirmed-'+action,id,'btn btn-danger')}${button('取消','close')}</div>`);}
function submitButton(text='儲存') {return `<p class="demo-form-error" role="alert" id="form-error"></p><button class="btn btn-primary" type="submit">${text}</button>`;}
function download(name,text,type='application/json') {const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function table(headers,rows) {return `<div class="demo-table-scroll"><table class="data-table"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${headers.length}">目前沒有資料</td></tr>`}</tbody></table></div>`;}
function row(cells) {return `<tr>${cells.map(c=>`<td>${c}</td>`).join('')}</tr>`;}
function formError(error) {if($('#form-error'))$('#form-error').textContent=error.message;notify(error.message,true);}
function colorSelect(value='blue') {return select('顏色','color',Object.keys(COLORS).map((v,i)=>[v,['藍','紅','橙','黃','綠','靛','紫'][i]]),value);}
function checked(name,label,value) {return `<label class="demo-check"><input type="checkbox" name="${name}" ${value?'checked':''}>${label}</label>`;}
function readPreview() {try{const p=JSON.parse(sessionStorage.getItem(PREVIEW)||'null');return p&&Date.now()-p.created<900000?p:null;}catch{return null;}}

function loginPage(register=false) {
 document.body.className='is-anonymous';
 return `<div class="signin-page"><header class="signin-header">${link('<img src="/static/img/timetable-icon.svg" alt="" width="32" height="32">NTUB Django','/','signin-brand')}${link('回首頁','/')}</header><main id="main-content" class="signin-main"><section class="signin-form-panel"><h1>${register?'建立學生資料':'登入'}</h1><p class="signin-intro">${register?'建立這個瀏覽器的展示資料；登入一律使用 ntub / 12345678。':'課堂展示帳號 ntub，密碼 12345678。'}</p><form data-form="${register?'register':'login'}" class="signin-form">${register?`<div class="signin-register-identifiers">${field('學號','studentNumber','','text','required maxlength="30"')}${field('Email','email','','email','required maxlength="100"')}</div><div class="signin-field">${field('顯示名稱','displayName','','text','required maxlength="60"')}</div>`:`<div class="signin-field"><label for="id_username">帳號</label><input id="id_username" name="username" autocomplete="username" required placeholder="ntub"></div>`}<div class="signin-field"><label for="id_password">密碼</label><div class="signin-password"><input id="id_password" name="password" type="password" autocomplete="current-password" required placeholder="12345678">${button('顯示','toggle-password','','demo-password-toggle')}</div></div>${checked('remember','保持登入（此瀏覽器）',true)}<p id="form-error" class="signin-error" role="alert"></p><button type="submit" class="signin-submit">${register?'建立資料並進入':'登入帳號'}</button></form><p class="signin-register">${link(register?'返回登入':'建立學生資料',register?'/accounts/login/':'/accounts/register/')}</p><p class="signin-help">這是前端展示，並非正式帳號驗證。資料僅儲存在目前的瀏覽器；清除網站資料會移除紀錄。</p></section></main><footer class="signin-footer">NTUB Django · 課表與選課</footer></div>`;
}
function landing() {
 document.body.className='is-anonymous';
 return `<div class="site-landing"><header class="site-header"><div class="site-header-inner">${link('<img src="/static/img/timetable-icon.svg" alt="">NTUB Django','/','site-brand')}<nav class="landing-navigation">${link('課程查詢','/courses/browse/')}${link('使用方式','/#features')}${link('登入','/accounts/login/')}${link('建立資料','/accounts/register/','site-button')}</nav></div></header><main id="main-content"><section class="site-intro"><div class="site-intro-inner"><div class="site-copy"><p>國立臺北商業大學 · 課表服務</p><h1>這學期，<br>安排好了。</h1><p>查課程、排課表，也把社團和自己的時間放進來。每天要去哪裡，一眼就能找到。</p><div class="site-actions">${link('開啟我的課表 →','/accounts/login/','site-button site-button-light')}${link('先找找課程','/courses/browse/')}</div></div><div class="site-preview"><div class="site-preview-head"><strong>我的一週</strong><span>課表示意</span></div><div class="site-preview-tabs"><span>我的課表</span><span>個人行程</span></div><div class="site-week"><span></span>${days.slice(0,5).map(d=>`<b>${d}</b>`).join('')}${['09:00','11:00','13:00'].map((t,i)=>`<small>${t}</small>${Array.from({length:5},(_,j)=>j===i||j===i+2?`<i class="${i===1?'green':''}">${['會計學','英文','社團活動'][i]}<small>${t} – ${i===2?'15:00':'12:00'}</small></i>`:'<span></span>').join('')}`).join('')}</div><div class="site-preview-foot">課程與個人行程，放在同一個地方。</div></div></div></section><div class="site-data"><span><strong>${catalog.classes.length}</strong> 個班級</span><span><strong>${new Set(catalog.offerings.map(o=>o.code)).size}</strong> 門課程</span><span><strong>${catalog.offerings.length}</strong> 筆開課資料</span>${link('瀏覽本學期課程 →','/courses/browse/')}</div><section class="site-features" id="features"><h2>從找課，到排好一週。</h2><p>前端展示版 · 帳號 ntub / 密碼 12345678 · 資料存在這個瀏覽器。</p><div class="site-feature-grid">${[['找合適的課','依課名、系所與學制查詢。','/courses/browse/'],['安排課程與生活','匯入班級或 Excel，再加入自己的行程。','/selection/timetable/'],['帶著課表出門','開啟列印版，或匯出資料備份。','/selection/timetable/print/']].map(([t,d,u])=>`<article><h3>${t}</h3><p>${d}</p>${link('前往 →',u)}</article>`).join('')}</div></section></main><footer class="site-footer"><strong>NTUB Django</strong><span>課程與生活，各有安排。</span>${link('登入系統','/accounts/login/')}</footer></div>`;
}
function shell(content) {
 const school=role==='school',admin=role==='admin'; document.body.className=school||admin?'is-school-view':'is-student-view';
 const nav=school? [['校務總覽','/school/'],['班級課表','/school/classes/'],['開課名額','/school/offerings/'],['全校課程','/school/courses/'],['匯入學生','/school/students/import/']]:admin?[['管理總覽','/admin/'],['帳號與身分','/accounts/roles/'],['開課管理','/school/offerings/'],['學期設定','/selection/console/']]:[['今日總覽','/'],['我的課表','/selection/timetable/'],['我的日曆','/selection/calendar/'],['尋找課程','/courses/browse/'],['好友與群組','/accounts/connections/']];
 nav.push(['個人資料','/accounts/profile/'],['資料與備份','/demo/storage/']);
 return `<header class="topbar"><div class="container topbar-inner">${link('<img src="/static/img/timetable-icon.svg" class="workspace-brand-icon" alt="">NTUB Django','/','brand')}<nav class="demo-topnav"><span class="demo-badge">前端展示</span><label>展示身分 <select id="role-switch" aria-label="展示身分"><option value="student" ${role==='student'?'selected':''}>學生</option><option value="school" ${school?'selected':''}>學校端</option><option value="admin" ${admin?'selected':''}>管理員</option></select></label><span>${esc(state.profile.displayName)}</span>${button('登出','logout','','navigation-logout')}</nav></div></header><aside class="workspace-sidebar"><div class="workspace-profile"><span class="workspace-avatar">${state.profile.avatar?`<img alt="頭像" src="${esc(state.profile.avatar)}">`:'n'}</span><strong>${esc(state.profile.displayName)}</strong><span>${school?'教務／行政':admin?'管理員':'我的學習空間'}</span></div><nav class="workspace-links">${nav.map(([l,u])=>link(l,u,path===u?'is-active':'')).join('')}</nav><div class="workspace-sidebar-note"><strong>NTUB Django</strong><span>課程與行程，在這裡整理。</span></div></aside><nav class="demo-mobile-nav" aria-label="工作區導覽">${nav.map(([l,u])=>link(l,u,path===u?'active':'')).join('')}</nav><main class="container main-content" id="main-content">${content}</main><footer class="footer"><p>NTUB Django · 前端展示 · 資料只存在此瀏覽器</p></footer>`;
}
function dashboard() {
 const list=items(),todayDay=new Date().getDay()||7;
 return heading(`你好，${esc(state.profile.displayName)}`,`${esc(className(state.profile.classId))} · ${esc(catalog.term)}`,link('開啟我的課表','/selection/timetable/','btn btn-primary'))+`<section class="workspace-metrics"><article><span>已排入課程</span><strong>${state.selected.length+new Set(state.customs.filter(i=>i.source==='excel').map(i=>i.title)).size}<small>門</small></strong>${link('管理課程 →','/selection/timetable/')}</article><article><span>每週上課時段</span><strong>${list.filter(i=>i.kind!=='custom').length}<small>節</small></strong><span>${esc(catalog.term)}</span></article><article><span>個人行程</span><strong>${state.customs.filter(i=>i.source!=='excel').length+state.events.length}<small>項</small></strong>${link('新增行程 →','/selection/calendar/events/new/')}</article></section><div class="workspace-dashboard"><section class="workspace-section"><header><h2>今日安排</h2><span>星期${days[todayDay-1]}</span></header>${agendaFor(today())}</section><aside class="workspace-section"><header><h2>常用工具</h2></header><nav class="workspace-tools">${[['課程查詢','/courses/browse/'],['Excel 匯入','/selection/import/excel/'],['完整日曆','/selection/calendar/'],['列印課表','/selection/timetable/print/']].map(([l,u])=>link(`<strong>${l}</strong><span>開啟 →</span>`,u)).join('')}</nav></aside></div>`+panel('本週總覽',`<div class="workspace-week-list">${days.map((d,i)=>`<article><strong>星期${d}</strong><span>${list.filter(item=>item.weekday===i+1).sort((a,b)=>a.start.localeCompare(b.start)).map(item=>`${item.start} ${esc(item.title)}`).join('、')||'沒有安排'}</span></article>`).join('')}</div>`);
}
function courseSlots(o) {return `<ul class="catalog-slots">${o.slots.map(s=>`<li>週${days[s.weekday-1]} · ${s.start}–${s.end} · ${esc(s.room)}</li>`).join('')}</ul>`;}
function courseCard(o,school=false) {return `<article class="catalog-course"><div class="catalog-course-info"><div class="catalog-course-code">${esc(o.code)} <span>開課序號 ${esc(o.serial)}</span>${selected(o.id)?'<span class="catalog-status">已排入課表</span>':''}</div><h3>${link(esc(o.name),`/courses/offering/${o.id}/`)}</h3><div class="catalog-course-facts"><span>授課教師 <strong>${esc(o.teacher||'待公布')}</strong></span><span>名額 <strong>${state.capacities[o.id]??o.capacity} 人</strong></span></div><p class="catalog-classes">${o.classes.map(className).map(esc).join(' · ')}</p>${courseSlots(o)}</div><div class="catalog-course-actions">${link('課程詳情 →',`/courses/offering/${o.id}/`)}${school?button('調整名額','capacity',o.id):authenticated()?button(selected(o.id)?'移出課表':'加入課表',selected(o.id)?'remove-course':'add-course',o.id,selected(o.id)?'catalog-remove':'catalog-add'):link('登入加入','/accounts/login/')}</div></article>`;}
function browse(school=false) {
 const q=(query.get('q')||'').trim().toLowerCase(),edu=query.get('edu')||'',dept=query.get('dept')||'',grade=query.get('grade')||'';
 const filtered=catalog.offerings.filter(o=>(!q||[o.name,o.code,o.teacher].some(v=>v.toLowerCase().includes(q)))&&o.classes.some(id=>{const c=catalog.classes.find(c=>c.id===id);return (!edu||c.edu===edu)&&(!dept||c.dept===dept)&&(!grade||c.code.slice(-3,-2)===grade);}));
 const size=15,total=Math.max(1,Math.ceil(filtered.length/size)),page=Math.min(total,Math.max(1,Number(query.get('page'))||1));
 return `<div class="catalog-workspace">${heading(school?'全校課程清單':'課程查詢','找課程、確認上課時間，再加入個人課表。',link('回我的課表 →','/selection/timetable/'))}<form data-form="search" class="catalog-search">${field('課名、課號或教師','q',q,'search','maxlength="80"')}${select('學制','edu',[['','全部學制'],...catalog.edus.map(e=>[e.id,e.name])],edu)}${select('系所','dept',[['','全部系所'],...catalog.departments.filter(d=>!edu||d.edu===edu).map(d=>[d.id,d.name])],dept)}${select('年級','grade',[['','全部年級'],...Array.from({length:5},(_,i)=>[i+1,(i+1)+' 年級'])],grade)}<div class="catalog-search-actions"><button type="submit" class="schedule-primary">搜尋課程</button>${link('清除條件',path)}</div></form><div class="catalog-results-head"><h2>查詢結果 <span>${filtered.length} 筆開課</span></h2><span>第 ${page} / ${total} 頁</span></div><div class="catalog-results">${filtered.slice((page-1)*size,page*size).map(o=>courseCard(o,school)).join('')||empty('沒有符合條件的課程','請換一個關鍵字，或清除篩選條件。')}</div><nav class="demo-pagination" aria-label="分頁">${page>1?link('← 上一頁',pageUrl(page-1),'btn btn-outline'):''}<span>${page} / ${total}</span>${page<total?link('下一頁 →',pageUrl(page+1),'btn btn-outline'):''}</nav></div>`;
}
function pageUrl(page) {const q=new URLSearchParams(query);q.set('page',page);return path+'?'+q;}
function courseDetail(id,roster=false) {
 const o=offering(id);if(!o)return missing('找不到此課程');
 if(roster) return heading('修課名單',esc(o.name),link('回課程詳情',`/courses/offering/${o.id}/`,'btn btn-outline'))+panel('展示名單',table(['學號','姓名','Email'],[...(selected(o.id)?[row(['ntub',esc(state.profile.displayName),esc(state.profile.email)])]:[]),...state.students.map(s=>row([esc(s.id),esc(s.name),esc(s.email)]))]))+`<p class="demo-muted">名單為目前瀏覽器的展示資料，未連線學校系統。</p>`;
 return heading(esc(o.name),`${esc(o.code)} · 開課序號 ${esc(o.serial)}`,link('返回課程查詢','/courses/browse/','btn btn-outline'))+panel('開課資訊',`<div class="demo-facts"><p>授課教師：${esc(o.teacher)}</p><p>名額：${state.capacities[o.id]??o.capacity} 人</p><p>班級：${o.classes.map(className).map(esc).join(' · ')}</p></div>${courseSlots(o)}<div class="demo-actions">${button(selected(o.id)?'移出課表':'加入我的課表',selected(o.id)?'remove-course':'add-course',o.id,'btn btn-primary')}${selected(o.id)?button('顏色與備註','course-pref',o.id):''}${role!=='student'?button('調整名額','capacity',o.id):''}${link('查看修課名單',`/courses/offering/${o.id}/roster/`,'btn btn-outline')}</div>`);
}
function timetableGrid(list,editable=true) {
 return `<div class="timetable-frame"><div class="timetable-scroll"><table class="timetable timetable-app-grid"><thead><tr><th class="tt-corner">節次</th>${days.map(d=>`<th class="tt-weekday-head"><span class="tt-day-label">週${d}</span></th>`).join('')}</tr></thead><tbody>${buildGrid(list).map(({period,days:cells})=>`<tr><th class="tt-period"><span class="tt-period-name">${esc(period[0])}</span><small class="tt-period-time">${period[1]}–${period[2]}</small></th>${cells.map((day,index)=>`<td class="tt-cell" data-grid-day="${index+1}" data-start="${period[1]}" data-end="${period[2]}">${day.map(i=>`<div class="tt-card tt-custom-card" style="--tt-accent:${COLORS[i.color]||COLORS.blue};--tt-wash:#edf2ff"><div class="tt-card-head"><span class="tt-tag">${i.kind==='course'?'我的課程':i.kind==='excel'?'Excel 課程':'個人行程'}</span>${editable?button('×',i.kind==='course'?'remove-course':'delete-custom',i.kind==='course'?i.offeringId:i.id,'tt-del-btn'):''}</div>${i.kind==='course'?link(`<strong class="tt-name">${esc(i.title)}</strong>`,`/courses/offering/${i.offeringId}/`):editable?button(`<strong class="tt-name">${esc(i.title)}</strong>`,'edit-custom',i.id,'tt-edit-event'):`<strong class="tt-name">${esc(i.title)}</strong>`}<div class="tt-meta">${esc(i.location)}</div>${i.teacher?`<div class="tt-meta">${esc(i.teacher)}</div>`:''}${i.note?`<div class="tt-meta tt-note">${esc(i.note)}</div>`:''}</div>`).join('')}${editable?`<button type="button" class="tt-create-event" data-action="new-custom" data-day="${index+1}" data-start="${period[1]}" data-end="${period[2]}" aria-label="星期${days[index]} ${period[1]} 新增行程"><span aria-hidden="true">＋</span></button>`:''}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div>`;
}
function timetable(print=false,shared=false) {
 const list=shared?sharedItems():items();
 if(print) return `<div class="demo-print-controls">${button('列印／存成 PDF','print','','btn btn-primary')}${link('返回課表','/selection/timetable/','btn btn-outline')}</div><h1>${shared?'同學':esc(state.profile.displayName)}的課表</h1><p>${esc(catalog.term)}</p><div class="schedule-workspace">${timetableGrid(list,false)}</div>`;
 return `<div class="schedule-workspace">${heading(shared?'同學課表':'我的課表',shared?'同學與好友為前端模擬資料，可用來展示分享介面。':'課程與個人行程',link('查詢與加入課程','/courses/browse/','btn btn-primary'))}<div class="schedule-toolbar"><div class="schedule-summary"><span><strong>${list.length}</strong> 個每週時段</span></div><nav>${link('完整日曆','/selection/calendar/')}${link('Excel／匯入紀錄','/selection/import/excel/')}${link('匯入班級','#import-class-section')}${button('同學課表','classmates')}${link('列印','/selection/timetable/print/')}${!shared?button('新增每週行程','new-custom'):''}</nav></div>${!shared?'<p class="schedule-grid-hint">點選空白時段新增行程，也可拖曳同一天的時段選擇起訖時間。</p>':''}${timetableGrid(list,!shared)}${shared?'':panel('已排入課程',state.selected.map(s=>{const o=offering(s.offeringId);return `<div class="demo-list-row"><div><strong>${link(esc(o.name),`/courses/offering/${o.id}/`)}</strong><small>${esc(o.teacher)}</small></div><div class="demo-actions">${button('顏色與備註','course-pref',o.id)}${button('移出課表','remove-course',o.id)}</div></div>`;}).join('')||empty('尚未加入課程',link('去全校課程查詢挑課 →','/courses/browse/')))+panel(`個人行程與 Excel 課程（${state.customs.length} 項）`,state.customs.map(i=>`<div class="demo-list-row"><div><strong>${esc(i.title)}</strong><small>星期${days[i.weekday-1]} ${i.start}–${i.end} · ${esc(i.location)} ${i.source==='excel'?'· Excel 課程':''}</small></div><div class="demo-actions">${button('編輯','edit-custom',i.id)}${button('刪除','delete-custom',i.id)}</div></div>`).join('')||empty('還沒有個人行程',button('新增每週行程','new-custom')))+classImport()+importTools()}</div>`;
}
function classImport() {return `<section class="panel" id="import-class-section"><h2 class="panel-title">匯入班級課表</h2><p class="panel-sub">選擇班級帶入全部課程，重複與衝堂時段會自動略過。</p><form data-form="class-import" class="demo-form">${classFilters(state.profile.classId)}${submitButton('開始匯入班級課表')}</form></section>`;}
function classFilters(value='') {const c=catalog.classes.find(c=>c.id===value),edu=c?.edu||'',dept=c?.dept||'';return `${select('依學制篩選','classEdu',[['','全部學制'],...catalog.edus.map(e=>[e.id,e.name])],edu)}${select('依系所篩選','classDept',[['','全部系所'],...catalog.departments.filter(d=>!edu||d.edu===edu).map(d=>[d.id,d.name])],dept)}${select('選擇班級','classId',[['','請選擇班級'],...catalog.classes.filter(c=>(!edu||c.edu===edu)&&(!dept||c.dept===dept)).map(c=>[c.id,c.name])],value)}`;}
function importTools() {return `<section class="panel" id="import-tools"><h2 class="panel-title">Excel 匯入與課程清理</h2><div class="demo-actions">${link('從 Excel 匯入課表','/selection/import/excel/','btn btn-primary')}${button('批次刪除匯入課程','clear-imported')}${button('清空所有已加入課程','clear-courses')}</div><h3>最近匯入紀錄</h3>${state.batches.slice().reverse().map(b=>`<div class="demo-list-row"><div><strong>${esc(b.label)}</strong><small>${new Date(b.created).toLocaleString()} · ${b.source==='excel'?'Excel':'班級'}匯入</small></div>${button('撤銷本次匯入','undo-batch',b.id)}</div>`).join('')||'<p class="empty-hint">還沒有匯入紀錄。</p>'}</section>`;}
function excelPage() {
 const preview=readPreview();let body=panel('從學校匯出的 Excel 匯入課表',`<p class="panel-sub">支援 .xlsx、.xls、CSV，單次最多 2 MB、200 個時段。檔案只在此瀏覽器處理，不會上傳。</p><p>支援學校 PoolExport 個人週課表及一般課程清單。先預覽，再確認匯入。</p><div class="demo-actions">${button('下載 Excel 格式範本','excel-template')}${button('下載學校週課表範例','school-example')}</div><form data-form="excel" class="demo-form"><label class="demo-field">課表檔案<input type="file" name="file" accept=".xlsx,.xls,.csv" required></label>${submitButton('上傳並預覽')}</form>`);
 if(preview) {const rows=store.previewRows(preview.rows);body+=panel(`匯入預覽：${esc(preview.label)}`,`<p>共 ${rows.length} 個時段。預覽保留 15 分鐘。</p>${table(['課名','星期','時間','教室','檢查結果'],rows.map(r=>row([esc(r.title),'週'+days[r.weekday-1],r.start+'–'+r.end,esc(r.location),r.duplicate?'已存在，略過':r.conflicts.length?'與 '+r.conflicts.map(esc).join('、')+' 重疊':'可匯入'])))}${preview.errors?.length?`<div class="demo-warning">${preview.errors.map(esc).join('<br>')}</div>`:''}<form data-form="excel-confirm" class="demo-form">${checked('skipConflicts','略過衝堂時段',true)}${submitButton('確認匯入我的課表')}</form>`);}
 return heading('Excel 匯入課表','匯入資料會儲存在目前瀏覽器。',link('回我的課表','/selection/timetable/','btn btn-outline'))+body;
}

function datedItems(date) {
 const day=new Date(date+'T12:00:00').getDay()||7;
 const weekly=items().filter(i=>i.weekday===day).map(i=>({...i,url:i.kind==='course'?`/courses/offering/${i.offeringId}/`:'/selection/timetable/'}));
 const events=[...state.events.map(e=>({...e,url:`/selection/calendar/events/${e.id}/`})),...state.groups.flatMap(g=>g.events.map(e=>({...e,url:`/accounts/groups/${g.id}/`,kind:'群組活動'})))].filter(e=>e.start.slice(0,10)<=date&&e.end.slice(0,10)>=date).map(e=>({...e,start:e.start.slice(0,10)===date?e.start.slice(11):'00:00',end:e.end.slice(0,10)===date?e.end.slice(11):'23:59',kind:e.kind||'日期行程'}));
 return [...weekly,...events].sort((a,b)=>a.start.localeCompare(b.start));
}
function agendaFor(date) {return datedItems(date).map(i=>`<div class="workspace-agenda-row"><time>${i.start}–${i.end}</time><div><strong>${esc(i.title)}</strong><p>${esc(i.location)}</p></div>${link('查看 →',i.url)}</div>`).join('')||empty('沒有排定行程',link('新增自己的安排 →','/selection/calendar/events/new/?date='+date));}
function calendarPage() {
 const mode=['day','week','month','list'].includes(query.get('view'))?query.get('view'):'month';
 let date=query.get('date')||today();if(!/^\d{4}-\d\d-\d\d$/.test(date)||!Number.isFinite(new Date(date+'T12:00:00').valueOf()))date=today();
 let first=date,count=1,step=1;
 if(mode==='week'){first=shiftDate(date,-((new Date(date+'T12:00:00').getDay()+6)%7));count=7;step=7;}
 if(mode==='month'){first=date.slice(0,7)+'-01';first=shiftDate(first,-((new Date(first+'T12:00:00').getDay()+6)%7));count=42;step=28;}
 if(mode==='list'){count=14;step=14;}
 const shift=delta=>{if(mode!=='month')return shiftDate(date,delta*step);const d=new Date(date+'T12:00:00');d.setDate(1);d.setMonth(d.getMonth()+delta);return dateString(d);};
 return `<div class="calendar-workspace">${heading('我的日曆','固定課程、個人行程與群組活動，在同一個日曆查看。',link('＋ 新增行程','/selection/calendar/events/new/','btn btn-primary'))}<nav class="calendar-toolbar"><div class="calendar-modes">${[['day','日'],['week','週'],['month','月'],['list','行程清單']].map(([v,l])=>link(l,`?view=${v}&date=${date}`,mode===v?'active':'')).join('')}</div><div class="calendar-navigation">${link('‹',`?view=${mode}&date=${shift(-1)}`)}<strong>${date.replaceAll('-',' / ')}</strong>${link('›',`?view=${mode}&date=${shift(1)}`)}${link('今天',`?view=${mode}&date=${today()}`,'calendar-today')}</div></nav>${mode==='month'?`<div class="calendar-weekdays">${days.map(d=>`<span>週${d}</span>`).join('')}</div>`:''}<div class="calendar-days calendar-days-${mode}">${Array.from({length:count},(_,i)=>{const day=shiftDate(first,i),dateObj=new Date(day+'T12:00:00');return `<section class="calendar-day ${day===today()?'is-today':''} ${mode==='month'&&day.slice(0,7)!==date.slice(0,7)?'is-outside':''}"><header>${link(`<strong>${dateObj.getDate()}</strong><span>週${days[(dateObj.getDay()+6)%7]}</span>`,`?view=day&date=${day}`)}${link('＋','/selection/calendar/events/new/?date='+day,'calendar-day-add')}</header><div class="calendar-day-items">${datedItems(day).map(item=>`<a class="calendar-item" href="${item.url}" style="--event-color:${COLORS[item.color]||COLORS.blue}"><small>${item.start}–${item.end}</small><strong>${esc(item.title)}</strong>${mode!=='month'?`<span>${esc(item.location)}</span>`:''}</a>`).join('')||(mode!=='month'?'<span class="calendar-empty">沒有安排</span>':'')}</div></section>`;}).join('')}</div></div>`;
}
function eventFields(item={}) {return `${field('行程名稱','title',item.title||'','text','required maxlength="100"')}${field('開始時間','start',item.start||`${query.get('date')||today()}T09:00`,'datetime-local','required')}${field('結束時間','end',item.end||`${query.get('date')||today()}T10:00`,'datetime-local','required')}${field('地點','location',item.location||'','text','maxlength="60"')}${colorSelect(item.color)}${textarea('備註','note',item.note)}`;}
function eventPage(id) {const item=id?state.events.find(e=>e.id===id):null;if(id&&!item)return missing('此日期行程已不存在');return heading(item?'編輯日期行程':'新增日期行程','行程可以跨日，會保存在此瀏覽器。',link('返回日曆','/selection/calendar/','btn btn-outline'))+panel('行程內容',`<form data-form="event" data-id="${esc(id||'')}" class="demo-form">${eventFields(item||{})}${submitButton()}${item?button('刪除行程','delete-event',item.id,'btn btn-danger'):''}</form>`);}
function profilePage(member=false,id='') {
 if(member) {const f=state.friends.find(f=>f.id===id);return heading(esc(f?.name||'展示同學'),'這是一份模擬同學的公開資料。',link('回好友與群組','/accounts/connections/','btn btn-outline'))+panel('基本資料',`<p>學生 · 國立臺北商業大學</p><p>用來展示好友與課表分享，沒有連線其他人的真實帳戶。</p>${link('查看同學課表',`/selection/timetable/student/${encodeURIComponent(id)}/`,'btn btn-primary')}`);}
 const p=state.profile;
 return heading('個人資料','編輯展示名稱、班級與基本資料。',link('資料與備份','/demo/storage/','btn btn-outline'))+panel('我的基本資料',`<form data-form="profile" class="demo-form">${field('顯示名稱','displayName',p.displayName,'text','required maxlength="60"')}${field('學號','studentNumber',p.studentNumber,'text','required maxlength="30"')}${field('Email','email',p.email,'email','required maxlength="100"')}${classFilters(p.classId)}${textarea('自我介紹','bio',p.bio)}<label class="demo-field">頭像（PNG／JPEG／WebP，最大 150 KB）<input name="avatar" type="file" accept="image/png,image/jpeg,image/webp"></label>${p.avatar?`<img class="demo-avatar-preview" alt="目前頭像" src="${esc(p.avatar)}">${checked('removeAvatar','移除頭像',false)}`:''}${submitButton('儲存個人資料')}</form>`);
}
function sharedItems() {return [{id:'shared-1',title:'展示同學的程式設計',weekday:2,start:'09:10',end:'10:00',location:'電708',kind:'custom',color:'green'},{id:'shared-2',title:'展示讀書會',weekday:4,start:'13:30',end:'14:20',location:'圖書館',kind:'custom',color:'purple'}];}
function connections() {
 const privacy=panel('誰可以看我的課表？',`<p class="panel-sub">這裡儲存展示用的分享設定；不會對外傳送資料。</p><form data-form="privacy" class="demo-form">${checked('classmates','同班同學',state.privacy.classmates)}${checked('friends','已互加好友',state.privacy.friends)}${checked('groups','群組成員',state.privacy.groups)}${submitButton('儲存分享設定')}</form>`);
 const friends=panel('好友與邀請',`<form data-form="friend" class="demo-form demo-inline">${field('輸入展示同學名稱','name','','text','required maxlength="60"')}${submitButton('送出模擬邀請')}</form>${state.friends.map(f=>`<div class="demo-list-row"><div><strong>${link(esc(f.name),`/accounts/profile/${f.id}/`)}</strong><small>${{accepted:'已成為好友',incoming:'收到模擬邀請',outgoing:'等待模擬回覆'}[f.status]}</small></div><div class="demo-actions">${f.status==='accepted'?link('查看課表',`/selection/timetable/student/${f.id}/`,'btn btn-outline'):button(f.status==='incoming'?'接受邀請':'模擬對方同意','friend-accept',f.id)}${button(f.status==='accepted'?'移除好友':'取消邀請','friend-remove',f.id)}</div></div>`).join('')}`);
 const groups=panel('我的群組',`<form data-form="group-create" class="demo-form demo-inline">${field('群組名稱','name','','text','required maxlength="60"')}${submitButton('建立群組')}</form>${state.groups.map(g=>`<div class="demo-list-row"><div><strong>${link(esc(g.name),`/accounts/groups/${g.id}/`)}</strong><small>${g.members.length} 位展示成員 · ${esc(g.description)}</small></div>${link('開啟群組',`/accounts/groups/${g.id}/`,'btn btn-outline')}</div>`).join('')||empty('尚未建立群組')}`);
 return heading('好友、群組與隱私','邀請與群組操作均為本機模擬，可用來展示完整流程。')+privacy+friends+panel('同班同學',state.profile.classId?`<p>${esc(className(state.profile.classId))}</p>${link('展示同學小林的課表','/selection/timetable/student/friend-1/','btn btn-outline')}`:empty('尚未選擇班級',link('前往個人資料綁定班級 →','/accounts/profile/')))+groups;
}
function groupPage(id) {
 const g=state.groups.find(g=>g.id===id);if(!g)return missing('群組已不存在');
 const members=panel('成員與設定',`<p>${esc(g.description)}</p><p>${g.members.map(esc).join('、')}</p><div class="demo-actions">${button('編輯群組','edit-group',g.id)}${button('刪除群組','delete-group',g.id,'btn btn-danger')}</div><form data-form="group-invite" data-id="${esc(g.id)}" class="demo-form demo-inline">${field('展示成員名稱','name','','text','required maxlength="60"')}${submitButton('加入模擬成員')}</form>`);
 const events=panel('共同行程',`<div class="demo-actions">${button('新增共同行程','new-group-event',g.id)}</div>${g.events.map(e=>`<div class="demo-list-row"><div><strong>${esc(e.title)}</strong><small>${esc(e.start.replace('T',' '))} – ${esc(e.end.replace('T',' '))} · ${esc(e.location)}</small></div><div class="demo-actions">${button('編輯','edit-group-event',e.id)}${button('刪除','delete-group-event',e.id)}</div></div>`).join('')||empty('還沒有共同行程')}`);
 const tasks=panel('待辦事項',`<form data-form="group-task" data-id="${esc(g.id)}" class="demo-form demo-inline">${field('待辦內容','title','','text','required maxlength="100"')}${submitButton('新增待辦')}</form>${g.tasks.map(t=>`<div class="demo-list-row"><label class="demo-check"><input type="checkbox" data-task="${esc(t.id)}" ${t.done?'checked':''}><span class="${t.done?'demo-done':''}">${esc(t.title)}</span></label>${button('刪除','delete-task',t.id)}</div>`).join('')}`);
 const memos=panel('共享記事',`<div class="demo-actions">${button('新增記事','new-memo',g.id)}</div>${g.memos.map(m=>`<div class="demo-list-row"><div><strong>${esc(m.title)}</strong><p>${esc(m.body).replaceAll('\n','<br>')}</p></div><div class="demo-actions">${button('編輯','edit-memo',m.id)}${button('刪除','delete-memo',m.id)}</div></div>`).join('')||empty('還沒有共享記事')}`);
 return heading(esc(g.name),'群組工作區 · 所有變更都存在此瀏覽器。',link('返回好友與群組','/accounts/connections/','btn btn-outline'))+members+events+tasks+memos;
}
function classPage() {
 const cid=query.get('classId')||state.profile.classId||catalog.classes[0].id,list=catalog.offerings.filter(o=>o.classes.includes(cid));
 const slots=list.flatMap(o=>o.slots.map(s=>({...s,id:'class-'+o.id,title:o.name,offeringId:o.id,location:s.room,teacher:o.teacher,kind:'course',color:'blue'})));
 return heading('全校班級課表','選擇班級查看完整週課表。')+panel('選擇班級',`<form data-form="class-view" class="demo-form">${classFilters(cid)}${submitButton('查看課表')}</form>`)+`<div class="schedule-workspace"><h2>${esc(className(cid))}</h2>${timetableGrid(slots,false)}</div>`;
}
function schoolDashboard(admin=false) {
 return heading(admin?'管理中樞':'學校端中心','校方與管理操作為本機展示，不會修改 Mid 的正式資料。')+`<section class="workspace-metrics"><article><span>班級</span><strong>${catalog.classes.length}</strong>${link('班級課表 →','/school/classes/')}</article><article><span>開課資料</span><strong>${catalog.offerings.length}</strong>${link('管理名額 →','/school/offerings/')}</article><article><span>展示學生</span><strong>${state.students.length+1}</strong>${link('匯入學生 →','/school/students/import/')}</article></section>`+panel('管理工具',`<nav class="workspace-tools">${[['全校課程','/school/courses/'],['開課名額管理','/school/offerings/'],['班級課表','/school/classes/'],['學生資料匯入','/school/students/import/'],['帳號與身分','/accounts/roles/'],['學期與分發展示','/selection/console/'],['資料備份','/demo/storage/']].map(([l,u])=>link(`<strong>${l}</strong><span>開啟 →</span>`,u)).join('')}</nav>`);
}
function capacitiesPage() {
 const q=(query.get('q')||'').toLowerCase(),all=catalog.offerings.filter(o=>(o.name+' '+o.code).toLowerCase().includes(q));
 const page=Math.min(Math.max(1,Number(query.get('page'))||1),Math.max(1,Math.ceil(all.length/25)));
 return heading('開課名額管理','修改值只儲存在本瀏覽器。')+panel('搜尋',`<form data-form="search" class="demo-form demo-inline">${field('課名或課號','q',q,'search')}${submitButton('搜尋')}</form>`)+table(['課號','課程名稱','教師','名額','操作'],all.slice((page-1)*25,page*25).map(o=>row([esc(o.code),link(esc(o.name),`/school/offerings/${o.id}/`),esc(o.teacher),state.capacities[o.id]??o.capacity,button('調整名額','capacity',o.id)])))+`<nav class="demo-pagination">${page>1?link('上一頁',pageUrl(page-1),'btn btn-outline'):''}<span>第 ${page} 頁 · 共 ${all.length} 筆</span>${page*25<all.length?link('下一頁',pageUrl(page+1),'btn btn-outline'):''}</nav>`;
}
function studentsPage() {
 let preview;try{preview=JSON.parse(sessionStorage.getItem('ntub.student-preview')||'null');}catch{preview=null;}
 return heading('匯入學生','匯入學號、姓名、Email；不建立真正的登入帳號。')+panel('上傳學生名單',`<div class="demo-actions">${button('下載學生匯入範本','students-template')}</div><form data-form="students" class="demo-form"><label class="demo-field">Excel 或 CSV<input type="file" name="file" accept=".csv,.xlsx,.xls" required></label>${submitButton('預覽學生名單')}</form>`)+(preview?panel('學生匯入預覽',table(['學號','姓名','Email'],preview.map(s=>row([esc(s.id),esc(s.name),esc(s.email)])))+button('確認匯入學生','confirm-students','','btn btn-primary')):'')+panel('展示學生名單',table(['學號','姓名','Email','操作'],state.students.map(s=>row([esc(s.id),esc(s.name),esc(s.email),button('移除','delete-student',s.id)]))));
}
function rolesPage() {const list=[{id:'ntub',name:state.profile.displayName,role:'student'},...state.roles];return heading('帳號與身分','固定登入帳號不變；以下身分只用來展示管理功能。')+panel('展示帳號',table(['帳號','名稱','展示身分','操作'],list.map(r=>row([esc(r.id),esc(r.name),{student:'學生',school:'學校端',admin:'管理員'}[r.role],r.id==='ntub'?'使用右上方切換身分':button('變更身分','edit-role',r.id)]))))+panel('新增展示身分',`<form data-form="role" class="demo-form">${field('帳號名稱','name','','text','required maxlength="60"')}${select('身分','role',[['student','學生'],['school','學校端'],['admin','管理員']])}${submitButton('新增展示帳號')}</form>`);}
function consolePage() {return heading('學期與選課分發展示','原版的分發入口保留作為本機管理展示。')+panel('目前學期',`<p>${esc(catalog.term)}</p><p>前端展示版的課表以每週固定時段呈現。</p><div class="demo-actions">${button('執行分發展示','allocation','','btn btn-primary')}${button('重設分發結果','reset-allocation')}${link('管理開課名額','/school/offerings/','btn btn-outline')}</div>${state.allocation?`<p role="status">已完成本機分發展示：目前 ${state.selected.length} 門課程。</p>`:''}`);}
function storagePage() {const size=new Blob([JSON.stringify(state)]).size;return heading('資料與備份','展示資料儲存在 localStorage，可匯出到另一台電腦。')+panel('目前瀏覽器資料',`<div class="demo-facts"><p>儲存位置：${esc(location.origin)}</p><p>資料鍵值：${STORAGE_KEY}</p><p>使用空間：約 ${Math.ceil(size/1024)} KB</p><p>${state.selected.length} 門課程 · ${state.customs.length} 個固定行程 · ${state.events.length} 個日期行程 · ${state.groups.length} 個群組</p></div><p class="demo-warning">localhost 與 127.0.0.1、不同連接埠或不同瀏覽器的資料各自獨立。請固定使用 http://localhost:8000；清除網站資料前先匯出。</p><div class="demo-actions">${button('匯出全部資料備份','export-state','','btn btn-primary')}${button('還原 JSON 備份','restore-state')}${button('重設展示資料','reset-state','','btn btn-danger')}</div><p class="demo-muted">固定帳號 ntub / 12345678 只供前端展示，不提供真實的帳號或權限保護。</p>`);}
function missing(title='找不到這個展示頁面') {return heading(esc(title),'資料可能已刪除，請從選單重新選擇。')+panel('返回工作區',`<div class="demo-actions">${link('今日總覽','/','btn btn-primary')}${link('我的課表','/selection/timetable/','btn btn-outline')}${link('課程查詢','/courses/browse/','btn btn-outline')}</div>`);}

function routeContent() {
 const route=resolveRoute(path);
 switch(route.page) {
  case 'dashboard':return dashboard();case 'browse':return browse();case 'school-browse':return browse(true);
  case 'course':return courseDetail(route.id,route.roster);case 'print':return timetable(true);
  case 'shared':return timetable(false,true);case 'timetable':return timetable();case 'excel':return excelPage();
  case 'calendar':return calendarPage();case 'new-event':return eventPage();case 'event':return eventPage(route.id);
  case 'profile':return profilePage();case 'member':return profilePage(true,route.id);case 'connections':return connections();
  case 'group':return groupPage(route.id);case 'school':return schoolDashboard();case 'admin':return schoolDashboard(true);
  case 'classes':return classPage();case 'capacities':return capacitiesPage();case 'students':return studentsPage();
  case 'roles':return rolesPage();case 'console':return consolePage();case 'storage':return storagePage();default:return missing();
 }
}
function render() {
 state=store.snapshot();path=location.pathname;if(!path.endsWith('/'))path+='/';query=new URLSearchParams(location.search);role=sessionStorage.getItem(ROLE)||'student';
 let content;
 if(['/accounts/logout/','/school/logout/'].includes(path)){logout();return;}
 if(['/accounts/login/','/accounts/register/','/school/login/','/admin/login/'].includes(path)){content=loginPage(path==='/accounts/register/');}
 else if(!authenticated()&&path==='/')content=landing();
 else if(!authenticated()&&!['/courses/browse/','/timetables/classes/'].includes(path)&&!/^\/courses\/offering\/\d+\/$/.test(path)){history.replaceState({},'','/accounts/login/?next='+encodeURIComponent(location.pathname+location.search));path='/accounts/login/';content=loginPage();}
 else content=shell(routeContent());
 $('#app').innerHTML=content;document.body.classList.toggle('demo-printing',path==='/selection/timetable/print/');document.title=($('#main-content h1')?.textContent||'NTUB Django')+' · 前端展示';
 if(query.has('next')&&path==='/accounts/login/')document.title='登入 · NTUB 前端展示';
 const hash=location.hash;if(hash)requestAnimationFrame(()=>{try{document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView();}catch{}});
}

function customDialog(id,defaults={}) {
 const item=state.customs.find(i=>i.id===id)||defaults;
 modal(id?'編輯每週行程':'新增每週行程',`<form data-form="custom" data-id="${esc(id||'')}" class="demo-form">${field('行程名稱','title',item.title||'','text','required maxlength="100"')}${select('星期','weekday',dayOptions,item.weekday||1)}${field('開始時間','start',item.start||'09:10','time','required')}${field('結束時間','end',item.end||'10:00','time','required')}${field('節次名稱（選填）','period',item.period||'','text','maxlength="30"')}${field('地點','location',item.location||'','text','maxlength="60"')}${colorSelect(item.color)}${select('可見範圍','visibility',[['inherit','依分享設定'],['private','僅自己'],['friends','好友'],['groups','群組']],item.visibility)}${textarea('備註','note',item.note)}${submitButton()}</form>`);
}
function currentGroup() {const id=path.match(/^\/accounts\/groups\/([^/]+)\/$/)?.[1];return state.groups.find(g=>g.id===id);}
function groupEventDialog(groupId,eventId) {
 const group=state.groups.find(g=>g.id===groupId),item=group?.events.find(e=>e.id===eventId);
 if(!group)throw Error('群組不存在。');
 modal(item?'編輯共同行程':'新增共同行程',`<form data-form="group-event" data-group="${esc(groupId)}" data-id="${esc(eventId||'')}" class="demo-form">${eventFields(item||{})}${submitButton()}</form>`);
}
function memoDialog(groupId,id) {const m=state.groups.find(g=>g.id===groupId)?.memos.find(m=>m.id===id);modal(m?'編輯記事':'新增共享記事',`<form data-form="memo" data-group="${esc(groupId)}" data-id="${esc(id||'')}" class="demo-form">${field('記事標題','title',m?.title||'','text','required maxlength="100"')}${textarea('內容','body',m?.body||'')}${submitButton()}</form>`);}
function logout() {sessionStorage.removeItem(AUTH);localStorage.removeItem(AUTH);sessionStorage.removeItem(ROLE);navigate('/accounts/login/',true);}
function after(message,url) {$('#dialog').close();if(url)navigate(url);else render();if(message)notify(message);}
function exportBook(name,rows) {
 if(!globalThis.XLSX)throw Error('Excel 元件未載入，請重新整理後再試。');
 const workbook=XLSX.utils.book_new();XLSX.utils.book_append_sheet(workbook,XLSX.utils.aoa_to_sheet(rows),'課表');XLSX.writeFile(workbook,name);
}
async function action(name,id,element) {
 if(name==='close'){$('#dialog').close();return;}
 if(name==='retry'){await start();return;}
 if(name==='export-raw'){download('mid-front-original-data.txt',localStorage.getItem(STORAGE_KEY)||'','text/plain');return;}
 if(name==='toggle-password'){const input=$('#id_password');input.type=input.type==='password'?'text':'password';element.textContent=input.type==='password'?'顯示':'隱藏';return;}
 if(name==='logout'){logout();return;}
 if(name==='print'){window.print();return;}
 if(name==='restore-state'){modal('還原資料備份',`<p>還原會覆蓋此瀏覽器現有的展示資料，請先匯出備份。</p><form data-form="restore" class="demo-form"><label class="demo-field">JSON 備份檔<input type="file" name="file" accept=".json,application/json" required></label>${submitButton('確認還原')}</form>`);return;}
 if(name==='reset-state'){confirmAction('重設展示資料','這會清除目前瀏覽器內的課程、行程、群組與設定，還原成初始展示資料。請先匯出備份。','reset-state');return;}
 if(name==='confirmed-reset-state'){if(store)store.reset();else{localStorage.setItem(STORAGE_KEY,JSON.stringify(initialState()));await start();}sessionStorage.removeItem(PREVIEW);after('已重設展示資料。','/');return;}
 if(!store)throw Error('請先修復或重設瀏覽器資料。');
 state=store.snapshot();
 switch(name) {
 case 'add-course': {const result=store.addOffering(id);after(result==='duplicate'?'這門課已在課表中。':'已加入課表。');break;}
 case 'remove-course':confirmAction('移出課程','確定從課表移除此課程？其他課程與行程會保留。','remove-course',id);break;
 case 'confirmed-remove-course':store.removeOffering(id);after('課程已移出。');break;
 case 'new-custom':customDialog(null,{weekday:element.dataset.day,start:element.dataset.start,end:element.dataset.end});break;
 case 'edit-custom':customDialog(id);break;
 case 'delete-custom':confirmAction('刪除每週行程','確定刪除此行程？','delete-custom',id);break;
 case 'confirmed-delete-custom':store.deleteCustom(id);after('每週行程已刪除。');break;
 case 'course-pref': {const s=state.selected.find(s=>s.offeringId===Number(id));if(!s)throw Error('此課程尚未加入。');modal('課程顏色與備註',`<form data-form="course-pref" data-id="${esc(id)}" class="demo-form">${colorSelect(s.color)}${textarea('備註','note',s.note)}${submitButton()}</form>`);break;}
 case 'undo-batch':confirmAction('撤銷匯入','只移除這批匯入新增的課程，其他資料會保留。','undo-batch',id);break;
 case 'confirmed-undo-batch':store.undoBatch(id);after('本次匯入已撤銷。');break;
 case 'clear-imported':confirmAction('批次刪除匯入','只刪除班級與 Excel 匯入的課程，保留手動加入的課程與個人行程。','clear-imported');break;
 case 'confirmed-clear-imported':store.clearImported();after('匯入課程已清除。');break;
 case 'clear-courses':confirmAction('清空所有已加入課程','移除手動加入及所有匯入的課程，保留自己的個人行程。','clear-courses');break;
 case 'confirmed-clear-courses':store.clearCourses();after('已清空課程，個人行程保留。');break;
 case 'excel-template':exportBook('timetable-import-template.xlsx',[['課程名稱','星期','開始時間','結束時間','教室','教師','備註'],['程式設計','週一','08:10','10:00','資管301','展示教師','範例資料，請替換']]);break;
 case 'school-example':exportBook('PoolExport-example.xlsx',[['節次','一','二','三','四','五','六','日'],['第五節\n13:30\n14:20','伺服器架設與規劃\n展示教師\n電707','','作業系統\n展示教師\n電703','智慧綠能\n展示教師\n藝409','社群大數據分析\n展示教師\n電607','',''],['第六節\n14:25\n15:15','伺服器架設與規劃\n展示教師\n電707','','作業系統\n展示教師\n電703','智慧綠能\n展示教師\n藝409','社群大數據分析\n展示教師\n電607','','']]);break;
 case 'delete-event':confirmAction('刪除日期行程','確定刪除此日期行程？','delete-event',id);break;
 case 'confirmed-delete-event':store.deleteEvent(id);after('日期行程已刪除。','/selection/calendar/');break;
 case 'classmates':modal('同學課表',`<p>前端展示中的模擬同學。</p><div class="demo-actions">${link('展示同學小林','/selection/timetable/student/friend-1/','btn btn-outline')}${link('展示同學小陳','/selection/timetable/student/friend-2/','btn btn-outline')}</div>`);break;
 case 'friend-accept':store.transact(s=>{const f=s.friends.find(f=>f.id===id);if(f)f.status='accepted';});after('模擬好友邀請已接受。');break;
 case 'friend-remove':confirmAction('移除好友或邀請','確定移除此筆展示好友關係？','friend-remove',id);break;
 case 'confirmed-friend-remove':store.transact(s=>{s.friends=s.friends.filter(f=>f.id!==id);});after('展示好友關係已移除。');break;
 case 'edit-group': {const g=state.groups.find(g=>g.id===id);if(!g)throw Error('群組不存在。');modal('編輯群組',`<form data-form="group-edit" data-id="${esc(g.id)}" class="demo-form">${field('群組名稱','name',g.name,'text','required maxlength="60"')}${textarea('群組說明','description',g.description)}${submitButton()}</form>`);break;}
 case 'delete-group':confirmAction('刪除群組','刪除群組及其中的展示行程、待辦與記事？','delete-group',id);break;
 case 'confirmed-delete-group':store.transact(s=>{s.groups=s.groups.filter(g=>g.id!==id);});after('群組已刪除。','/accounts/connections/');break;
 case 'new-group-event':groupEventDialog(id);break;
 case 'edit-group-event':groupEventDialog(currentGroup().id,id);break;
 case 'delete-group-event':confirmAction('刪除共同行程','確定刪除這筆群組活動？','delete-group-event',id);break;
 case 'confirmed-delete-group-event':store.deleteEvent(id,currentGroup().id);after('共同行程已刪除。');break;
 case 'delete-task':store.transact(s=>{const g=s.groups.find(g=>g.id===currentGroup().id);g.tasks=g.tasks.filter(t=>t.id!==id);});after('待辦已移除。');break;
 case 'new-memo':memoDialog(id);break;
 case 'edit-memo':memoDialog(currentGroup().id,id);break;
 case 'delete-memo':confirmAction('刪除記事','確定刪除此筆共享記事？','delete-memo',id);break;
 case 'confirmed-delete-memo':store.transact(s=>{const g=s.groups.find(g=>g.id===currentGroup().id);g.memos=g.memos.filter(m=>m.id!==id);});after('記事已刪除。');break;
 case 'capacity': {const o=offering(id);modal('調整開課名額',`<p>${esc(o.name)}</p><form data-form="capacity" data-id="${id}" class="demo-form">${field('名額','capacity',state.capacities[id]??o.capacity,'number','required min="0" max="9999" step="1"')}${submitButton()}</form>`);break;}
 case 'students-template':exportBook('student-import-template.xlsx',[['學號','姓名','Email'],['demo001','展示學生','demo001@example.com']]);break;
 case 'confirm-students': {const rows=JSON.parse(sessionStorage.getItem('ntub.student-preview')||'null');if(!Array.isArray(rows)||!rows.length)throw Error('請重新上傳學生名單。');let count=0;store.transact(s=>{for(const student of rows)if(!s.students.some(t=>t.id===student.id)){s.students.push(student);count++;}});sessionStorage.removeItem('ntub.student-preview');after(`已匯入 ${count} 位展示學生，重複學號已略過。`);break;}
 case 'delete-student':confirmAction('移除展示學生','確定移除此筆學生資料？','delete-student',id);break;
 case 'confirmed-delete-student':store.transact(s=>{s.students=s.students.filter(t=>t.id!==id);});after('展示學生已移除。');break;
 case 'edit-role': {const r=state.roles.find(r=>r.id===id);modal('變更展示身分',`<form data-form="role-edit" data-id="${esc(id)}" class="demo-form">${select('展示身分','role',[['student','學生'],['school','學校端'],['admin','管理員']],r.role)}${submitButton()}</form>`);break;}
 case 'allocation':store.transact(s=>{s.allocation=true;});after('本機分發展示已完成，已排入的課程保留。');break;
 case 'reset-allocation':store.transact(s=>{delete s.allocation;});after('分發展示狀態已重設。');break;
 case 'export-state':download('mid-front-backup-'+today()+'.json',JSON.stringify(store.snapshot(),null,2));notify('已匯出資料備份。');break;
 default:throw Error('此操作不存在，請重新整理後再試。');
 }
}
async function workbookTables(file) {
 const bytes=await readSpreadsheet(file,globalThis.XLSX);
 return new Promise((resolve,reject)=>{
  const worker=new Worker('/static/demo/import-worker.js'),timer=setTimeout(()=>{worker.terminate();reject(Error('檔案處理超過 10 秒，請另存成較小的課表檔後重試。'));},10000);
  const done=()=>{clearTimeout(timer);worker.terminate();};
  worker.onmessage=({data})=>{done();if(data.error)reject(Error(data.error));else resolve(data.tables);};
  worker.onerror=()=>{done();reject(Error('無法讀取檔案，請另存成 .xlsx 或 UTF-8 CSV 後重試。'));};
  worker.postMessage(bytes,[bytes]);
 });
}
async function submit(form) {
 const data=new FormData(form),v=Object.fromEntries(data),id=form.dataset.id;
 switch(form.dataset.form) {
 case 'login':case 'register': {
  const register=form.dataset.form==='register';
  if((!register&&v.username!=='ntub')||v.password!=='12345678')throw Error('展示帳號為 ntub，密碼為 12345678。');
  if(register)store.transact(s=>{s.profile={...s.profile,displayName:v.displayName.trim(),studentNumber:v.studentNumber.trim(),email:v.email.trim()};});
  sessionStorage.setItem(AUTH,'ntub');if(data.has('remember'))localStorage.setItem(AUTH,'ntub');else localStorage.removeItem(AUTH);
  const next=new URLSearchParams(location.search).get('next');
  const dest=next?.startsWith('/')&&!next.startsWith('//')&&!/\/(login|logout|register)\//.test(next)?next:'/';navigate(dest,true);notify('登入成功。');break;
 }
 case 'search': {const q=new URLSearchParams();for(const [key,value] of data)if(value)q.set(key,value);navigate(path+'?'+q);break;}
 case 'class-view':if(!v.classId)throw Error('請選擇班級。');navigate(path+'?classId='+encodeURIComponent(v.classId));break;
 case 'class-import':{const result=store.importClass(v.classId);after(`新增 ${result.added} 門，略過重複 ${result.duplicates} 門、衝堂 ${result.conflicts} 門。`);break;}
 case 'custom': {const clashes=store.conflicts({...v,weekday:Number(v.weekday)},id);store.saveCustom({...v,id});after(clashes.length?'每週行程已儲存；與 '+[...new Set(clashes.map(i=>i.title))].join('、')+' 時間重疊。':'每週行程已儲存。');break;}
 case 'course-pref':store.transact(s=>{const item=s.selected.find(i=>i.offeringId===Number(id));if(!item)throw Error('課程已移除。');item.color=v.color;item.note=v.note;});after('課程設定已儲存。');break;
 case 'event':store.saveEvent({...v,id});after('日期行程已儲存。','/selection/calendar/');break;
 case 'excel': {const tables=await workbookTables(data.get('file')),parsed=parseTables(tables);sessionStorage.setItem(PREVIEW,JSON.stringify({...parsed,label:data.get('file').name,created:Date.now()}));render();notify('預覽完成，請檢查後確認匯入。');break;}
 case 'excel-confirm':{const preview=readPreview();if(!preview)throw Error('預覽已過期，請重新上傳。');const result=store.confirmImport(preview.rows,preview.label,{skipConflicts:data.has('skipConflicts')});sessionStorage.removeItem(PREVIEW);after(`新增 ${result.added} 個時段，略過重複 ${result.duplicates} 個、衝堂 ${result.conflicts} 個。`,'/selection/timetable/');break;}
 case 'profile': {
   let avatar=state.profile.avatar;
   const file=data.get('avatar');if(file?.size){if(file.size>150*1024||!['image/png','image/jpeg','image/webp'].includes(file.type))throw Error('頭像請使用 150 KB 以內的 PNG／JPEG／WebP。');avatar=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('頭像讀取失敗。'));reader.readAsDataURL(file);});}
   if(data.has('removeAvatar'))avatar='';
   store.transact(s=>{s.profile={...s.profile,displayName:v.displayName.trim(),studentNumber:v.studentNumber.trim(),email:v.email.trim(),classId:v.classId,bio:v.bio,avatar};});after('個人資料已儲存。');break;
 }
 case 'privacy':store.transact(s=>{s.privacy={classmates:data.has('classmates'),friends:data.has('friends'),groups:data.has('groups')};});after('分享設定已儲存。');break;
 case 'friend':store.transact(s=>{if(s.friends.some(f=>f.name===v.name.trim()))throw Error('此展示同學已在好友或邀請名單。');s.friends.push({id:uid(),name:v.name.trim(),status:'outgoing'});});after('已建立本機模擬邀請。');break;
 case 'group-create':{const gid=uid();store.transact(s=>s.groups.push({id:gid,name:v.name.trim(),description:'',members:['ntub'],events:[],tasks:[],memos:[]}));after('群組已建立。','/accounts/groups/'+gid+'/');break;}
 case 'group-edit':store.transact(s=>{const g=s.groups.find(g=>g.id===id);g.name=v.name.trim();g.description=v.description;});after('群組設定已儲存。');break;
 case 'group-invite':store.transact(s=>{const g=s.groups.find(g=>g.id===id);if(g.members.includes(v.name.trim()))throw Error('這位成員已在群組。');g.members.push(v.name.trim());});after('模擬成員已加入。');break;
 case 'group-event':store.saveEvent({...v,id},form.dataset.group);after('共同行程已儲存。');break;
 case 'group-task':store.transact(s=>s.groups.find(g=>g.id===id).tasks.push({id:uid(),title:v.title.trim(),done:false}));after('待辦已新增。');break;
 case 'memo':store.transact(s=>{const g=s.groups.find(g=>g.id===form.dataset.group),old=g.memos.find(m=>m.id===id),item={id:old?.id||uid(),title:v.title.trim(),body:v.body};if(old)g.memos[g.memos.indexOf(old)]=item;else g.memos.push(item);});after('共享記事已儲存。');break;
 case 'capacity':store.transact(s=>{s.capacities[id]=Number(v.capacity);});after('展示名額已儲存。');break;
 case 'students': {
  const tables=await workbookTables(data.get('file'));let rows=[];
  for(const t of tables){const header=t.rows.findIndex(r=>r.includes('學號')&&r.includes('姓名')&&r.includes('Email'));if(header<0)continue;const h=t.rows[header];for(const r of t.rows.slice(header+1)){if(!r.some(x=>String(x).trim()))continue;const item={id:String(r[h.indexOf('學號')]||'').trim(),name:String(r[h.indexOf('姓名')]||'').trim(),email:String(r[h.indexOf('Email')]||'').trim()};if(!item.id||!item.name||!/^\S+@\S+\.\S+$/.test(item.email))throw Error('學生資料有缺漏，請檢查學號、姓名及 Email。');rows.push(item);}}
  if(!rows.length)throw Error('找不到學生資料，請使用下載的範本。');if(rows.length>500)throw Error('單次最多匯入 500 位展示學生。');sessionStorage.setItem('ntub.student-preview',JSON.stringify(rows));render();notify('學生名單預覽已完成。');break;
 }
 case 'role':store.transact(s=>{if(s.roles.some(r=>r.name===v.name.trim()))throw Error('展示名稱已存在。');s.roles.push({id:uid(),name:v.name.trim(),role:v.role});});after('展示身分已新增。');break;
 case 'role-edit':store.transact(s=>{s.roles.find(r=>r.id===id).role=v.role;});after('展示身分已更新。');break;
 case 'restore':{const file=data.get('file');if(file.size>6*1024*1024)throw Error('備份不得超過 6 MB。');const raw=await file.text();if(store)store.restore(raw);else{const validated=validateState(JSON.parse(raw),catalog);localStorage.setItem(STORAGE_KEY,JSON.stringify(validated));await start();}sessionStorage.removeItem(PREVIEW);after('資料備份已還原。','/demo/storage/');break;}
 default:throw Error('此表單尚無法處理，請重新整理後再試。');
 }
}

document.addEventListener('click',async event=>{
 const actionButton=event.target.closest('[data-action]');
 if(actionButton){event.preventDefault();try{await action(actionButton.dataset.action,actionButton.dataset.id,actionButton);}catch(error){formError(error);}return;}
 const a=event.target.closest('a[href]');
 if(!a||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||a.download||a.target)return;
 const url=new URL(a.href);if(url.origin!==location.origin)return;
 if(url.pathname===location.pathname&&url.hash){event.preventDefault();history.pushState({},'',url);document.getElementById(decodeURIComponent(url.hash.slice(1)))?.scrollIntoView({behavior:'smooth'});return;}
 event.preventDefault();navigate(url.pathname+url.search+url.hash);
});
document.addEventListener('submit',async event=>{
 const form=event.target.closest('form[data-form]');if(!form)return;
 event.preventDefault();if(busy)return;busy=true;const btn=form.querySelector('[type=submit]');if(btn)btn.disabled=true;
 try{await submit(form);}catch(error){formError(error);}finally{busy=false;if(btn)btn.disabled=false;}
});
document.addEventListener('change',event=>{
 try {
  if(event.target.id==='role-switch'){sessionStorage.setItem(ROLE,event.target.value);navigate(event.target.value==='school'?'/school/':event.target.value==='admin'?'/admin/':'/');}
  if(event.target.matches('[data-task]')){const g=currentGroup();store.transact(s=>{const t=s.groups.find(item=>item.id===g.id).tasks.find(t=>t.id===event.target.dataset.task);t.done=event.target.checked;});render();}
  const form=event.target.closest('form');
  if(form&&['classEdu','classDept'].includes(event.target.name)) {
   const edu=form.elements.classEdu.value,deptSelect=form.elements.classDept,classSelect=form.elements.classId;
   if(event.target.name==='classEdu'){deptSelect.innerHTML='<option value="">全部系所</option>'+catalog.departments.filter(d=>!edu||d.edu===edu).map(d=>`<option value="${esc(d.id)}">${esc(d.name)}</option>`).join('');}
   const dept=deptSelect.value;classSelect.innerHTML='<option value="">請選擇班級</option>'+catalog.classes.filter(c=>(!edu||c.edu===edu)&&(!dept||c.dept===dept)).map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('');
  }
  if(form&&event.target.name==='edu'&&form.dataset.form==='search'){const edu=event.target.value;form.elements.dept.innerHTML='<option value="">全部系所</option>'+catalog.departments.filter(d=>!edu||d.edu===edu).map(d=>`<option value="${esc(d.id)}">${esc(d.name)}</option>`).join('');}
 }catch(error){formError(error);}
});
let dragStart;
document.addEventListener('pointerdown',event=>{const cell=event.target.closest('[data-grid-day]');if(cell&&!event.target.closest('a,button,.tt-card')&&event.button===0)dragStart={day:cell.dataset.gridDay,start:cell.dataset.start,end:cell.dataset.end};});
document.addEventListener('pointerup',event=>{if(!dragStart)return;const cell=event.target.closest('[data-grid-day]'),start=dragStart;dragStart=null;if(!cell||cell.dataset.gridDay!==start.day)return;customDialog(null,{weekday:start.day,start:[start.start,cell.dataset.start].sort()[0],end:[start.end,cell.dataset.end].sort().at(-1)});});
window.addEventListener('popstate',()=>{try{render();}catch(error){fatal(error);}});
window.addEventListener('storage',event=>{if([STORAGE_KEY,AUTH].includes(event.key)){try{store=createStore(localStorage,catalog);render();notify('已同步另一個分頁的資料。');}catch(error){fatal(error);}}});
function fatal(error) {document.body.className='is-anonymous';$('#app').innerHTML=`<main class="demo-recovery" id="main-content"><h1>展示資料需要處理</h1><p role="alert">${esc(error.message)}</p><p>不會自動覆寫原始資料。先下載原始資料，再選擇還原備份或重設。</p><div class="demo-actions">${button('重新載入','retry','','btn btn-primary')}${button('下載原始資料','export-raw')}${button('還原 JSON 備份','restore-state')}${button('重設展示資料','reset-state','','btn btn-danger')}</div></main>`;}
async function start() {
 try{const response=await fetch('/static/demo/catalog.json');if(!response.ok)throw Error('課程資料載入失敗。');catalog=await response.json();store=createStore(localStorage,catalog);render();}
 catch(error){fatal(error);}
}
await start();
