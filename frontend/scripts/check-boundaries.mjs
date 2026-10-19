import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const root = path.resolve(import.meta.dirname, '../src')
const files = []
function walk(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name)
    if (entry.isDirectory()) walk(file)
    else if (/\.tsx?$/.test(file) && !/\.test\.|[\\/]test[\\/]/.test(file)) files.push(file)
  }
}
walk(root)
const errors = [], graph = new Map()
for (const file of files) {
  const relative = path.relative(root, file).replaceAll('\\', '/')
  const source = ts.createSourceFile(file, readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true)
  const edges = []
  for (const node of source.statements) {
    if (!(ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) || !node.moduleSpecifier || !ts.isStringLiteral(node.moduleSpecifier)) continue
    const specifier = node.moduleSpecifier.text
    let target = specifier.startsWith('@/') ? path.join(root, specifier.slice(2)) : specifier.startsWith('.') ? path.resolve(path.dirname(file), specifier) : null
    if (!target) continue
    const targetRelative = path.relative(root, target).replaceAll('\\', '/')
    if (relative.startsWith('shared/') && !targetRelative.startsWith('shared/')) errors.push(`${relative}: shared imports ${targetRelative}`)
    const own = /^features\/([^/]+)\//.exec(relative)?.[1]
    const other = /^features\/([^/]+)\/(.+)$/.exec(targetRelative)
    if (own && other && other[1] !== own && !['contracts', 'index'].includes(other[2])) errors.push(`${relative}: private feature import ${targetRelative}`)
    const typeOnly = node.isTypeOnly || node.importClause?.isTypeOnly || (node.importClause?.namedBindings && ts.isNamedImports(node.importClause.namedBindings) && !node.importClause.name && node.importClause.namedBindings.elements.every(item => item.isTypeOnly))
    if (typeOnly) continue
    target = [target + '.ts', target + '.tsx', path.join(target, 'index.ts')].find(candidate => files.includes(candidate))
    if (target) edges.push(target)
  }
  graph.set(file, edges)
}
const visited = new Set(), active = []
function visit(file) {
  if (active.includes(file)) { errors.push('Runtime cycle: ' + [...active.slice(active.indexOf(file)), file].map(item => path.relative(root, item)).join(' -> ')); return }
  if (visited.has(file)) return
  active.push(file)
  for (const target of graph.get(file) ?? []) visit(target)
  active.pop(); visited.add(file)
}
for (const file of files) visit(file)
if (errors.length) throw new Error(errors.join('\n'))
console.log(`Frontend dependency boundaries passed (${files.length} modules).`)
