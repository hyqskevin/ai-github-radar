# Spec: 拆分 init 任务为 stars/refresh + keywords/extract

**日期**: 2026-08-20
**TODO**: T144
**类型**: 业务重构

---

## B1 设计

### 背景
- 当前 `/api/stars/refresh` 是一个组合任务:拉 GitHub stars + 提取关键字
- 前端 settings.vue 有一个「初始化(拉取 Star + 提取关键字)」卡片,放了一个「保存配置 + 立即拉取」按钮
- 用户反馈:**拉 star 和提取关键字是两个独立任务**,应分到「我的 Star」和「关键字」两个功能卡片下
- 设置页应该只管**配置**(provider/api_key/model/base_url/github_user/github_token),不管**动作**

### 改动

**1. 后端 jobs/runner.py**
- 把 `run_init` 内部拆为:
  - `_fetch_stars(user) -> dict`:仅拉 GitHub stars,写 stars 表
  - `_extract_keywords(no_llm) -> dict`:仅从 stars 表读 + 提取关键字,写 keywords 表
- 暴露 `run_fetch_stars(user)` 和 `run_extract_keywords(no_llm=False)` 两个 public 函数
- 保留 `run_init(user, no_llm)` 作为组合版本(scheduler 用,前端不再用)
- `TASK_TYPES` 增加 `"fetch_stars"` / `"extract_keywords"`

**2. 后端 web/app.py**
- `POST /api/stars/refresh` 改调 `submit_task("fetch_stars", run_fetch_stars, user=...)`
- 新增 `POST /api/keywords/extract` → `submit_task("extract_keywords", run_extract_keywords, no_llm=...)`

**3. 前端 settings.vue**
- 删除「初始化」卡片(含「保存配置 + 立即拉取」按钮 + 「初始化流程」UAlert)
- 保留 LLM 配置卡 + GitHub 配置卡(只做配置保存)

**4. 前端 stars.vue**
- 「拉取 Star」按钮(`triggerInit`)改调 `POST /api/stars/refresh`(语义不变,后端行为变)

**5. 前端 keywords.vue**
- 新增「提取关键字」按钮(类似 stars.vue 的「拉取 Star」)
- 调 `POST /api/keywords/extract`,带 `no_llm` 切换

---

## B2 验收 AC-N

- AC-1: 后端 `jobs/runner.py` 有 `run_fetch_stars` 和 `run_extract_keywords` 两个函数
- AC-2: `POST /api/stars/refresh` 只触发 fetch_stars job,不再调 extract
- AC-3: `POST /api/keywords/extract` 触发 extract_keywords job,带 `no_llm` 参数
- AC-4: 前端 `/settings` 不再有「初始化」卡片(只剩 LLM + GitHub 两个)
- AC-5: 前端 `/stars` 「拉取 Star」按钮调 `/api/stars/refresh`;`/keywords` 「提取关键字」按钮调 `/api/keywords/extract`
- AC-6: pages_more 测试更新:settings.vue 不含「初始化」+「保存配置 + 立即拉取」字串
- AC-7: keywords.vue 测试断言:包含 `/api/keywords/extract` + 「提取关键字」字串

---

## B3 测试矩阵 (C1-C10)

- C2 单元:`test_jobs.py` 新增 `test_run_fetch_stars_only_no_keywords` + `test_run_extract_keywords_only_no_fetch`
- C6 happy:`test_app.py` 新增 `test_api_stars_refresh_triggers_fetch_stars_job` + `test_api_keywords_extract_triggers_extract_keywords_job`
- C7 edge:不传 user 时返回 4xx 或友好错误
- C8 错误路径:fetch 失败不阻塞 extract(各自独立 job)

不补 E2E(纯后端 + UI 调整)。