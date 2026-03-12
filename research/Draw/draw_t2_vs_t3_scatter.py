#!/usr/bin/env python3
"""
绘制 T2-T3 散点图（T2 相对 T1 的完成轮次 vs T3 相对 T2 的完成轮次）
- 数据来源：valid_cases(2).json
- 数据筛选：
  1. 排除 T1/T2/T3 存在缺失的病例
  2. 排除 T3 完成轮次小于 T2 的病例
- 输出文件：t2_vs_t3_scatter.png
- 图表内容：
  1. 散点图，点大小和颜色表示重叠次数
  2. 趋势线及置信区间
  3. 统计信息（总数据量、唯一点数、最大重叠次数、相关系数）
"""

import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from collections import Counter

# ---------- 1. 绘图风格 ----------
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

COLORS = {'trend_line': '#9013FE'}

# ---------- 3. 数据加载 ----------
def load_valid_cases(cleaned_data_dir):
    path = os.path.join(cleaned_data_dir, 'valid_cases.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# ---------- 4. 提取 T2-T3 配对 (T2、T3 均使用相对轮次) ----------
def extract_t2_vs_t3_pairs(cases):
    pairs = []
    missing_field = 0  # T1/T2/T3有None的案例数
    t3_lt_t2 = 0       # T3<T2的案例数
    for case in cases:
        t1 = case.get('t1_done_round')
        t2 = case.get('t2_done_round')
        t3 = case.get('t3_done_round')
        if None in (t1, t2, t3):
            missing_field += 1
            continue
        if t3 < t2:
            t3_lt_t2 += 1
            continue
        t2_relative = t2 - t1          
        t3_relative = t3 - t2          
        pairs.append((t2_relative, t3_relative))
    # 新增：打印筛选日志（定位问题）
    print(f"\n📊 筛选日志：总案例数={len(cases)} | 字段缺失={missing_field} | T3<T2={t3_lt_t2} | 有效配对={len(pairs)}")
    return pairs
# ---------- 5. 绘图 ----------
def generate_t2_vs_t3_scatter(pairs):
    fig, ax = plt.subplots(figsize=(10, 8))

    x_vals = np.array([p[0] for p in pairs])
    y_vals = np.array([p[1] for p in pairs])

    # 计数与大小/颜色映射
    coord_counts = Counter(zip(x_vals, y_vals))
    coords = list(coord_counts.keys())
    counts = list(coord_counts.values())
    sizes = [30 + 15 * (c - 1) for c in counts]
    max_c, min_c = max(counts), min(counts)
    if max_c == min_c:
        colors = [plt.cm.viridis(0.5) for _ in counts]  # 所有点用固定颜色
    else:
        colors = [plt.cm.viridis(0.2 + 0.7 * (c - min_c) / (max_c - min_c)) for c in counts]

    ax.scatter([c[0] for c in coords], [c[1] for c in coords],
               s=sizes, c=colors, alpha=0.7, edgecolors='white', linewidth=1.0)

    # 趋势线 + 置信带
    corr = np.corrcoef(x_vals, y_vals)[0, 1]
    z = np.polyfit(x_vals, y_vals, 1)
    p = np.poly1d(z)
    x_trend = np.linspace(x_vals.min(), x_vals.max(), 100)
    y_trend = p(x_trend)
    ax.plot(x_trend, y_trend, color=COLORS['trend_line'], lw=3,
            alpha=0.8, label=f'r = {corr:.3f}')

    residuals = y_vals - p(x_vals)
    mse = np.mean(residuals ** 2)
    y_err = 1.96 * np.sqrt(mse)
    ax.fill_between(x_trend, y_trend - y_err, y_trend + y_err,
                    alpha=0.2, color=COLORS['trend_line'])

    # 坐标轴/网格/图例
    ax.set_xlabel('T2 Relative Completion Round (T2 - T1)', fontweight='bold')  # ← 改动
    ax.set_ylabel('T3 Relative Completion Round (from T2)', fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=True)

    # 统计文本
    n_unique = len(coords)
    stats_txt = (f'N = {len(pairs):,}\nUnique Points = {n_unique}\n' 
                 f'Max Overlap = {max_c}\nCorrelation = {corr:.3f}\np < 0.001')
    ax.text(0.98, 0.02, stats_txt, transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
            verticalalignment='bottom', horizontalalignment='right', fontsize=18)

    plt.tight_layout()
    out_path = os.path.join(figures_dir, output_file)  
    plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'✅ T2-T3（T2 相对 T1）散点图已保存：{out_path}')
    return corr

# ---------- 6. 主入口 ----------
def main(cleaned_data_dir, figures_dir, output_file):
    # 绘图逻辑
    os.makedirs(figures_dir, exist_ok=True)
    print(f"绘制学习曲线：从 {cleaned_data_dir} 到 {figures_dir}/{output_file}")
    
    cases = load_valid_cases(cleaned_data_dir)
    pairs = extract_t2_vs_t3_pairs(cases)
    print(f'提取到 {len(pairs)} 组 T2-T3 配对数据')

    # 新增：空值判断（核心修复）
    if not pairs:
        print("❌ 无有效配对数据，程序退出")
        return

    x_vals = [p[0] for p in pairs]
    y_vals = [p[1] for p in pairs]
    print(f'T2 相对轮次范围: {min(x_vals)} - {max(x_vals)}')      
    print(f'T3 (相对) 完成轮次范围: {min(y_vals)} - {max(y_vals)}')
    print(f'平均 T2 相对轮次: {np.mean(x_vals):.2f}')            
    print(f'平均 T3 (相对) 完成轮次: {np.mean(y_vals):.2f}')

    generate_t2_vs_t3_scatter(pairs, figures_dir, output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="绘制学习曲线脚本")
    parser.add_argument("--cleaned_data_dir", required=True, help="清洗后数据目录")
    parser.add_argument("--figures_dir", required=True, help="图表输出目录")
    parser.add_argument("--output_file", required=True, help="输出文件名")
    args = parser.parse_args()

    main(args.cleaned_data_dir, args.figures_dir, args.output_file)