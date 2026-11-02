import {PERIODS,validateSlot} from './model.mjs';
const str=v=>v==null?'':String(v).trim();
const norm=v=>str(v).replace(/[\s_:：*＊()（）]/g,'').toLowerCase();
const aliases={title:['課程名稱','科目名稱','課名','科目','課程','title','course'],weekday:['星期','星期幾','週幾','上課星期','day','weekday'],start:['開始時間','起始時間','上課開始','start'],end:['結束時間','下課時間','上課結束','end'],period:['節次','上課節次','節數','period'],schedule:['上課時間','授課時間','星期節次','時間節次'],location:['教室','上課教室','地點','上課地點','room','location'],teacher:['教師','授課教師','任課教師','老師','teacher'],note:['備註','說明','note']};
const days=Object.fromEntries([...('一二三四五六日')].map((v,i)=>[v,i+1]));days.天=7;
function weekdays(raw) {
  raw=str(raw);if(/[單雙]週/.test(raw)) throw Error('尚不支援單雙週。');
  if(/^[1-7](\.0)?$/.test(raw)) return [Number(raw)];
  const found=[...new Set([...raw.replace(/星期|禮拜|週|周/g,'')].filter(c=>days[c]).map(c=>days[c]))];
  if(!found.length) throw Error('無法辨識星期。');return found;
}
function clock(v) {
  if(typeof v==='string' && /^0?\.\d+$/.test(v.trim())) v=Number(v);
  if(typeof v==='number'&&v>=0&&v<1) {const m=Math.round(v*1440);return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;}
  const m=str(v).replaceAll('：',':').match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
  if(!m||Number(m[1])>23||Number(m[2])>59) throw Error('無法辨識時間。');return `${m[1].padStart(2,'0')}:${m[2]}`;
}
function times(label) {
  const raw=str(label).replaceAll('：',':'), explicit=raw.match(/\d{1,2}:\d{2}/g);
  if(explicit?.length>=2) return [clock(explicit[0]),clock(explicit[1])];
  const named=PERIODS.find(p=>raw.includes(p[0]));if(named) return named.slice(1);
  const numbers=(raw.match(/\d+/g)||[]).map(Number);
  if(!numbers.length||Math.min(...numbers)<1||Math.max(...numbers)>13) throw Error('節次請使用 1–13 或明確起訖時間。');
  return [PERIODS[Math.min(...numbers)-1][1],PERIODS[Math.max(...numbers)-1][2]];
}
export function parseTables(tables) {
  const parsed=[], errors=[];
  for(const {name,rows} of tables) {
    if(rows.length>500||rows.some(r=>r.length>30||r.some(v=>str(v).length>3000))) throw Error('每張表最多 500 列、30 欄；儲存格內容最多 3000 字。');
    let header=-1, columns={};
    for(let i=0;i<Math.min(25,rows.length);i++) {
      const c={};rows[i].forEach((v,j)=>Object.entries(aliases).forEach(([key,names])=>{if(names.map(norm).includes(norm(v))) c[key]=j;}));
      if(c.title!=null&&(c.weekday!=null||c.schedule!=null)&&Object.keys(c).length>Object.keys(columns).length) {header=i;columns=c;}
    }
    if(header>=0) {
      rows.slice(header+1).forEach((row,index)=>{
        const get=key=>row[columns[key]]??'',title=str(get('title'));if(!title) return;
        try {
          const teacher=str(get('teacher')),location=str(get('location')),note=[teacher,str(get('note'))].filter(Boolean).join(' · ');
          let slots=[];
          if(columns.schedule!=null&&!str(get('weekday'))) {
            const segments=[...str(get('schedule')).matchAll(/(?:星期|週|周|\()([一二三四五六日天])\)?\s*([^;；\n]+)/g)];
            if(!segments.length) throw Error('無法辨識上課時間。');
            slots=segments.map(m=>({weekday:weekdays(m[1])[0],range:times(m[2])}));
          } else {
            const range=str(get('start'))&&str(get('end'))?[clock(get('start')),clock(get('end'))]:times(get('period'));
            slots=weekdays(get('weekday')).map(weekday=>({weekday,range}));
          }
          for(const {weekday,range} of slots) parsed.push(validateSlot({title,weekday,start:range[0],end:range[1],location,note}));
        } catch(e) {errors.push(`${name} 第 ${header+index+2} 列：${e.message}`);}
      });continue;
    }
    let found=false;
    for(let i=0;i<Math.min(25,rows.length);i++) {
      const dayColumns={};
      rows[i].forEach((v,j)=>{const t=str(v);if(/^(星期|週|周)[一二三四五六日天]$/.test(t)||(j>0&&['節次','時間','時段'].includes(norm(rows[i][0]))&&days[t])) dayColumns[j]=weekdays(t)[0];});
      if(Object.keys(dayColumns).length<3) continue;
      found=true;
      rows.slice(i+1).forEach((row,index)=>{
        if(!Object.keys(dayColumns).some(j=>str(row[j]))) return;
        try {
          const first=Math.min(...Object.keys(dayColumns).map(Number)),range=times(row.slice(0,first).map(str).join(' '));
          for(const [column,weekday] of Object.entries(dayColumns)) {
            const content=str(row[column]);if(!content||['-','—','無','空堂'].includes(content)) continue;
            const lines=content.split(/\r?\n/).map(str).filter(Boolean);
            parsed.push(validateSlot({title:lines[0],weekday,start:range[0],end:range[1],location:lines[2]||'',note:[lines[1],...lines.slice(3)].filter(Boolean).join('\n')}));
          }
        } catch(e) {errors.push(`${name} 第 ${i+index+2} 列：${e.message}`);}
      });break;
    }
    if(!found) errors.push(`${name}：找不到課程清單或週課表欄位。`);
  }
  const seen=new Set(),rows=parsed.filter(row=>{const key=JSON.stringify([row.title,row.weekday,row.start,row.end,row.location]);if(seen.has(key))return false;seen.add(key);return true;});
  if(rows.length>200) throw Error('單次最多匯入 200 個上課時段。');
  if(!rows.length) throw Error(errors.slice(0,5).join('\n')||'檔案沒有可辨識課程。');
  return {rows,errors:errors.slice(0,30)};
}
export async function readSpreadsheet(file,XLSX) {
  if(!file||!file.size||file.size>2*1024*1024||! /\.(xlsx|xls|csv)$/i.test(file.name)) throw Error('請選擇 2 MB 以內的 .xlsx、.xls 或 .csv 檔案。');
  if(!XLSX) throw Error('Excel 元件未載入，請重新整理或重新安裝環境。');
  const bytes=await file.arrayBuffer();
  // Workbook parsing runs in a worker so malformed/compressed input cannot lock the UI.
  return bytes;
}
