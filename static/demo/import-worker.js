/* SheetJS is vendored locally. Files are never uploaded to the server. */
importScripts('/static/vendor/xlsx.full.min.js');
self.onmessage = ({data}) => {
  try {
    const bytes=new Uint8Array(data),binary=(bytes[0]===0x50&&bytes[1]===0x4b)||(bytes[0]===0xd0&&bytes[1]===0xcf);
    let input=data;
    if(!binary) {
      try{input=new TextDecoder('utf-8',{fatal:true}).decode(bytes);}
      catch{input=new TextDecoder('big5').decode(bytes);}
    }
    const workbook=XLSX.read(input,{type:binary?'array':'string',sheetRows:501,cellHTML:false,cellFormula:false,cellStyles:false});
    if(workbook.SheetNames.length>5) throw Error('最多支援 5 張工作表。');
    const tables=workbook.SheetNames.map(name=>{
      const sheet=workbook.Sheets[name],ref=sheet['!fullref']||sheet['!ref'];
      if(ref) {const range=XLSX.utils.decode_range(ref);if(range.e.r>=500||range.e.c>=30) throw Error('每張表最多 500 列、30 欄。');}
      return {name,rows:XLSX.utils.sheet_to_json(sheet,{header:1,defval:'',raw:false,blankrows:true})};
    });
    self.postMessage({tables});
  } catch(error) {self.postMessage({error:error.message||'檔案讀取失敗。'});}
};
