// server/api/keywords/[id].delete.ts
// T105 AC-2: 删关键字
import { deleteKeyword, HttpError } from '../../utils/handlers'

export default defineEventHandler((event) => {
  const id = Number(getRouterParam(event, 'id'))
  if (!Number.isFinite(id)) {
    throw createError({ statusCode: 400, statusMessage: 'id must be a number' })
  }
  try {
    deleteKeyword(id)
    setResponseStatus(event, 204)
    return null
  } catch (e) {
    if (e instanceof HttpError) {
      throw createError({ statusCode: e.statusCode, statusMessage: e.message })
    }
    throw e
  }
})