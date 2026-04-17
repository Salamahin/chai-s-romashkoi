import { listEntries } from './log_service'
import type { LogWindow } from './log_service'
import { getHomeData } from './home_service'
import type { HomeData } from './home_service'
import { getProfile, getKnownTags } from './profile_service'
import type { ProfileSnapshot } from './profile_service'
import { listRelations, getKnownLabels } from './relations_service'
import type { RelationsSnapshot } from './relations_service'

export interface AppCache {
  log: LogWindow | null
  homeData: HomeData | null
  profile: ProfileSnapshot | null
  knownTags: string[]
  relations: RelationsSnapshot | null
  knownLabels: string[]
  ready: boolean
}

export function currentWeekWindow(): { weekStart: string; weekEnd: string } {
  const weekEnd = new Date()
  const weekStart = new Date(weekEnd.getTime() - 7 * 24 * 60 * 60 * 1000)
  return { weekStart: weekStart.toISOString(), weekEnd: weekEnd.toISOString() }
}

export const cache = $state<AppCache>({
  log: null,
  homeData: null,
  profile: null,
  knownTags: [],
  relations: null,
  knownLabels: [],
  ready: false,
})

export async function prefetch(token: string): Promise<void> {
  const { weekStart, weekEnd } = currentWeekWindow()

  const results = await Promise.allSettled([
    listEntries(token, weekStart, weekEnd),
    getHomeData(token),
    getProfile(token),
    getKnownTags(token),
    listRelations(token),
    getKnownLabels(token),
  ])

  const [logResult, homeResult, profileResult, tagsResult, relationsResult, labelsResult] = results

  if (logResult.status === 'fulfilled') cache.log = logResult.value
  if (homeResult.status === 'fulfilled') cache.homeData = homeResult.value
  if (profileResult.status === 'fulfilled') cache.profile = profileResult.value
  if (tagsResult.status === 'fulfilled') cache.knownTags = tagsResult.value
  if (relationsResult.status === 'fulfilled') cache.relations = relationsResult.value
  if (labelsResult.status === 'fulfilled') cache.knownLabels = labelsResult.value

  cache.ready = true
}

export async function refreshLog(token: string): Promise<void> {
  try {
    const { weekStart, weekEnd } = currentWeekWindow()
    const log = await listEntries(token, weekStart, weekEnd)
    cache.log = log
  } catch {
    // silently swallow — preserve existing cache
  }
}

export async function refreshProfile(token: string): Promise<void> {
  try {
    const [snapshot, tags] = await Promise.all([getProfile(token), getKnownTags(token)])
    cache.profile = snapshot
    cache.knownTags = tags
  } catch {
    // silently swallow — preserve existing cache
  }
}

export async function refreshRelations(token: string): Promise<void> {
  try {
    const [snap, labels] = await Promise.all([listRelations(token), getKnownLabels(token)])
    cache.relations = snap
    cache.knownLabels = labels
  } catch {
    // silently swallow — preserve existing cache
  }
}

export function clearCache(): void {
  cache.log = null
  cache.homeData = null
  cache.profile = null
  cache.knownTags = []
  cache.relations = null
  cache.knownLabels = []
  cache.ready = false
}
