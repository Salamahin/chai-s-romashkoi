import { oauthServer, backendProcess } from './global-setup'

export default async function globalTeardown(): Promise<void> {
  backendProcess?.kill()
  await oauthServer.stop()
}
