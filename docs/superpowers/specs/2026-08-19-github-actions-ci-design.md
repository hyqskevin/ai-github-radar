# Spec — T121 GitHub Actions CI

| 维度 | 内容 |
|---|---|
| **TODO ID** | T121-T123 |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 中 — 后续合并 PR 都需要 CI 绿 |

---

## B1. 目标

1. PR 触发后自动跑所有测试 + audit + lint
2. 任何 commit push 到 main 后跑后端 + 前端 e2e
3. 不引入外部服务依赖(只跑本地 mock backend)

---

## B2. Workflow 结构

```
.github/workflows/
├── backend-ci.yml        # Python: ruff + pytest + audit + design-check
├── frontend-ci.yml       # Nuxt: pnpm test + pnpm test:e2e + build
└── ci.yml                # 总入口(同时跑后端 + 前端, fast-fail)
```

**职责划分**:
- `backend-ci.yml`:只在 `src/`, `tests/unit`, `scripts/`, `pyproject.toml` 改动时跑
- `frontend-ci.yml`:只在 `app/web/` 改动时跑
- `ci.yml`:并行跑两者,任一 fail 整个 PR fail

---

## B3. backend-ci.yml 设计

```yaml
name: backend-ci

on:
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'
      - 'scripts/**'
      - 'pyproject.toml'
      - '.github/workflows/backend-ci.yml'
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip

      - name: Install uv
        run: pip install uv

      - name: Setup venv
        run: |
          uv venv
          source .venv/bin/activate
          uv pip install -e '.[dev]'

      - name: ruff check
        run: |
          source .venv/bin/activate
          ruff check src tests scripts

      - name: ruff format check
        run: |
          source .venv/bin/activate
          ruff format --check src tests scripts

      - name: audit-loop
        run: |
          source .venv/bin/activate
          python3 scripts/audit-loop.py --strict

      - name: design-check
        run: python3 scripts/design-check.py

      - name: pytest + coverage
        run: |
          source .venv/bin/activate
          PYTHONPATH=src .venv/bin/python -m pytest tests/unit --cov=src/ai_github_radar --cov-report=xml --cov-report=term --cov-fail-under=80

      - name: Upload coverage
        if: always()
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false  # 阶段二再严格
```

**关键**:
- `paths:` 过滤,避免前端 PR 触发后端
- `cache: pip` 加速(uv 会自动 cache 吗?--试一下;不行再加 `actions/cache`)
- `--cov-fail-under=80` 强制覆盖率 >=80%(阶段一 89%)
- `fail_ci_if_error: false` 不阻塞 codecov 上传失败

---

## B4. frontend-ci.yml 设计

```yaml
name: frontend-ci

on:
  pull_request:
    paths:
      - 'app/web/**'
      - '.github/workflows/frontend-ci.yml'
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    defaults:
      run:
        working-directory: app/web
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: pnpm

      - name: Install pnpm
        run: npm install -g pnpm@11

      - name: Setup
        run: pnpm install --frozen-lockfile

      - name: Install Playwright browsers
        run: pnpm exec playwright install --with-deps chromium

      - name: Vitest unit tests
        run: pnpm test

      - name: Vitest coverage
        run: pnpm test -- --coverage

      - name: Build
        run: pnpm build

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: app/web/.playwright-report
          retention-days: 7

  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: app/web
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: pnpm

      - name: Install pnpm
        run: npm install -g pnpm@11

      - name: Setup
        run: pnpm install --frozen-lockfile

      - name: Install Playwright browsers
        run: pnpm exec playwright install --with-deps chromium

      - name: Build for preview
        run: pnpm build
        env:
          NITRO_PRESET: node-server

      - name: Start preview server
        run: |
          nohup pnpm preview > preview.log 2>&1 &
          echo "PID=$!"
          for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
            if curl -sf http://127.0.0.1:3000/api/keywords >/dev/null; then
              echo "✓ preview server ready"
              break
            fi
            sleep 2
          done

      - name: Run Playwright e2e
        run: |
          PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 \
            PLAYWRIGHT_NO_SERVER=1 \
            pnpm exec playwright test --reporter=list

      - name: Stop preview
        if: always()
        run: pkill -f "node.*server.mjs" || true
```

**关键**:
- e2e 用 `pnpm preview`(production build)而非 `pnpm dev` (dev server 慢 + JIT)
- `PLAYWRIGHT_NO_SERVER=1` 让 playwright 不自己启 dev server
- 步骤拆 jobs 防止 build 拖累 test 速度

---

## B5. ci.yml 设计(总入口)

```yaml
name: ci

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  backend:
    uses: ./.github/workflows/backend-ci.yml
  frontend:
    uses: ./.github/workflows/frontend-ci.yml
```

**为什么用 reusable workflow?**
- 后端 / 前端 独立失败信息
- 并行触发(默认 behavior)

---

## B6. 风险

- **R1**: GitHub 免费 runner 30min timeout — 留 15-20min 应该够
- **R2**: Playwright 装 chromium + deps 慢(~3min)— 用 `--with-deps` 自动装系统 lib
- **R3**: pnpm cache 在自托管 runner 上可能要 `--cache-dependency-path=app/web/pnpm-lock.yaml`
- **R4**: `actions/setup-node` 默认 cache 是 `~/.npm` 不是 `~/.local/share/pnpm` — 用 pnpm action `pnpm/action-setup@v4` 更稳

---

## B7. 测试

| AC | 怎么验 |
|---|---|
| YAML 合法 | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/backend-ci.yml'))"` |
| paths 触发过滤 | 看 on: 块 |
| 步骤顺序合理 | 跑 yaml parse |
| 覆盖率门槛 | `--cov-fail-under=80` 在 pytest step |

**本地验证**:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/backend-ci.yml')); print('OK')"
```