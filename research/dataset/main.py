from pathlib import Path
from .manager import DatasetManager
from .schemas import PatientCase

def main():
    """数据集管理模块使用示例"""
    # 初始化数据集管理器
    dataset_dir = Path(__file__).parent / "medical_cases"
    manager = DatasetManager(str(dataset_dir))
    
    # 创建示例病例
    sample_case = PatientCase(
        record_id="CASE001",
        patient_id="P001",
        main_complaint="发热、咳嗽3天",
        age=45,
        gender="男",
        present_illness={
            "发热情况": "体温最高38.5度，间断发热",
            "咳嗽情况": "干咳为主，无痰，无胸闷气促",
            "其他症状": "轻度乏力，食欲略减"
        },
        past_history={
            "既往病史": "否认高血压、糖尿病等慢性病史",
            "过敏史": "否认药物及食物过敏史",
            "个人史": "无吸烟饮酒习惯"
        }
    )
    
    # 演示基本操作
    print("=== 数据集管理示例 ===")
    
    # 1. 添加病例
    if manager.add_case(sample_case):
        print(f"✅ 成功添加病例: {sample_case.record_id}")
    
    # 2. 读取病例
    loaded_case = manager.get_case("CASE001")
    if loaded_case:
        print("\n📋 读取的病例信息:")
        print(f"- 病例ID: {loaded_case.record_id}")
        print(f"- 主诉: {loaded_case.main_complaint}")
        print(f"- 患者信息: {loaded_case.age}岁 {loaded_case.gender}性")
    
    # 3. 清理示例数据
    if dataset_dir.exists():
        for file in dataset_dir.glob("*"):
            file.unlink()
        dataset_dir.rmdir()
        print("\n🧹 示例数据已清理")

if __name__ == "__main__":
    main()