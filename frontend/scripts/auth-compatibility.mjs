// Synthetic cross-runtime fixtures; no application configuration or database.
import { hashSync, compareSync } from 'bcryptjs'
import { SignJWT, jwtVerify } from 'jose'
import { readFileSync, writeFileSync } from 'node:fs'

const secret = new TextEncoder().encode('any640-synthetic-contract-secret-at-least-32-characters')
const now = 1791622800
const user = { id: '10000000-0000-4000-8000-000000000001', email: 'owner@example.test' }
const passwords = ['synthetic-password', '  spaced secret  ', 'пароль🔒🔑', 'a'.repeat(72) + 'tail',
  'Ж'.repeat(40), 'null\0byte-secret', 'lone\ud800secret']
if (process.argv[2] === '--generate') {
  const token = await new SignJWT({ email: user.email }).setProtectedHeader({ alg: 'HS256' })
    .setSubject(user.id).setIssuedAt(now).setExpirationTime(now + 604800).sign(secret)
  writeFileSync(process.argv[3], JSON.stringify({ now, user, token,
    passwords: passwords.map(password => ({ password, hash: hashSync(password, '$2b$04$......................') })),
  }, null, 2) + '\n')
} else {
  const input = JSON.parse(readFileSync(0, 'utf8'))
  const payload = (await jwtVerify(input.token, secret, { currentDate: new Date(now * 1000) })).payload
  if (payload.sub !== user.id || payload.email !== user.email || payload.exp - payload.iat !== 604800) throw new Error('Session incompatibility')
  for (const item of input.passwords) if (!compareSync(item.password, item.hash)) throw new Error('Password incompatibility')
  process.stdout.write('Cross-runtime session and bcrypt compatibility passed\n')
}
