import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createStore,initialState,STORAGE_KEY,validateState,validateSlot,buildGrid,getItems,PERIODS} from '../static/demo/model.mjs';
import {parseTables} from '../static/demo/import.mjs';
import {PAGES,resolveRoute} from '../static/demo/routes.mjs';
const catalog=JSON.parse(readFileSync(new URL('../static/demo/catalog.json',import.meta.url)));
class MemoryStorage {
 data=new Map();blocked=false;
 getItem(k){return this.data.get(k)??null;}
 setItem(k,v){if(this.blocked)throw Error('QuotaExceededError');this.data.set(k,v);}
}
const context=()=>{const storage=new MemoryStorage();return {storage,store:createStore(storage,catalog)};};
const slot=(extra={})=>({title:'作業系統',weekday:1,start:'13:30',end:'14:20',location:'電703',note:'展示教師',...extra});
const schoolGrid=[['節次','一','二','三','四','五','六','日'],['第五節\n13:30\n14:20','作業系統\n展示教師\n電703','','程式設計\n展示教師\n電708','','','',''],['第六節\n14:25\n15:15','作業系統\n展示教師\n電703','','程式設計\n展示教師\n電708','','','','']];

test('catalog preserves all 258 classes / 2031 offerings with resolvable references',()=>{
 assert.equal(catalog.classes.length,258);assert.equal(catalog.offerings.length,2031);
 for(const o of catalog.offerings){assert.ok(o.slots.length);for(const id of o.classes)assert.ok(catalog.classes.some(c=>c.id===id));for(const s of o.slots)assert.ok(s.weekday>=1&&s.weekday<=7);}
});
test('fresh storage is initialized once and survives a new store instance',()=>{
 const {store,storage}=context();store.saveCustom(slot());assert.equal(createStore(storage,catalog).snapshot().customs.length,1);assert.ok(storage.getItem(STORAGE_KEY));
});
test('course add/remove, duplicate prevention and conflict rejection',()=>{
 const {store}=context(),first=catalog.offerings.find(o=>o.slots.length===2);
 assert.equal(store.addOffering(first.id),'added');assert.equal(store.addOffering(first.id),'duplicate');
 const second=catalog.offerings.find(o=>o.id!==first.id&&o.slots.some(s=>first.slots.some(t=>s.weekday===t.weekday&&s.start<t.end&&t.start<s.end)));
 assert.throws(()=>store.addOffering(second.id),/衝堂/);assert.equal(store.snapshot().selected.length,1);
 store.removeOffering(first.id);assert.equal(store.snapshot().selected.length,0);
});
test('class import can be undone without deleting manual selections or custom events',()=>{
 const {store}=context();store.saveCustom(slot({start:'23:00',end:'23:30'}));
 const first=catalog.offerings[0];store.addOffering(first.id);const result=store.importClass(first.classes[0]);assert.ok(result.added>0);
 const batch=store.snapshot().batches[0];store.undoBatch(batch.id);assert.equal(store.snapshot().selected.length,1);assert.equal(store.snapshot().customs.length,1);
});
test('PoolExport imports teacher/room, deduplicates and shares fifth/sixth period rows',()=>{
 const {store}=context();const {rows,errors}=parseTables([{name:'PoolExport',rows:schoolGrid}]);assert.equal(rows.length,4);assert.equal(errors.length,0);assert.equal(rows[0].note,'展示教師');assert.equal(rows[0].location,'電703');
 const result=store.confirmImport(rows,'PoolExport.xls');assert.equal(result.added,4);assert.equal(store.confirmImport(rows,'again.xls').duplicates,4);
 const grid=buildGrid(getItems(store.snapshot(),catalog));assert.equal(grid.length,9);assert.deepEqual(grid[4].period,PERIODS[4]);assert.equal(grid[4].days[0][0].title,'作業系統');assert.equal(grid[5].days[2][0].title,'程式設計');
});
test('list format supports aliases, multiple weekdays, schedule strings, fractions and period ranges',()=>{
 const list=[['課程名稱','星期','開始時間','結束時間','教室','教師'],['程式','週一、週三','8:10','09:00','301','王老師']];
 assert.equal(parseTables([{name:'list',rows:list}]).rows.length,2);
 assert.equal(parseTables([{name:'list',rows:[['課名','星期','節次'],['程式',2,'3-4']]}]).rows[0].end,'12:00');
 assert.equal(parseTables([{name:'list',rows:[['課名','星期','開始時間','結束時間'],['程式',2,0.5,0.5625]]}]).rows[0].start,'12:00');
 assert.equal(parseTables([{name:'list',rows:[['課名','上課時間'],['程式','週一 08:10-09:00;週三 10:10-11:00']]}]).rows.length,2);
});
test('malformed/oversized spreadsheets report errors and make no mutations',()=>{
 const {store}=context(),before=store.snapshot();assert.throws(()=>parseTables([{name:'bad',rows:[['wrong']]}]));
 assert.throws(()=>parseTables([{name:'bad',rows:Array.from({length:501},()=>[])}]));
 assert.throws(()=>parseTables([{name:'bad',rows:[['課名','星期','節次'],['程式','單週一','2']]}]));assert.deepEqual(store.snapshot(),before);
});
test('preview reports collisions; skip conflicts preserves existing personal events',()=>{
 const {store}=context();store.saveCustom(slot({title:'自習'}));assert.equal(store.previewRows([slot()])[0].conflicts[0],'自習');
 assert.equal(store.confirmImport([slot()],'test',{skipConflicts:true}).conflicts,1);assert.equal(store.snapshot().batches.length,0);
 assert.equal(store.confirmImport([slot()],'test',{skipConflicts:false}).added,1);assert.equal(store.snapshot().customs.length,2);
});
test('custom edit/delete retains source and batch for undo and reflects changes after reload',()=>{
 const {store,storage}=context();store.confirmImport([slot()],'test');const old=store.snapshot().customs[0];
 store.saveCustom({...old,title:'已編輯',start:'14:25',end:'15:15'});const saved=createStore(storage,catalog).snapshot().customs[0];assert.equal(saved.source,'excel');assert.equal(saved.batch,old.batch);assert.equal(saved.title,'已編輯');
 store.undoBatch(old.batch);assert.equal(store.snapshot().customs.length,0);
 const id=store.saveCustom(slot());store.deleteCustom(id);assert.equal(store.snapshot().customs.length,0);
});
test('clear imported vs clear all courses preserves manual and personal data appropriately',()=>{
 const {store}=context();store.addOffering(catalog.offerings[0].id);store.saveCustom(slot({title:'自習',start:'23:00',end:'23:30'}));store.confirmImport([slot()],'test');
 store.clearImported();assert.equal(store.snapshot().selected.length,1);assert.equal(store.snapshot().customs.length,1);
 store.clearCourses();assert.equal(store.snapshot().selected.length,0);assert.equal(store.snapshot().customs.length,1);
});
test('grid separates identical labels at different times and merges identical intervals',()=>{
 const list=[slot({period:'中午',start:'12:00',end:'12:30'}),slot({period:'中午',start:'12:30',end:'13:00'}),slot({period:'13:30–14:20'}),slot({weekday:3})];
 const grid=buildGrid(list);assert.equal(grid.length,11);assert.equal(grid.filter(r=>r.period[1]==='13:30').length,1);assert.equal(grid.filter(r=>r.period[0]==='中午').length,2);
 const compact=buildGrid(list,{full:false});assert.equal(compact.length,3);assert.equal(compact.flatMap(r=>r.days.flat()).length,4);
});
test('date event and group event CRUD persists, including events crossing midnight',()=>{
 const {store,storage}=context();const event={title:'展示活動',start:'2026-11-02T23:00',end:'2026-11-03T01:00'};
 const id=store.saveEvent(event);store.saveEvent({...event,id,title:'新標題'});assert.equal(createStore(storage,catalog).snapshot().events[0].title,'新標題');store.deleteEvent(id);assert.equal(store.snapshot().events.length,0);
 const groupId=store.snapshot().groups[0].id,gid=store.saveEvent(event,groupId);assert.equal(store.snapshot().groups[0].events.length,1);store.deleteEvent(gid,groupId);assert.equal(store.snapshot().groups[0].events.length,0);
 assert.throws(()=>store.saveEvent({...event,end:event.start}));
});
test('profile, privacy, social, group tasks/memos and school changes survive a round trip',()=>{
 const {store,storage}=context();store.transact(s=>{s.profile.displayName='展示修改';s.privacy.friends=false;s.friends[1].status='accepted';s.groups[0].tasks.push({id:'t1',title:'練習',done:true});s.groups[0].memos.push({id:'m1',title:'記事',body:'文字'});s.capacities[1]=88;s.students.push({id:'demo001',name:'展示學生',email:'demo@example.com'});s.roles.push({id:'role1',name:'教務展示',role:'school'});});
 const saved=createStore(storage,catalog).snapshot();assert.equal(saved.profile.displayName,'展示修改');assert.equal(saved.capacities[1],88);assert.equal(saved.groups[0].tasks[0].done,true);assert.equal(saved.friends[1].status,'accepted');assert.equal(saved.students.length,1);
});
test('invalid form input and malformed backup do not damage existing data',()=>{
 const {store}=context();store.saveCustom(slot());const before=store.snapshot();
 for(const invalid of [{title:''},{weekday:9},{start:'24:00'},{end:'12:00'},{location:'x'.repeat(61)}]) assert.throws(()=>store.saveCustom(slot(invalid)));
 assert.throws(()=>store.restore('{bad json'));assert.throws(()=>store.restore(JSON.stringify({version:99})));assert.deepEqual(store.snapshot(),before);
});
test('quota failure is atomic and corrupted storage is preserved for recovery',()=>{
 const {store,storage}=context(),before=store.snapshot();storage.blocked=true;assert.throws(()=>store.saveCustom(slot()),/尚未儲存/);assert.deepEqual(store.snapshot(),before);
 storage.blocked=false;storage.setItem(STORAGE_KEY,'broken');assert.throws(()=>createStore(storage,catalog),/原始資料仍保留/);assert.equal(storage.getItem(STORAGE_KEY),'broken');
});
test('export/restore and reset leave a usable demo state',()=>{
 const {store}=context();store.saveCustom(slot());const backup=JSON.stringify(store.snapshot());store.reset();assert.equal(store.snapshot().customs.length,0);store.restore(backup);assert.equal(store.snapshot().customs.length,1);assert.doesNotThrow(()=>validateState(store.snapshot(),catalog));
});
test('all page routes and every catalog detail/roster deep link resolve',()=>{
 assert.ok(Object.keys(PAGES).length>=25);for(const [path,page] of Object.entries(PAGES)){assert.equal(resolveRoute(path).page,page);assert.equal(resolveRoute(path.slice(0,-1)||'/').page,page);}
 for(const o of catalog.offerings){for(const prefix of ['/courses/offering/','/school/offerings/']){assert.equal(resolveRoute(prefix+o.id+'/').page,'course');assert.equal(resolveRoute(prefix+o.id+'/roster/').roster,true);}}
 for(const path of ['/accounts/groups/example/','/accounts/profile/example/','/selection/calendar/events/example/','/selection/timetable/student/example/'])assert.notEqual(resolveRoute(path).page,'missing');
 assert.equal(resolveRoute('/unknown-page/').page,'missing');
});
