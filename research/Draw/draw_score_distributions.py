#!/usr/bin/env python3
"""
使用 new_format_clean 生成的 valid_cases.json 数据
绘制 Figure-7：评分分布箱线图
- 数据来源：最后一轮的 evaluation_scores
- 评分维度：7 个维度（如 CI, CQ, IC 等）
- 输出文件：score_distributions.png
"""
import os, json, numpy as np, matplotlib.pyplot as plt, matplotlib, seaborn as sns
import argparse
from collections import defaultdict


# ---------- 1. 配置 ----------
# 1. 维度 key 清单（7 维）
EVALUATION_DIMENSIONS = [
    'clinical_inquiry',
    'communication_quality',
    'information_completeness',   # 你实际有的第 7 维
    'overall_professionalism',
    'present_illness_similarity',
    'past_history_similarity',
    'chief_complaint_similarity'
]

# 2. 缩写标签
DIMENSION_NAMES = {
    'clinical_inquiry': 'CI',
    'communication_quality': 'CQ',
    'information_completeness': 'IC',
    'overall_professionalism': 'OP',
    'present_illness_similarity': 'HPIS',
    'past_history_similarity': 'PHS',
    'chief_complaint_similarity': 'CCS'
}

COLORS = ['#FF6B9D', '#C44569', '#F8B500', '#6C7B7F',
          '#00D2D3', '#55A3FF', '#786FA6', '#F19066']

# ---------- 2. 样式（与旧脚本完全一致） ----------
plt.style.use('seaborn-v0_8-whitegrid')
matplotlib.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 18,
    'axes.linewidth': 1.2,
    'grid.linewidth': 0.8,
    'lines.linewidth': 2.5,
    'axes.labelsize': 18,
    'xtick.labelsize': 18,
    'ytick.labelsize': 18,
    'axes.unicode_minus': False
})

# ---------- 3. 数据加载 ----------
def load_a_grade_cases(cleaned_data_dir):
     with open(os.path.join(cleaned_data_dir, 'valid_cases.json'), 'r', encoding='utf-8') as f:
        return json.load(f)
# ---------- 4. 抽取最后一轮分数 ----------
def extract_final_scores(cases):
    dim_scores = defaultdict(list)
    for case in cases:
        if not case['rounds']: continue
        final = case['rounds'][-1]
        ev_scores = final.get('evaluation_scores') or {}
        for d in EVALUATION_DIMENSIONS:
            sc = ev_scores.get(d, {}).get('score')
            if isinstance(sc, (int, float)):
                dim_scores[d].append(float(sc))

        # ===== debug：看哪一维完全没数据 =====
    for d in EVALUATION_DIMENSIONS:
        if not dim_scores[d]:
            print(f"[警告] 维度 {d} 无有效 score，Figure 7 将跳过该箱体！")
    # =====================================
    return dim_scores

# ---------- 5. IQR=0 修复 ----------
def fix_boxplot_data(scores):
    arr = np.array(scores, dtype=float)
    q1, q3 = np.percentile(arr, [25, 75])
    if q1 == q3:
        median, std = np.median(arr), np.std(arr)
        eps = np.random.normal(0, max(0.001, std/10), size=arr.shape)
        arr = np.where(arr == median, arr + eps, arr)
    return arr.tolist()

# ---------- 6. 画图 ----------
def generate_figure(dimension_scores, figures_dir, output_file):
    fig, ax = plt.subplots(figsize=(16, 9))

    plot_data, labels, means = [], [], []
    for d in EVALUATION_DIMENSIONS:
        sc = dimension_scores[d]
        if sc:
            fixed = fix_boxplot_data(sc)
            plot_data.append(fixed)
            labels.append(DIMENSION_NAMES[d])
            means.append(np.mean(sc))

    bp = ax.boxplot(plot_data, patch_artist=True, showmeans=True, meanline=True,
                    showfliers=False,
                    boxprops=dict(linewidth=1.5),
                    whiskerprops=dict(linewidth=1.5),
                    capprops=dict(linewidth=1.5),
                    medianprops=dict(linewidth=2.5, color='black'),
                    meanprops=dict(linewidth=2, color='red', linestyle='--'),
                    widths=0.6)

    ax.set_xticklabels(labels)
    for patch, color in zip(bp['boxes'], COLORS):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
        patch.set_edgecolor('white')

    ax.set_ylabel('Evaluation Score', fontweight='bold')
    ax.grid(True, axis='y', alpha=0.3)
    ax.set_axisbelow(True)
    sns.despine(ax=ax, top=True, right=True)

    # 均值文字
    for i, m in enumerate(means):
        ax.text(i+1, m+0.2, f'{m:.2f}', ha='center', va='bottom', fontsize=18,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

    # 图例
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], color='red', linestyle='--', linewidth=2, label='Mean'),
                       Line2D([], [], color='black', linewidth=2.5, label='Median')],
              loc='upper left', frameon=True, fancybox=True, shadow=True)

    plt.tight_layout()
    out_file = os.path.join(figures_dir, output_file)
    plt.savefig(out_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

# ---------- 7. main ----------
def main(cleaned_data_dir, figures_dir, output_file):
    # 绘图逻辑
    os.makedirs(figures_dir, exist_ok=True)
    print(f"绘制学习曲线：从 {cleaned_data_dir} 到 {figures_dir}/{output_file}")
    
    cases = load_a_grade_cases(cleaned_data_dir)
    scores = extract_final_scores(cases)
    generate_figure(scores, figures_dir, output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="绘制学习曲线脚本")
    parser.add_argument("--cleaned_data_dir", required=True, help="清洗后数据目录")
    parser.add_argument("--figures_dir", required=True, help="图表输出目录")
    parser.add_argument("--output_file", required=True, help="输出文件名")
    args = parser.parse_args()

    main(args.cleaned_data_dir, args.figures_dir, args.output_file)