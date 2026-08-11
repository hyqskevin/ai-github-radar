// server/api/keywords.post.ts
// T105 AC-2: 加关键字
import { createKeyword, HttpError } from '../utils/handlers'

export default defineEventHandler(async (event) => {
  const body = await readBody<{ term?: string; weight?: number }>(event)
  try {
    setResponseStatus(event, 201)
    return createKeyword(body ?? {})
  } catch (e) {
    if (e instanceof HttpError) {
      throw createError({ statusCode: e.statusCode, statusMessage: e.message })
    }
    throw e
  }
})