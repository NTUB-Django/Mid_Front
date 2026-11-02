import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {parseTables} from '../static/demo/import.mjs';
const vendor=readFileSync(new URL('../static/vendor/xlsx.full.min.js',import.meta.url),'utf8');
const worker=readFileSync(new URL('../static/demo/import-worker.js',import.meta.url),'utf8');
function engine() {
 const sandbox={TextDecoder};vm.createContext(sandbox);sandbox.self=sandbox;
 sandbox.importScripts=()=>vm.runInContext(vendor,sandbox);
 vm.runInContext(worker,sandbox);return sandbox;
}
function read(sandbox,bytes){let result;sandbox.postMessage=data=>{result=data;};sandbox.byteValues=Array.from(new Uint8Array(bytes));vm.runInContext('self.onmessage({data:new Uint8Array(byteValues).buffer})',sandbox);if(result.error)throw Error(result.error);return result.tables;}
const rows=[['節次','一','二','三','四','五','六','日'],['第五節\n13:30\n14:20','作業系統\n展示教師\n電703','','','','','',''],['第六節\n14:25\n15:15','作業系統\n展示教師\n電703','','','','','','']];
test('vendored 0.20.3 worker reads actual xlsx and legacy BIFF xls files',()=>{
 const sandbox=engine();assert.equal(sandbox.XLSX.version,'0.20.3');
 for(const bookType of ['xlsx','biff8']) {
  const workbook=sandbox.XLSX.utils.book_new();sandbox.XLSX.utils.book_append_sheet(workbook,sandbox.XLSX.utils.aoa_to_sheet(rows),'課表');
  const bytes=sandbox.XLSX.write(workbook,{type:'array',bookType});
  const parsed=parseTables(read(sandbox,bytes));assert.equal(parsed.rows.length,2);assert.equal(parsed.rows[0].location,'電703');assert.equal(parsed.rows[1].start,'14:25');
 }
});
test('school HTML xls with br separators and UTF-8 CSV both round-trip',()=>{
 const sandbox=engine();
 const html='<html><meta charset="utf-8"><table>'+rows.map(r=>'<tr>'+r.map(c=>'<td>'+c.replaceAll('\n','<br>')+'</td>').join('')+'</tr>').join('')+'</table></html>';
 const bytes=new TextEncoder().encode(html).buffer;
 const parsed=parseTables(read(sandbox,bytes));assert.equal(parsed.rows.length,2);assert.equal(parsed.rows[0].note,'展示教師');
 const csv='\ufeff課程名稱,星期,開始時間,結束時間,教室\n程式設計,週一,08:10,09:00,301\n';
 assert.equal(parseTables(read(sandbox,new TextEncoder().encode(csv).buffer)).rows[0].title,'程式設計');
});
test('worker rejects workbook dimensions above classroom import limit',()=>{
 const sandbox=engine(),workbook=sandbox.XLSX.utils.book_new(),sheet=sandbox.XLSX.utils.aoa_to_sheet([['課名']]);sheet['!ref']='A1:A501';
 sandbox.XLSX.utils.book_append_sheet(workbook,sheet,'課表');const bytes=sandbox.XLSX.write(workbook,{type:'array',bookType:'xlsx'});assert.throws(()=>read(sandbox,bytes),/500/);
});

test('legacy Big5 HTML exports preserve Chinese weekday headers',()=>{
 const sandbox=engine();
 // Big5 bytes for 節次、一、二、三、作業系統 generated from the school export encoding.
 const prefix=Buffer.from('<table><tr><td>'),suffix=Buffer.from('</table>');
 const cells=['b860a6b8','a440','a447','a454'];
 const header=Buffer.concat([prefix,...cells.flatMap((hex,i)=>[Buffer.from(hex,'hex'),Buffer.from(i===cells.length-1?'</td></tr>':'</td><td>')])]);
 const body=Buffer.concat([Buffer.from('<tr><td>13:30-14:20</td><td>'),Buffer.from('a740b77ea874b2ce','hex'),Buffer.from('</td><td></td><td></td></tr>')]);
 const buffer=Buffer.concat([header,body,suffix]);
 const parsed=parseTables(read(sandbox,buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength)));
 assert.equal(parsed.rows[0].title,'作業系統');assert.equal(parsed.rows[0].weekday,1);
});
