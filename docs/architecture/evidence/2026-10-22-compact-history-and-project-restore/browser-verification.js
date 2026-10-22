async(page) => {
 const results=[];
 for (const [locale,email] of [['en','auto-pdf-en-1792674371005@example.test'],['ru','auto-pdf-ru-1792674406418@example.test']]) {
  const context=await page.context().browser().newContext({viewport:{width:1440,height:1000}}),tab=await context.newPage(),base='http://localhost:3100';
  const check=(v,m)=>{if(!v)throw Error(m)};
  await context.request.post(base+'/api/locale',{data:{locale}});
  check((await context.request.post(base+'/api/auth/login',{data:{email,password:'Auto-pdf-test-42'}})).ok(),'login');
  let archived=(await(await context.request.get(base+'/api/v2/projects?archived=true')).json()).projects[0];
  if (!archived) {
   const active=(await(await context.request.get(base+'/api/v2/projects')).json()).projects[0];
   check(!!active,'synthetic project missing');
   await context.request.delete(base+`/api/v2/projects/${active.id}`);
   archived=(await(await context.request.get(base+'/api/v2/projects?archived=true')).json()).projects[0];
  }
  const id=archived.id,draftBefore=await(await context.request.get(base+`/api/v2/projects/${id}/draft`)).json();
  await tab.goto(base+'/history');const row=tab.getByRole('button',{name:new RegExp(archived.name)});await row.waitFor();check(await row.getAttribute('aria-expanded')==='false','must start collapsed');check(await tab.locator('select#history-project').count()===0,'old selector remains');
  await tab.screenshot({path:`output/local/compact-history-${locale}-desktop.png`});await tab.setViewportSize({width:390,height:844});await tab.screenshot({path:`output/local/compact-history-${locale}-mobile.png`});check(await tab.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile overflow');
  await row.click();await tab.getByRole('article',{name:locale==='en'?'Latest saved version':'Последняя сохранённая версия'}).waitFor();check(!(await(await context.request.get(base+'/api/v2/projects')).json()).projects.length,'viewing restored project');
  await tab.setViewportSize({width:1440,height:1000});await tab.screenshot({path:`output/local/compact-details-${locale}.png`,fullPage:true});
  await Promise.all([tab.waitForResponse(response=>response.url().endsWith(`/projects/${id}/restore`) && response.request().method()==='POST'), tab.getByRole('button',{name:locale==='en'?'Restore':'Восстановить',exact:true}).click()]);await tab.getByRole('button',{name:locale==='en'?'Restoring…':'Восстановление…',exact:true}).waitFor({state:'hidden'});
  check((await(await context.request.get(base+'/api/v2/projects')).json()).projects[0].id===id,'not active after restore');
  const draftAfter=await(await context.request.get(base+`/api/v2/projects/${id}/draft`)).json();check(JSON.stringify(draftBefore)===JSON.stringify(draftAfter),'draft changed');
  const projectAfter=(await(await context.request.get(base+`/api/v2/projects/${id}`)).json()).project;check(JSON.stringify(projectAfter.history)===JSON.stringify(archived.history),'history changed');
  check((await context.request.post(base+`/api/v2/projects/${id}/restore`,{data:{}})).ok(),'repeat restore');await tab.reload();await tab.getByRole('button',{name:new RegExp(archived.name)}).waitFor();check(!await tab.getByRole('button',{name:locale==='en'?'Restore':'Восстановить',exact:true}).count(),'reload archive state');
  await context.request.delete(base+`/api/v2/projects/${id}`);await context.close();results.push({locale,compact:true,mobile:true,readOnlyExpansion:true,restore:true,preservedDraftAndHistory:true,reload:true});
 }
 return results;
}
