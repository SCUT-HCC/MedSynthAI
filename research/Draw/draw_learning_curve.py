#!/usr/bin/env python3
"""
绘制每轮子任务完成率曲线（缺失病例按 13 补齐）
- 完成率计算公式：
  完成率 = [Σ(出现病例当期completed) + 缺失病例×13] / (总病例数×13)
- 输出文件：learning_curve.png
- 曲线包含趋势线及置信区间
"""
import os
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import argparse
from collections import defaultdict

plt.style.use('seaborn-v0_8-whitegrid')
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
matplotlib.rcParams['font.size'] = 18
matplotlib.rcParams['axes.linewidth'] = 1.2
matplotlib.rcParams['grid.linewidth'] = 0.8
matplotlib.rcParams['lines.linewidth'] = 2.5
matplotlib.rcParams['axes.labelsize'] = 18
matplotlib.rcParams['xtick.labelsize'] = 18
matplotlib.rcParams['ytick.labelsize'] = 18
matplotlib.rcParams['axes.unicode_minus'] = False

COLORS = {
    'accent_orange': '#E67E22',
    'deep_purple': '#9B59B6',
}

# ---------- 工具 ----------
def load_valid_cases(cleaned_data_dir):
    with open(os.path.join(cleaned_data_dir, 'valid_cases.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

# ---------- 数据提取（缺失病例按 13 补齐） ----------
def extract_per_round_with_missing13(cases):
    total_cases = len([c for c in cases if c.get('is_valid', True)])
    total_tasks = total_cases * 13
    print(f"[INFO] 总病例数 = {total_cases}，恒定分母 = {total_tasks}")

    # 记录每轮出现了哪些病例
    round_cases = defaultdict(set)      # round -> {case_index, ...}
    round_done  = defaultdict(int)      # round -> 出现病例的completed之和

    for case in cases:
        if not case.get('is_valid', True):
            continue
        seen_round = set()              # 防重复
        for rd in case.get('rounds', []):
            rn = rd.get('round', 0)
            if rn in seen_round:
                continue
            seen_round.add(rn)
            cnt = rd['subtasks_detail'].get('completed_count', 0)
            round_done[rn] += cnt
            round_cases[rn].add(case['case_index'])

    # 补齐缺失病例
    by_round = {}
    for rn in round_done.keys():
        missing = total_cases - len(round_cases[rn])
        by_round[rn] = round_done[rn] + missing * 13

    return dict(by_round), total_tasks

# ---------- 绘图 ----------
def generate_figure_6_curve(by_round: dict, total_tasks: int, figures_dir, output_file, max_rounds):
    rounds = sorted(by_round.keys())
    rates = [(by_round[rn] / total_tasks) * 100 for rn in rounds]

    # 画到 30 轮
    max_r = max_rounds
    rounds = [r for r in rounds if r <= max_r]
    rates = rates[:len(rounds)]

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(rounds, rates, 'o-', color=COLORS['accent_orange'],
            linewidth=3, markersize=8, markerfacecolor='white', markeredgewidth=2,
            label='Per-round completion rate')

    if len(rounds) > 3:
        z = np.polyfit(rounds, rates, 2)
        p = np.poly1d(z)
        x_smooth = np.linspace(min(rounds), max(rounds), 200)
        y_smooth = p(x_smooth)
        ax.plot(x_smooth, y_smooth, '--', color=COLORS['deep_purple'],
                alpha=0.8, linewidth=2.5, label='Trend')
        res = np.array(rates) - p(rounds)
        std = np.std(res)
        ax.fill_between(x_smooth, y_smooth - std, y_smooth + std,
                        alpha=0.2, color=COLORS['deep_purple'])

    ax.set_xlabel('Round Number', fontweight='bold')
    ax.set_ylabel('Completion Rate (%)', fontweight='bold')
    ax.set_xlim(0, max_rounds)
    ax.set_xticks(range(0, 31, 5))
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_ylim(0, 105)
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='lower right', frameon=True, fancybox=True, shadow=True)

    final_rate = rates[-1] if rates else 0
    ax.text(0.02, 0.98, f'Final Rate: {final_rate:.1f}%',
            transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
            verticalalignment='top', fontsize=18)

    out_file = os.path.join(figures_dir, output_file)
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ 完成率曲线已保存：{out_file}  （最终 {final_rate:.1f}%）")

# ---------- 主入口 ----------
def main(cleaned_data_dir, figures_dir, output_file, max_rounds):
    # 绘图逻辑
    os.makedirs(figures_dir, exist_ok=True)
    print(f"绘制学习曲线：从 {cleaned_data_dir} 到 {figures_dir}/{output_file}")

    cases = load_valid_cases(cleaned_data_dir)
    print(f"加载 {len(cases)} 个病例")
    by_round, total_tasks = extract_per_round_with_missing13(cases)
    generate_figure_6_curve(by_round, total_tasks, figures_dir, output_file, max_rounds)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="绘制学习曲线脚本")
    parser.add_argument("--cleaned_data_dir", required=True, help="清洗后数据目录")
    parser.add_argument("--figures_dir", required=True, help="图表输出目录")
    parser.add_argument("--output_file", required=True, help="输出文件名")
    parser.add_argument("--max_rounds", type=int, default=30, help="最大轮次")
    args = parser.parse_args()

    main(args.cleaned_data_dir, args.figures_dir, args.output_file, args.max_rounds)