# A9 部署与运维 — ai-github-radar

> 阶段一单机 CLI，无容器化。macOS / Linux 直接跑。

## 安装

见 [INSTALL.md](../INSTALL.md)。

## 升级

```bash
cd ~/path/to/ai-github-radar
git pull
uv sync                              # 更新依赖
uv run alembic upgrade head          # DB schema 迁移
```

## 周期调度（macOS launchd）

模板文件：`scripts/com.kevin.ai-github-radar.plist`。

安装：

```bash
cp scripts/com.kevin.ai-github-radar.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.kevin.ai-github-radar.plist
launchctl start com.kevin.ai-github-radar
```

查看状态：

```bash
launchctl list | grep ai-github-radar
```

停：

```bash
launchctl unload ~/Library/LaunchAgents/com.kevin.ai-github-radar.plist
```

## 周期调度（Linux systemd）

模板：`scripts/ai-github-radar.service` + `scripts/ai-github-radar.timer`。

```bash
sudo cp scripts/ai-github-radar.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-github-radar.timer
```

## 备份

阶段一无外部存储，唯一状态在 `./data/radar.db`。

```bash
cp -r data/ data.bak.$(date +%Y%m%d)
```

定期清理：见 `data/` 目录的 rotation 策略（log 30 天，DB 看心情）。

## 监控

阶段一无外部监控。`scan` 失败时 stderr 输出 + exit code 非 0，外部调度器（launchd）会记日志到 `~/Library/Logs/`。

## 故障排查

| 现象 | 排查 |
|---|---|
| `init` 报 401 | 检查 `GITHUB_TOKEN` 是否过期 |
| `init` 报 403 | token scope 不够，要 `public_repo` |
| `scan` 没结果 | 关键字太窄，`keyword list` 看是不是没启用的 |
| 飞书推送失败 | webhook URL 失效或消息超长（飞书限制 20KB） |
| daemon 退出 | 看 `data/radar.log` 末尾的 ERROR |

## 测试覆盖

- [ ] `tests/ops/test_launchd_plist.py` — plist XML 合法
- [ ] `tests/ops/test_backup.py` — DB 备份/还原 round-trip
- [ ] `tests/e2e/test_fresh_install.sh` — 在临时目录跑通 init