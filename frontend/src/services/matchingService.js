// frontend/src/services/matchingService.js
import { apiGet } from './api'

/** Ranked opposite-gender matches for a user (admin/supervisor). */
export function getMatchesForUser(userId, options = {}) {
  const params = new URLSearchParams()
  if (options.status) params.set('status', options.status)
  if (options.minScore != null) params.set('min_score', String(options.minScore))
  if (options.limit != null) params.set('limit', String(options.limit))
  if (options.includeIneligible) params.set('include_ineligible', 'true')
  const query = params.toString()
  return apiGet(`/admin/users/${userId}/matches${query ? `?${query}` : ''}`)
}

/** Full score breakdown for a specific pair of users. */
export function scoreUserPair(userAId, userBId) {
  return apiGet(`/admin/matches/pair?user_a=${userAId}&user_b=${userBId}`)
}
