// server/api/health.get.ts
// T105 AC-1
import { getHealth } from '../utils/handlers'

export default defineEventHandler(() => getHealth())