import { OAuth2Server } from 'oauth2-mock-server'

const server = new OAuth2Server()
await server.issuer.keys.generate('RS256')

server.service.on('beforeTokenSigning', (token, req) => {
  const email = req.query?.login_hint ?? req.body?.login_hint ?? 'e2e@example.com'
  token.payload.email = email
  token.payload.sub = email
})

await server.start(4444, 'localhost')

console.log('Mock OAuth server running at http://localhost:4444')

async function shutdown() {
  await server.stop()
  process.exit(0)
}

process.on('SIGTERM', shutdown)
process.on('SIGINT', shutdown)
