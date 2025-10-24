import logging
from loader import GuidanceLoader

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# 初始化 GuidanceLoader
loader = GuidanceLoader(
    use_department_comparison=True,
    comparison_rules_file="guidance/department_comparison_guidance.json",  # 不从文件加载，直接使用模拟数据
)


# 测试数据
examples = [
    {
        "case": "头痛意识障碍",
        "dept1": "内科-神经内科", 
        "dept2": "外科-神经外科",
        "key_points": ["外伤史", "出血征象", "手术指征"]
    },
    {
        "case": "腹痛恶心呕吐",
        "dept1": "内科-消化内科",
        "dept2": "外科-普外科", 
        "key_points": ["急腹症", "梗阻征象", "穿孔"]
    },
    {
        "case": "胸痛胸闷",
        "dept1": "内科-心血管内科",
        "dept2": "外科-心脏外科",
        "key_points": ["手术指征", "瓣膜病变", "血管病变"]
    },
    {
        "case": "手部外伤骨折",
        "dept1": "外科-手外科",
        "dept2": "外科-骨科",
        "key_points": ["手部专科性", "功能重建需求"]
    },
    {
        "case": "腰椎间盘突出",
        "dept1": "外科-脊柱外科", 
        "dept2": "外科-骨科",
        "key_points": ["解剖部位", "脊柱专业性"]
    }
]

# 运行测试
for example in examples:
    print(f"测试案例: {example['case']}")
    guidance = loader._get_comparison_guidance(example["dept1"], example["dept2"])
    print(f"对比指导:\n{guidance}")
    print("-" * 50)