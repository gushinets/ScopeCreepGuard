async (page) => {
  await page.getByRole('button', { name: 'Scope check', exact: true }).click();
  const input = page.getByRole('textbox', { name: 'New client request', exact: true });
  await input.waitFor();
  let csvRequests = 0, downloads = 0;
  const countRequest = request => { if (request.url().includes('/export.csv?')) csvRequests++; };
  const countDownload = () => { downloads++; };
  page.on('request', countRequest); page.on('download', countDownload);
  await page.route('**/api/v2/drafts/*', async route => {
    if (route.request().method() === 'PUT') await route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ error: 'errors.requestFailed' }) });
    else await route.continue();
  });
  await input.fill('Keep this failed-save edit\nCSV must wait for persistence');
  await page.getByRole('button', { name: 'Export Draft CSV', exact: true }).click();
  await page.getByText('Changes not saved. Your edits are kept on this device.', { exact: true }).waitFor();
  await page.getByText('Could not export the current saved Drafts. Check the save status, finish any newer edits, and try again.', { exact: true }).waitFor();
  if (csvRequests || downloads) throw new Error('Stale export started despite save failure');
  if (!(await input.inputValue()).startsWith('Keep this failed-save edit')) throw new Error('Local edits lost');
  await page.screenshot({ path: 'output/playwright/any556/save-failure-en.png', fullPage: true });
  await page.unroute('**/api/v2/drafts/*');
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await page.getByText('Saved', { exact: true }).waitFor();
  const pending = page.waitForEvent('download');
  const responsePromise = page.waitForResponse(r => r.url().includes('/export.csv?'));
  await page.getByRole('button', { name: 'Export Draft CSV', exact: true }).click();
  const response = await responsePromise;
  if (response.status() !== 200) throw new Error('Retry export failed');
  await (await pending).saveAs('output/playwright/any556/single-after-retry-en.csv');
  page.off('request', countRequest); page.off('download', countDownload);
  return { failedSaveCsvRequests: 0, failedSaveDownloads: 0, editsPreserved: true, retryExportUrl: response.url(), retryDownloadStatus: response.status() };
}
