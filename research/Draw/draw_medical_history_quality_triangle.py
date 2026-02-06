import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt

# ---------- 解析输入参数 ----------
parser = argparse.ArgumentParser(description="绘制医疗历史质量三角图")
parser.add_argument('--normal_dir', type=str, required=True, help="Agent Driven 模式的清洗数据目录")
parser.add_argument('--sequence_dir', type=str, required=True, help="Medical Priority 模式的清洗数据目录")
parser.add_argument('--score_dir', type=str, required=True, help="Score Driven 模式的清洗数据目录")
parser.add_argument('--figures_dir', type=str, required=True, help="图片输出目录")
parser.add_argument('--output_file', type=str, required=True, help="输出图片文件名")
args = parser.parse_args()

# ---------- 1. 策略文件夹 ----------
STRATEGIES = [
    'Medical Priority',
    'Score Driven',
    'Agent Driven'
]
# 映射策略名称到实际的目录名称
DATA_DIRS = {
    'Medical Priority': args.sequence_dir,
    'Score Driven': args.score_dir,
    'Agent Driven': args.normal_dir
}
JSON_FILE = 'valid_cases.json'           # 统一文件名

# ---------- 2. 维度/标签/配色 ----------
DIMENSIONS = [
    'chief_complaint_similarity',
    'present_illness_similarity',
    'past_history_similarity'
]
DIMENSION_LABELS = ['CCS', 'PHS', 'HPIS']

COLORS = {
    'Medical Priority': '#2E8B57',
    'Score Driven': '#778899',
    'Agent Driven': '#4169E1'
}

# ---------- 3. 读取单个策略 ----------
def load_scores_from_folder(folder_name: str):
    """读取 folder_name/valid_cases.json，返回 {dim: [score,...]}"""
    json_path = os.path.join(folder_name, JSON_FILE)
    if not os.path.exists(json_path):
        raise FileNotFoundError(json_path)

    scores = {dim: [] for dim in DIMENSIONS}
    with open(json_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)          # list[dict]

    for case in cases:
        if not case.get('rounds'):
            continue
        final_round = case['rounds'][-1]
        ev = final_round.get('evaluation_scores') or {}
        for dim in DIMENSIONS:
            sc = ev.get(dim, {}).get('score')
            if isinstance(sc, (int, float)):
                scores[dim].append(float(sc))
    return scores


# ---------- 4. 均值 ----------
def calc_mean(scores):
    return {dim: (np.mean(vals) if vals else 0.0) for dim, vals in scores.items()}

def plot_radar(mean_scores_dict, out_path):
    angles = np.linspace(0, 2*np.pi, len(DIMENSIONS), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    max_val = 0

    for strategy, mean_scores in mean_scores_dict.items():
        values = [mean_scores[dim] for dim in DIMENSIONS]
        values += values[:1]
        max_val = max(max_val, max(values))
        ax.plot(angles, values, 'o-', lw=2.5, color=COLORS[strategy], label=strategy)
        ax.fill(angles, values, alpha=0.25, color=COLORS[strategy])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(DIMENSION_LABELS, fontsize=14, fontweight='bold')
    ax.set_ylim(2, 5)  # 修改范围为 2 到 max_val * 1.1 或至少 5
    ax.set_title('Medical History Quality Triangle', size=16, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'雷达图已保存 → {out_path}')


def main():
    mean_scores_dict = {}
    for strategy, folder in DATA_DIRS.items():
        print(f"正在处理策略: {strategy}")  # 打印策略名称
        scores = load_scores_from_folder(folder)
        if any(scores.values()):  # 至少一个维度有数据
            mean_scores = calc_mean(scores)
            mean_scores_dict[strategy] = mean_scores
            print(f"{strategy} 的均值: {mean_scores}")  # 打印均值

    if not mean_scores_dict:
        print('没有足够的数据绘制雷达图')
        return

    out_file = os.path.join(args.figures_dir, args.output_file)
    plot_radar(mean_scores_dict, out_file)


if __name__ == '__main__':
    main()