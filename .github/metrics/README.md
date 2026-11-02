# 访问与克隆数据

`views.csv` 与 `clones.csv` 由 [`.github/workflows/traffic.yml`](../workflows/traffic.yml) 每天自动更新。

GitHub 的流量接口只返回最近 14 天的数据，工作流每天抓取一次并按日期合并，超过 14 天的记录因此可以保留下来。同一天重复抓取以最新一次为准，不会产生重复行。

| 文件 | 列 | 含义 |
|---|---|---|
| `views.csv` | `date, views, unique_visitors` | 当日浏览量、独立访客数 |
| `clones.csv` | `date, clones, unique_cloners` | 当日克隆次数、独立克隆人数 |

## 启用方式

流量接口需要仓库的 Administration 读权限，`GITHUB_TOKEN` 没有这个权限，所以要单独配置一个令牌：

1. 新建 fine-grained token，仅授权本仓库，权限选 **Administration: Read-only**。
2. 在仓库 `Settings → Secrets and variables → Actions` 中添加 secret，名称为 `TRAFFIC_TOKEN`。
3. 在 Actions 页面手动运行一次 `记录访问与克隆`，确认生成数据。

未配置 `TRAFFIC_TOKEN` 时，工作流会跳过并在日志中输出警告，不会报错。
