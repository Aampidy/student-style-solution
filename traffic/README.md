# 访问与克隆数据

`README.md` 顶部的两个徽章和图表由 [`.github/workflows/traffic.yml`](../.github/workflows/traffic.yml) 每天自动更新，数据来自 GitHub 的仓库流量接口。

GitHub 只提供最近 14 天的数据，工作流每天抓取一次，把滚动窗口合并成长期历史。同一天重复抓取取当日最大值：当天计数会随时间增长，取最大值才是最终值。

| 文件 | 含义 |
|---|---|
| `clones.csv` / `clones.json` | 克隆次数与独立克隆人数，按日期累计 |
| `views.csv` / `views.json` | 浏览量、独立访客数，按日期累计 |
| `badge-clones.json` / `badge-views.json` | shields.io endpoint 徽章读取的累计值 |
| `chart.png` | 全部历史数据的双面板图，每次运行重新生成 |

## 启用方式

流量接口需要仓库的 Administration 读权限，`GITHUB_TOKEN` 没有这个权限，需要单独配置令牌：

1. 新建 fine-grained token，仅授权本仓库，仓库权限选 **Administration: Read-only**；classic token 则勾选 `repo`。
2. 在仓库 `Settings → Secrets and variables → Actions → Repository secrets` 中添加 `TRAFFIC_TOKEN`。必须配在仓库级，Environment secret 在未指定 environment 的 job 中读不到。
3. 在 Actions 页面手动运行一次「记录访问与克隆」，确认生成数据。

secret 缺失或权限不足时，工作流会直接失败，日志中会给出对应的排查提示。
