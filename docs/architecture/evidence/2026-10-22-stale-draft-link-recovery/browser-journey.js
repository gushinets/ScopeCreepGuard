async(page)=>{
 const base='http://localhost:3000',browser=page.context().browser(),check=(value,message)=>{if(!value)throw Error(message)};
 const ownerContext=await browser.newContext();const password='Stale-link-test-42';
 const register=await ownerContext.request.post(base+'/api/auth/register',{data:{email:`stale-owner-${Date.now()}@example.test`,password}});check(register.ok(),'Owner registration failed');
 const response=await ownerContext.request.post(base+'/api/v2/projects',{data:{name:'Owned link fixture',industry:'Development',scope:'Maintain a daily dashboard and CSV export for two suppliers.',startDate:'2026-10-22',pricingModel:'hourly',currency:'USD',hourlyRate:'30',fixedPrice:'',operationId:crypto.randomUUID()}});check(response.ok(),'Project creation failed');const project=(await response.json()).project;
 const oldDraft=(await(await ownerContext.request.get(base+`/api/v2/projects/${project.id}/draft`)).json()).draft;
 const results=[];
 for(const locale of ['ru','en']){
  const context=await browser.newContext({viewport:{width:locale==='ru'?900:1440,height:900}}),tab=await context.newPage();await context.request.post(base+'/api/locale',{data:{locale}});
  const target=`/?keep=value&draft=${oldDraft.id}#reply`;
  await tab.goto(base+'/register?returnTo='+encodeURIComponent(target));await tab.locator('#auth-email').fill(`stale-new-${locale}-${Date.now()}@example.test`);await tab.locator('#auth-password').fill(password);await tab.locator('form button[type=submit]').click();
  const start=tab.getByRole('button',{name:locale==='ru'?'Создать первый проект':'Create your first project',exact:true});await start.waitFor();
  check(new URL(tab.url()).searchParams.get('draft')===null,'Foreign draft remains in URL');check(new URL(tab.url()).searchParams.get('keep')==='value','Unrelated query lost');
  const foreign=await context.request.get(base+`/api/v2/drafts/${oldDraft.id}`);check(foreign.status()===404,'Cross-account access allowed');
  check(!(await(await context.request.get(base+'/api/v2/projects')).json()).projects.length,'Foreign project inserted');
  await tab.screenshot({path:`output/local/stale-link-recovered-${locale}.png`});await tab.reload();await start.waitFor();
  const ownResponse=await context.request.post(base+'/api/v2/projects',{data:{name:'My separate project',industry:'Development',scope:'Maintain a daily dashboard and CSV export for two suppliers.',startDate:'2026-10-22',pricingModel:'hourly',currency:'USD',hourlyRate:'30',fixedPrice:'',operationId:crypto.randomUUID()}});check(ownResponse.ok(),'Own project creation failed');const own=(await ownResponse.json()).project;
  const ownDraft=(await(await context.request.get(base+`/api/v2/projects/${own.id}/draft`)).json()).draft;
  await tab.goto(base+target);await tab.locator('#request-input').waitFor();check(new URL(tab.url()).searchParams.get('draft')===ownDraft.id,'Own draft was not selected');
  results.push({locale,newAccountRecovered:true,ownDraftFallback:true,reloadWorks:true,ownershipPreserved:true});await context.close();
 }
 await ownerContext.close();return results;
}
