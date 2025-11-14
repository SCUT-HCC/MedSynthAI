import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from .schemas import PatientCase, Dataset

class DatasetManager:
    """数据集管理类"""
    
    def __init__(self, base_dir: str = "datasets"):
        """初始化数据集管理器"""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.base_dir / "metadata.json"
        self._init_metadata()
    
    def _init_metadata(self):
        """初始化元数据文件"""
        if not self.metadata_file.exists():
            dataset = Dataset(
                name="medical_cases",
                description="医疗问诊病例数据集",
                version="1.0.0"
            )
            self._save_metadata(dataset)
    
    def _save_metadata(self, dataset: Dataset):
        """保存元数据"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(dataset.model_dump(), f, ensure_ascii=False, indent=2, default=str)
    
    def add_case(self, case: PatientCase) -> bool:
        """添加新病例到数据集"""
        try:
            case_file = self.base_dir / f"case_{case.record_id}.json"
            with open(case_file, "w", encoding="utf-8") as f:
                json.dump(case.model_dump(), f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            print(f"添加病例失败: {e}")
            return False
    
    def get_case(self, case_id: str) -> Optional[PatientCase]:
        """获取指定病例"""
        try:
            case_file = self.base_dir / f"case_{case_id}.json"
            if not case_file.exists():
                return None
            with open(case_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PatientCase(**data)
        except Exception as e:
            print(f"获取病例失败: {e}")
            return None