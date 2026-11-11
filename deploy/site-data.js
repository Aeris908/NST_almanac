// Протоколы загружаются только при открытии раздела. Неудачный запрос можно повторить.
window.NSTData = (() => {
  const requests=new Map();
  let generation=0;
  async function load(item) {
    if(!item?.lazy_url)return item;
    const url=item.lazy_url;
    if(!requests.has(url))requests.set(url,fetch(url).then(response=>{
      if(!response.ok)throw Error('Протоколы не загрузились. Повторите запрос или обновите страницу.');
      return response.json();
    }).catch(()=>{requests.delete(url);throw Error('Протоколы не загрузились. Повторите запрос или обновите страницу.');}));
    const value=await requests.get(url);Object.assign(item,value);delete item.lazy_url;return item;
  }
  function ready(item,host,render) {
    if(!item?.lazy_url){if(host)delete host.dataset.loadKey;return true;}
    const key=String(++generation);host.dataset.loadKey=key;host.replaceChildren();
    const status=document.createElement('p');status.className='data-status';status.setAttribute('role','status');status.textContent='Загружаем протоколы…';host.append(status);
    load(item).then(()=>{if(host.isConnected&&host.dataset.loadKey===key)render();}).catch(error=>{
      if(host.dataset.loadKey!==key)return;
      status.textContent=error.message;const retry=document.createElement('button');retry.className='filter-btn';retry.textContent='Повторить загрузку';retry.onclick=render;host.append(retry);
    });return false;
  }
  return {load,ready};
})();
