"""
指导规则系统模块

提供医疗问诊指导规则的加载和管理功能。
"""

from .loader import GuidanceLoader, get_comparison_guidance, update_guidance_for_triager

__all__ = [
    "GuidanceLoader"
]