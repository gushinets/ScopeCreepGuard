import { readFile, writeFile } from 'node:fs/promises'
import openapiTS, { astToString } from 'openapi-typescript'

const output = new URL('../lib/api/generated.ts', import.meta.url)
const source = new URL('../../contracts/openapi.json', import.meta.url)
const generated = astToString(await openapiTS(source))
if (process.argv.includes('--check')) {
  if (await readFile(output, 'utf8') !== generated) throw new Error('Stale API types; run pnpm api:types')
} else {
  await writeFile(output, generated)
}
