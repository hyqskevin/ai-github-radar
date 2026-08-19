# Spec — T115 本地部署 + 周期调度

| 维度 | 内容 |
|---|---|
| **TODO ID** | T115-T119 |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 高 — 用户明确要"不用 docker 直接本地部署" |

---

## B1. 设计目标

1. 用户 clone 仓库 → 跑 3 条命令 → 两端服务跑起来(后端 :8765 + 前端 :5173)
2. 系统级周期调度:macOS launchd / Linux systemd **user service**(无需 root)
3. **不引入新依赖**(用 uv + python + node + 已有二进制)

---

## B2. 架构

```
                    ┌─ Python FastAPI ── :8765 ──┐
   launchd /        │  ai_github_radar.web         │
   systemd timer ──►│  scan 触发 → push ──► 飞书/邮件/文件│
   (每 24h 一次)    │  SQLite: data/radar.db        │
                    └──────────────────────────────┘
                              ▲
                              │ /api/integration/health
                              │ 透传 GET /api/keywords
                    ┌──────────────────────────────┐
   用户浏览器 ──► │  Nuxt 4 (pnpm dev / SSR)        │
   http://...:5173 │  :5173                          │
                    └──────────────────────────────┘
```

**关键设计**:
- 周期调度只调 **Python scan 命令**(不动前端服务)
- 前端服务可选起(用户手动起;或另起一个 launchd 拉 Nuxt)
- **launchd plist 用 `KeepAlive=false`**(跑完即退出)+ `StartInterval=86400` 每 24h 触发一次
- **systemd user timer** 同样的语义

---

## B3. 文件结构

```
scripts/
├── dev.sh                     # 一键起两端 (已有, 改写)
├── setup-python.sh            # 已有
├── setup-node.sh              # 已有
├── install-launchd.sh         # 新: macOS 安装 plist + 启动
├── install-systemd.sh         # 新: Linux 安装 systemd user service + timer
├── uninstall-launchd.sh       # 新
├── uninstall-systemd.sh       # 新
└── log-rotate/                # 新: logrotate conf for Linux

app/web/
└── (Nitro 端, 不动)
```

---

## B4. launchd plist 设计

```xml
<!-- ~/Library/LaunchAgents/com.ai-github-radar.scanner.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai-github-radar.scanner</string>
    <key>ProgramArguments</key>
    <array>
        <string>/ABS/PATH/TO/.venv/bin/python</string>
        <string>-m</string>
        <string>ai_github_radar</string>
        <string>scan</string>
        <string>--push</string>
        <string>local</string>
        <string>--top</string>
        <string>10</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/ABS/PATH/TO/REPO</string>
    <key>StandardOutPath</key>
    <string>/ABS/PATH/TO/data/logs/scanner.log</string>
    <key>StandardErrorPath</key>
    <string>/ABS/PATH/TO/data/logs/scanner.err</string>
    <key>StartInterval</key>
    <integer>86400</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <false/>
    </dict>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/ABS/PATH/TO/.venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

**关键点**:
- `StartInterval=86400` 每 24h 一次(launchd 跟 wall-clock 不同, 24h = 1 day 实际)
- `RunAtLoad=true` 装上立刻跑一次
- `KeepAlive.SuccessfulExit=false` 成功后不重启(避免死循环)
- `KeepAlive.Crashed=false` 崩溃也不重启(launchd 调度轮询太多次反而烦)

---

## B5. systemd timer 设计

```ini
# ~/.config/systemd/user/ai-github-radar-scan.service
[Unit]
Description=ai-github-radar scanner (run scan + push)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/ABS/PATH/TO/REPO
ExecStart=/ABS/PATH/TO/.venv/bin/python -m ai_github_radar scan --push local --top 10
StandardOutput=append:/ABS/PATH/TO/data/logs/scanner.log
StandardError=append:/ABS/PATH/TO/data/logs/scanner.err

[Install]
WantedBy=default.target
```

```ini
# ~/.config/systemd/user/ai-github-radar-scan.timer
[Unit]
Description=Run ai-github-radar scanner every 24h

[Timer]
OnBootSec=1min
OnUnitActiveSec=24h
Persistent=true

[Install]
WantedBy=timers.target
```

**关键点**:
- `Type=oneshot` 跑完即退出
- `OnBootSec=1min` 启动后 1min 跑首次
- `OnUnitActiveSec=24h` 上次跑完后 24h 跑下次
- `Persistent=true` 错过调度时间(系统睡眠)会在开机时补跑

---

## B6. install 脚本

### install-launchd.sh
1. 解析 `$PROJECT_ROOT` (默认 `$(pwd)`)
2. `sed -e "s|@PROJECT_ROOT@|$PROJECT_ROOT|g"` 模板 → 输出 plist
3. `cp` 到 `~/Library/LaunchAgents/`
4. `launchctl load` 启动
5. `launchctl list` 验证
6. 友好 stdout:plsit 路径 + 怎么 disable / 怎么 stop

### install-systemd.sh
1. 同上 → 模板生成 `.service` + `.timer`
2. `cp` 到 `~/.config/systemd/user/`
3. `systemctl --user daemon-reload`
4. `systemctl --user enable --now ai-github-radar-scan.timer`
5. `systemctl --user list-timers` 验证

---

## B7. dev.sh 改造

旧版只跑前端。新版同时跑两端:
1. 启动 Python 后端(后台)→ :8765
2. 启动 Nuxt 前端(后台)→ :5173
3. 都设 `PYTHON_BACKEND_URL` 环境变量指向 8765
4. trap SIGINT 退出时 kill 两端

---

## B8. 测试

| AC | 怎么验 |
|---|---|
| 1. `dev.sh` 起两端 | bash 跑 + curl 两端 |
| 2. launchd plist 模板 sed 后合法 | `plutil -lint` |
| 3. systemd unit 模板 sed 后合法 | `systemd-analyze verify`(可选) |
| 4. install 脚本 dry-run 不破坏 | `--dry-run` flag |

---

## B9. 风险

- **R1**: macOS `launchctl load` 需要 `~/Library/LaunchAgents/` 存在 → `mkdir -p`
- **R2**: systemd user service 需要 `systemd --user` 支持 → 检查 `systemctl --user status`
- **R3**: 路径含空格 → 用引号包,sed 用 `|` 分隔避免冲突
- **R4**: 用户没 `loginctl enable-linger` → systemd user timer 在 logout 时不跑 → 提示用户开启