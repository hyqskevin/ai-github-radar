// server/api/keywords/[id].patch.ts
// T105 AC-2: 改关键字
import { updateKeyword, HttpError } from '../../utils/handlers'
import type { Keyword } from '../../utils/types'

export default defineEventHandler(async (event) => {
  const id = Number(getRouterParam(event, 'id'))
  if (!Number.isFinite(id)) {
    throw createError({ statusCode: 400, statusMessage: 'id must be a number' })
  }
  const body = await readBody<Partial<Omit<Keyword, 'id'>>>(event) ?? {}
  try {
    return updateKeyword(id, body)
  } catch (e) {
    if (e instanceof HttpError) {
      throw createError({ statusCode: e.statusCode, statusMessage: e.message })
    }
    throw e
  }
})