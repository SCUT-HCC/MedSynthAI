"""
绘制 T2 和 T3 的完成轮次分布柱状图（基于 valid_cases.json）
- 数据来源：valid_cases(2).json
- 数据筛选：
  1. T2 和 T3 的完成轮次在 1~30 之间的病例
  2. 未完成的任务计入 "uncompleted"
- 输出文件：t2t3_combined_distribution.png
- 图表内容：
  1. T2 和 T3 的完成轮次分布柱状图
  2. 平均值竖线（仅统计完成轮次在 1~30 的病例）
  3. 统计信息（均值、未完成任务数等）
"""
import os, json, numpy as np, matplotlib.pyplot as plt, matplotlib
import seaborn as sns
import argparse
sns.set_style("whitegrid")

# ---------- 样式同旧 ----------
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

# ---------- 数据加载 ----------
def load_valid_cases(cleaned_data_dir):
    with open(os.path.join(cleaned_data_dir, 'valid_cases.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


# ---------- 1. 抽取 T2/T3 完成轮次 ----------
def extract_t2t3_rounds(cases):
    t2_done, t3_done = [], []   # ≤30轮完成
    t2_uf,  t3_uf  = 0, 0       # >30轮仍未完成

    for c in cases:
        # T2
        r2 = c.get('t2_done_round')
        if r2 is not None and 1 <= r2 <= 30:
            t2_done.append(r2)
        elif r2 is None:          # 未完成：认为>30
            t2_uf += 1

        # T3
        r3 = c.get('t3_done_round')
        if r3 is not None and 1 <= r3 <= 30:
            t3_done.append(r3)
        elif r3 is None:
            t3_uf += 1

    return t2_done, t3_done, t2_uf, t3_uf


# ---------- 2. 绘图（仅 T2/T3） ----------
def plot_t2t3(t2_done, t3_done, t2_uf, t3_uf, figures_dir, output_file):
    fig, ax = plt.subplots(figsize=(12, 7))

    # 横轴：1~30 外加 uncompleted 柱子，并插入空白标签
    all_rounds = list(range(1, 31)) + [''] * 2 + ['uncompleted']  # 插入3个空白标签
    x = np.arange(len(all_rounds))
    width = 0.35

    def counts(done_lst, uf):
        cnt = [done_lst.count(r) for r in range(1, 31)]
        cnt.extend([0] * 2)  # 对应空白标签的计数为0
        cnt.append(uf)      # 最后一根是 uncompleted
        return cnt

    rects2 = ax.bar(x - width/2, counts(t2_done, t2_uf), width,
                    label='T2 Task', color='#F5A623', alpha=0.8, edgecolor='w', lw=1.2)
    rects3 = ax.bar(x + width/2, counts(t3_done, t3_uf), width,
                    label='T3 Task', color='#7ED321', alpha=0.8, edgecolor='w', lw=1.2)

    # 均值竖线：只统计≤30轮完成
    mu2 = np.mean(t2_done) if t2_done else 0
    mu3 = np.mean(t3_done) if t3_done else 0
    if t2_done:
        ax.axvline(int(round(mu2)) - 1, color='#F5A623', ls='--', lw=2.5, alpha=0.7)
    if t3_done:
        ax.axvline(int(round(mu3)) - 1, color='#7ED321', ls='--', lw=2.5, alpha=0.7)

    ax.set_xlabel('Task Completion Round', fontweight='bold')
    ax.set_ylabel('Number of Cases', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) if isinstance(i, int) else i for i in all_rounds])
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_axisbelow(True)
    for sp in ax.spines.values():
        sp.set_linewidth(1.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 统计文字
    stats = (f"T2: μ={mu2:.1f}, M={np.median(t2_done):.1f}, uncompleted={t2_uf}\n"
             f"T3: μ={mu3:.1f}, M={np.median(t3_done):.1f}, uncompleted={t3_uf}")
    ax.text(0.98, 0.98, stats, transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
            va='top', ha='right', fontsize=16)

    plt.tight_layout()
    out_path = os.path.join(figures_dir, output_file)
    plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'✅ T2/T3 完成轮次图已生成 → {out_path}')
    print(f'   T2 完成(≤30)={len(t2_done)}，uncompleted={t2_uf}；'
          f'T3 完成(≤30)={len(t3_done)}，uncompleted={t3_uf}')


# ---------- 3. 主入口 ----------
def main(cleaned_data_dir, figures_dir, output_file):
    # 绘图逻辑
    os.makedirs(figures_dir, exist_ok=True)
    print(f"绘制学习曲线：从 {cleaned_data_dir} 到 {figures_dir}/{output_file}")

    cases = load_valid_cases(cleaned_data_dir)
    print(f'加载 {len(cases)} 个有效病例')
    t2_done, t3_done, t2_uf, t3_uf = extract_t2t3_rounds(cases)
    plot_t2t3(t2_done, t3_done, t2_uf, t3_uf, figures_dir, output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="绘制学习曲线脚本")
    parser.add_argument("--cleaned_data_dir", required=True, help="清洗后数据目录")
    parser.add_argument("--figures_dir", required=True, help="图表输出目录")
    parser.add_argument("--output_file", required=True, help="输出文件名")
    args = parser.parse_args()

    main(args.cleaned_data_dir, args.figures_dir, args.output_file)

