#!/usr/bin/env python3
"""
- 针对 results 结果部分的数据清洗
- 每轮子任务完成数 = triage.completed + hpi.completed + ph.completed
- 总任务数固定为 13（2+6+5）
- 生成 valid_cases.json 供绘图使用
"""
import os
import json
import glob
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
import numpy as np

# 设置项目根目录
PROJ_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJ_ROOT))

# ---------- 路径 ----------
def get_paths() -> Dict[str, str]:
    return {
        "DATA_DIR": str(PROJ_ROOT / "results_11_30/results_11_30_Agent_Driven"),
        "CLEANED_DATA_DIR": str(PROJ_ROOT / "research/Draw/clean_workflow_valid/cleaned_data"),
    }

# ---------- 清洗器 ----------
class NewFormatCleaner:
    def __init__(self, data_dir: str, cleaned_dir: str):
        self.data_dir = data_dir
        self.cleaned_dir = cleaned_dir
        os.makedirs(self.cleaned_dir, exist_ok=True)

    # ---------------- T1/T2/T3 完成标记 ----------------
    def _extract_task_done(self, events: List[dict]) -> dict:
        step_done = {}
        for ev in events:
            if ev.get("event_type") == "step_complete" and "task_completion_summary" in ev:
                phases = ev["task_completion_summary"]["phases"]
                sn = ev["step_number"]
                step_done[sn] = {
                    "t1_done": phases.get("triage", {}).get("is_completed", False),
                    "t2_done": phases.get("hpi", {}).get("is_completed", False),
                    "t3_done": phases.get("ph", {}).get("is_completed", False),
                    "triage_completed": phases.get("triage", {}).get("completed", 0),
                    "hpi_completed": phases.get("hpi", {}).get("completed", 0),
                    "ph_completed": phases.get("ph", {}).get("completed", 0),
                }
        return step_done

    # ---------------- 单病例处理 ----------------
    def process_file(self, file_path: str) -> Optional[dict]:
        case_id = int(os.path.basename(file_path).split('_')[-1].split('.')[0])
        events = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        threshold = 0.85
        for ev in events:
            if ev.get("event_type") == "workflow_start":
                threshold = ev["workflow_config"]["completion_threshold"]
                break

        task_scores_by_round: Dict[int, Dict[str, float]] = defaultdict(dict)
        for ev in events:
            if ev.get("event_type") == "task_scores_update":
                rnd = ev["step_number"]
                for task, score in ev["new_scores"].items():
                    if isinstance(score, set):
                        score = max(score) if score else 0.0
                    if isinstance(score, (np.integer, np.floating)):
                        score = float(score.item())
                    task_scores_by_round[rnd][task] = float(score)

        step_done = self._extract_task_done(events)

        eval_scores_cache: Dict[int, dict] = {}
        for ev in events:
            if ev.get("event_type") == "agent_execution" and ev.get("agent_name") == "evaluator":
                sn = ev["step_number"]
                eval_scores_cache[sn] = ev["output_data"]

        rounds, t1, t2, t3, max_round = [], None, None, None, 0
        for ev in events:
            if ev.get("event_type") == "agent_execution" and "step_number" in ev:
                sn = ev["step_number"]
                max_round = max(max_round, sn)
                out_data = ev.get("output_data") or {}

                step_info = step_done.get(sn, {})
                completed_count = (
                    step_info.get("triage_completed", 0) +
                    step_info.get("hpi_completed", 0) +
                    step_info.get("ph_completed", 0)
                )
                total_count = 13  # ✅ 强制为13
                completion_rate = completed_count / total_count if total_count else 0.0

                rounds.append({
                    "case_index": case_id,
                    "round": sn,
                    "timestamp": ev["timestamp"],
                    "agent_name": ev["agent_name"],
                    "input_data": ev.get("input_data"),
                    "output_data": out_data,
                    "execution_time_seconds": ev.get("execution_time_seconds"),
                    "is_t1_done": step_done.get(sn, {}).get("t1_done", False),
                    "is_t2_done": step_done.get(sn, {}).get("t2_done", False),
                    "is_t3_done": step_done.get(sn, {}).get("t3_done", False),
                    "is_final": False,
                    "current_subtask": "",
                    "evaluation_scores": eval_scores_cache.get(sn),
                    "subtasks_detail": {
                        "completed_count": completed_count,
                        "total_count": total_count,
                        "completion_rate": completion_rate,
                        "task_scores": {k: v for k, v in task_scores_by_round.get(sn, {}).items()},
                        "triage_completed": step_info.get("triage_completed", 0),
                        "hpi_completed": step_info.get("hpi_completed", 0),
                        "ph_completed": step_info.get("ph_completed", 0),
                    },
                })

                if step_done.get(sn, {}).get("t1_done") and t1 is None:
                    t1 = sn
                if step_done.get(sn, {}).get("t2_done") and t2 is None:
                    t2 = sn
                if step_done.get(sn, {}).get("t3_done") and t3 is None:
                    t3 = sn


        return {
            "case_index": case_id,
            "file_path": file_path,
            "case_info": None,
            "rounds": rounds,
            "final_summary": None,
            "t1_done_round": t1,
            "t2_done_round": t2,
            "t3_done_round": t3,
            "max_round": max_round,
            "is_valid": True,
            "filter_reason": None,
        }

    # ---------------- 批量流程 ----------------
    def run(self):
        files = sorted(glob.glob(os.path.join(self.data_dir, "workflow_*_case_*.jsonl")))
        valid_cases = []
        for fp in files:
            case_data = self.process_file(fp)
            if case_data:
                valid_cases.append(case_data)

        out_file = os.path.join(self.cleaned_dir, "valid_cases.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(valid_cases, f, ensure_ascii=False, indent=2)
        print(f"[NewFormatCleaner] 共 {len(valid_cases)} 个有效病例 → {out_file}")

# ---------- 入口 ----------
def main(data_dir, output_dir):
    # 数据清洗逻辑
    os.makedirs(output_dir, exist_ok=True)
    print(f"清洗数据：从 {data_dir} 到 {output_dir}")
    paths = get_paths()
    cleaner = NewFormatCleaner(data_dir, output_dir)
    cleaner.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数据清洗脚本")
    parser.add_argument("--data_dir", required=True, help="原始数据目录")
    parser.add_argument("--output_dir", required=True, help="清洗后数据输出目录")
    args = parser.parse_args()

    main(args.data_dir, args.output_dir)