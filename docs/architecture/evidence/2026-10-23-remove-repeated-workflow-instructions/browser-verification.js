async(page) => {
 const results=[];
 for(const locale of ['ru','en']) {
  const context=await page.context().browser().newContext({viewport:{width:1440,height:1000}}),tab=await context.newPage(),base='http://localhost:3000';
  const check=(value,message)=>{if(!value)throw Error(message)};
  await context.request.post(base+'/api/locale',{data:{locale}});
  const registration=await context.request.post(base+'/api/auth/register',{data:{email:`copy-${locale}-${Date.now()}@example.test`,password:'Copy-check-test-42'}});check(registration.ok(),'registration');
  await tab.goto(base+'/');await tab.getByRole('button',{name:locale==='ru'?'Создать первый проект':'Create your first project',exact:true}).click();
  await tab.locator('#project-name').fill(locale==='ru'?'Проверка интерфейса':'Interface check');await tab.locator('#project-industry').selectOption('Development');await tab.locator('#project-scope').fill(locale==='ru'?'Разработка сайта из пяти страниц':'Build a five-page website');await tab.locator('#project-startDate').fill('2026-10-23');await tab.locator('#project-currency').selectOption('USD');await tab.locator('#project-hourlyRate').fill('30');
  await tab.getByRole('button',{name:locale==='ru'?'Сохранить проект':'Save project',exact:true}).click();await tab.locator('#request-input').waitFor();
  check(await tab.locator('.assessment-workspace').innerText()==='','idle assessment still teaches');
  check(await tab.locator('.coachmark').count()===1,'guide duplicated or missing');
  await tab.getByRole('button',{name:locale==='ru'?'Пропустить знакомство':'Skip onboarding',exact:true}).first().click();await tab.locator('.coachmark').waitFor({state:'hidden'});
  await tab.screenshot({path:`output/local/no-repeat-${locale}-desktop.png`});
  await tab.setViewportSize({width:390,height:844});await tab.screenshot({path:`output/local/no-repeat-${locale}-mobile.png`});check(await tab.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'overflow');
  await tab.locator('#request-input').fill(locale==='ru'?'Добавьте шестую страницу':'Add a sixth page');check(await tab.getByRole('button',{name:locale==='ru'?'Проверить запрос':'Check scope',exact:true}).isEnabled(),'primary action unavailable');
  await tab.reload();await tab.locator('#request-input').waitFor();check(await tab.locator('.assessment-workspace').innerText()==='','reload restores idle instructions');
  await context.close();results.push({locale,oneContextualGuide:true,noIdleInstructions:true,skip:true,mobile:true,primaryAction:true,reload:true});
 }
 return results;
}
