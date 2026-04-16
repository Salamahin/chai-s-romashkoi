import { OAuth2Server } from 'oauth2-mock-server'
import { spawn, type ChildProcess } from 'child_process'
import path from 'path'

export const oauthServer = new OAuth2Server()
export let backendProcess: ChildProcess | null = null

export default async function globalSetup(): Promise<void> {
  await oauthServer.issuer.keys.generate('RS256')

  oauthServer.service.on('beforeTokenSigning', (token: any, req: any) => {
    const email = req.query?.login_hint ?? req.body?.login_hint ?? 'e2e@example.com'
    token.payload.email = email
    token.payload.sub = email
  })

  await oauthServer.start(4444, 'localhost')

  const env = {
    ...process.env,
    VITE_OAUTH_ISSUER_URL: 'http://localhost:4444',
    VITE_GOOGLE_CLIENT_ID: 'e2e-client',
    VITE_API_URL: 'http://localhost:8000',
    OAUTH_MOCK_TOKEN_ENDPOINT: 'http://localhost:4444/token',
    OAUTH_VALID_ISSUERS: 'http://localhost:4444',
    JWKS_URL: 'http://localhost:4444/jwks',
    OAUTH_REDIRECT_URI: 'http://localhost:5173/',
    GOOGLE_CLIENT_ID: 'e2e-client',
  }

  // Copy env vars into current process so Vite (webServer) picks them up
  Object.assign(process.env, env)

  // Start backend with the env vars already set
  const repoRoot = path.resolve(__dirname, '..')
  backendProcess = spawn('uv', ['run', 'python', '-m', 'dev.server'], {
    cwd: path.join(repoRoot, 'backend'),
    env,
    stdio: ['ignore', 'ignore', 'inherit'],
  })

  const start = Date.now()
  let ready = false
  while (Date.now() - start < 15000) {
    try {
      await fetch('http://localhost:8000/')
      ready = true
      break
    } catch {
      // not ready yet
    }
    await new Promise((r) => setTimeout(r, 300))
  }
  if (!ready) throw new Error('Backend did not become ready within 15s')
}
