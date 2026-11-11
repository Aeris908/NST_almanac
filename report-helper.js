// Консервативный разбор: предлагает числа и точные имена, никогда не сохраняет результат сам.
(function(root){
  function parse(text,players=[]) {
    const names=new Map();for(const player of players)for(const name of [player.nick,...(player.aliases||[])]){const key=name.toLowerCase().trim();if(!names.has(key))names.set(key,new Set());names.get(key).add(player.nick);}
    const roster=value=>value.split(/\s*(?:&|\+|\/)\s*/).map(name=>{const found=names.get(name.trim().toLowerCase());return found?.size===1?[...found][0]:null;});
    const seen=new Set(),games=[],unparsed=[];
    for(const [index,line] of String(text).split(/\r?\n/).entries()) {
      const raw=line.trim();if(!raw)continue;
      const score=raw.match(/(?<!\d)(\d{1,2})\s*[:]\s*(\d{1,2})(?!\d)/);
      if(!score){unparsed.push({line:index+1,text:raw});continue;}
      const pk=raw.match(/(?:пк|pk|пен\.?|буллиты)\s*[:]?\s*(\d{1,2})\s*[-:]\s*(\d{1,2})/i);
      if((pk&&/\bOT\b|овертайм/i.test(raw))||(!pk&&/\(\s*\d{1,2}\s*[-:]\s*\d{1,2}\s*\)/.test(raw))){unparsed.push({line:index+1,text:raw+' — неоднозначный дополнительный результат; проверьте тип исхода вручную.'});continue;}
      if(/(?:пк|pk|пен\.?|буллиты)\s*[:]?\s*$/i.test(raw.slice(0,score.index))||(raw.match(/\d{1,2}\s*:\s*\d{1,2}/g)||[]).length>(pk?2:1)){
        unparsed.push({line:index+1,text:raw+' — несколько результатов или нет счёта основного времени; разберите вручную.'});continue;
      }
      const labels=raw.slice(0,score.index).replace(/^\s*\d+[.)]\s*/, '').split(/\s+(?:vs|против|—|–|-)\s+|\s*[—–]\s*/i);
      const sides=labels.length===2?labels.map(roster):[];
      const known=sides.length===2&&sides.every(side=>side.length===2&&side.every(Boolean))&&new Set(sides.flat()).size===4;
      const duplicate=seen.has(raw);seen.add(raw);
      games.push({raw,line:index+1,s1:Number(score[1]),s2:Number(score[2]),phase:pk?'penalties':(/\bOT\b|овертайм/i.test(raw)?'overtime':'regular'),pk1:pk?Number(pk[1]):null,pk2:pk?Number(pk[2]):null,sides:known?sides:null,
        warnings:[...(!known?['Составы и ориентацию сторон нужно указать вручную.']:[]),...(duplicate?['Повтор строки: возможно, цитата или дубль.']:[]),...(/^>/.test(raw)?['Строка похожа на цитату.']:[])]});
    }
    return {games,unparsed};
  }
  root.NSTReport={parse};if(typeof module!=='undefined')module.exports={parse};
})(typeof window==='undefined'?globalThis:window);
