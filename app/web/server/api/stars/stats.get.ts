// server/api/stars/stats.get.ts
// T105 AC-4: star 统计
import { getStarsStats } from '../../utils/handlers'

export default defineEventHandler(() => getStarsStats())