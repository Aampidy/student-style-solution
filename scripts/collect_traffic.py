#!/usr/bin/env python3
"""抓取仓库流量数据并合并进版本化的历史文件。

GitHub 的流量接口只返回最近 14 天的数据，因此需要定时运行本脚本
（见 .github/workflows/traffic.yml），把滚动窗口累积成长期历史。

除历史文件外还会生成：
  - traffic/badge-clones.json、traffic/badge-views.json：
    README 中 shields.io endpoint 徽章读取的累计值；
  - traffic/chart.png：每日访问与克隆的双面板图，
    运行环境缺少 matplotlib 时跳过。

本地运行需要设置 TRAFFIC_TOKEN 和 GITHUB_REPOSITORY 两个环境变量。
"""

from __future__ import annotations

import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

API_ROOT = "https://api.github.com"
TRAFFIC_DIR = Path(
    os.environ.get("TRAFFIC_DIR")
    or Path(__file__).resolve().parent.parent / "traffic"
)

# 常见的令牌配置错误，直接写进日志，省去逐条排查
ERROR_HINTS = {
    401: "令牌无效或已过期，请重新生成 TRAFFIC_TOKEN。",
    403: "令牌权限不足：fine-grained token 需要 Administration: Read-only，classic token 需要 repo 权限。",
    404: "令牌没有选中该仓库（fine-grained token 的 Repository access），或仓库名有误。",
}


def gh_get(path: str, token: str) -> dict:
    """调用 GitHub REST API 并返回解析后的 JSON。"""
    req = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "student-style-solution-traffic-collector",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        hint = ERROR_HINTS.get(exc.code, "")
        message = f"GitHub API 返回 {exc.code}：{detail}"
        if hint:
            message = f"{message}\n排查提示：{hint}"
        raise RuntimeError(message) from exc


def merge_daily(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """按日期合并历史数据。

    同一天可能被多次抓取，当天计数会随时间增长，所以重叠日期取最大值；
    日期滑出 14 天窗口后，保留下来的就是最终值。
    """
    by_ts: dict[str, dict] = {row["timestamp"]: row for row in existing}
    for row in incoming:
        ts = row["timestamp"]
        prev = by_ts.get(ts)
        if prev is None:
            by_ts[ts] = {
                "timestamp": ts,
                "count": row["count"],
                "uniques": row["uniques"],
            }
        else:
            by_ts[ts] = {
                "timestamp": ts,
                "count": max(prev["count"], row["count"]),
                "uniques": max(prev["uniques"], row["uniques"]),
            }
    return sorted(by_ts.values(), key=lambda r: r["timestamp"])


def write_history(name: str, data: dict) -> list[dict]:
    """把接口数据合并进 JSON 与 CSV 历史文件，返回合并后的完整历史。"""
    TRAFFIC_DIR.mkdir(parents=True, exist_ok=True)
    json_path = TRAFFIC_DIR / f"{name}.json"
    csv_path = TRAFFIC_DIR / f"{name}.csv"

    existing: list[dict] = []
    if json_path.exists():
        existing = json.loads(json_path.read_text(encoding="utf-8")).get("history", [])

    merged = merge_daily(existing, data.get(name, []))
    payload = {
        "totals": {
            "count": sum(r["count"] for r in merged),
            "uniques_last_seen": data.get("uniques", 0),
            "count_last_window": data.get("count", 0),
        },
        "history": merged,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "count", "uniques"])
        for row in merged:
            writer.writerow([row["timestamp"], row["count"], row["uniques"]])

    return merged


def write_badge(name: str, label: str, value: int, color: str) -> None:
    """生成 shields.io endpoint 格式的徽章文件。"""
    badge = {
        "schemaVersion": 1,
        "label": label,
        "message": f"{value:,}".replace(",", " "),
        "color": color,
    }
    (TRAFFIC_DIR / f"badge-{name}.json").write_text(
        json.dumps(badge, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def render_chart(clones: list[dict], views: list[dict], repo: str) -> None:
    """把历史数据画成双面板折线图；没有数据时生成一张等待占位图。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError:
        print("未安装 matplotlib，跳过图表生成", file=sys.stderr)
        return

    def parse(rows: list[dict]) -> tuple[list, list]:
        dates = [
            datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
            for r in rows
        ]
        values = [r["count"] for r in rows]
        return dates, values

    views_dates, views_values = parse(views)
    clone_dates, clone_values = parse(clones)

    fig, (ax_views, ax_clones) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    fig.patch.set_facecolor("white")

    panels = (
        (ax_views, views_dates, views_values, "#2563eb", "Views / day"),
        (ax_clones, clone_dates, clone_values, "#16a34a", "Clones / day"),
    )
    for ax, dates, values, color, ylabel in panels:
        ax.set_ylabel(ylabel, fontsize=11)
        if not dates:
            ax.text(
                0.5, 0.5, "No data yet",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=11, color="#9ca3af",
            )
            continue
        ax.fill_between(dates, values, alpha=0.25, color=color)
        ax.plot(dates, values, color=color, linewidth=2, marker="o", markersize=4)
        # 标注最近一天，避免把数据末端误看成坐标轴刻度
        ax.annotate(
            f"{dates[-1]:%d %b}: {values[-1]}",
            xy=(dates[-1], values[-1]),
            xytext=(-14, 22),
            textcoords="offset points",
            ha="right",
            fontsize=9,
            fontweight="bold",
            color=color,
            bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": color, "alpha": 0.95},
            arrowprops={"arrowstyle": "-", "color": color, "lw": 1},
        )

    last_dates = [dates[-1] for _, dates, _, _, _ in panels if dates]
    if last_dates:
        subtitle = f"last data point: {max(last_dates):%d %b %Y}"
    else:
        subtitle = "waiting for the first collection"
    ax_views.set_title(
        f"Repository traffic — {repo}"
        f"    (total: {sum(views_values):,} views • {sum(clone_values):,} clones)"
        .replace(",", " ")
        + f"\n{subtitle}",
        fontsize=12,
        fontweight="bold",
    )

    for ax in (ax_views, ax_clones):
        ax.grid(alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # 完全没有数据时不显示日期轴，避免出现无意义的默认刻度
    if not views_dates and not clone_dates:
        ax_clones.xaxis.set_visible(False)

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(TRAFFIC_DIR / "chart.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    token = os.environ.get("TRAFFIC_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token:
        print(
            "缺少 TRAFFIC_TOKEN：请在仓库 Settings → Secrets and variables → "
            "Actions → Repository secrets 中配置，而不是 Environment secrets。",
            file=sys.stderr,
        )
        return 1
    if not repo:
        print(
            "缺少 GITHUB_REPOSITORY：Actions 会自动提供；本地运行请手动设置。",
            file=sys.stderr,
        )
        return 1

    try:
        clones = gh_get(f"/repos/{repo}/traffic/clones", token)
        views = gh_get(f"/repos/{repo}/traffic/views", token)
    except RuntimeError as exc:
        print(f"拉取流量数据失败：{exc}", file=sys.stderr)
        return 1

    clones_history = write_history("clones", clones)
    views_history = write_history("views", views)

    clones_total = sum(r["count"] for r in clones_history)
    views_total = sum(r["count"] for r in views_history)

    write_badge("clones", "clones", clones_total, "16a34a")
    write_badge("views", "views", views_total, "2563eb")

    render_chart(clones_history, views_history, repo)

    print(f"已更新 {repo} 的流量数据：{TRAFFIC_DIR}")
    print(f"  累计克隆：{clones_total} 次 | 累计访问：{views_total} 次")
    return 0


if __name__ == "__main__":
    sys.exit(main())
