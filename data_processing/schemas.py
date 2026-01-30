"""
爱爱医病历数据采集模块 - 数据提取Schema

定义用于JsonCssExtractionStrategy的数据提取模式
"""

from typing import Dict


def get_case_extraction_schema() -> Dict:
    """
    获取病例详情提取的JSON Schema
    
    基于对HTML结构的分析，设计精确的CSS选择器来提取：
    - 发布人信息
    - 病例摘要
    - 病案介绍
    - 诊治过程
    - 分析总结
    """
    
    schema = {
        "name": "爱爱医病例详情",
        "baseSelector": "body",  # 整个页面作为基础
        "fields": [
            {
                "name": "title", 
                "selector": "h2", 
                "type": "text"
            },
            {
                "name": "publisher_info", 
                "selector": ".doctor_desc", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "publisher_name", 
                "selector": ".doctor_desc span", 
                "type": "text"
            },
            {
                "name": "publisher_title", 
                "selector": ".doctor_desc i", 
                "type": "text"
            },
            {
                "name": "publisher_update_time", 
                "selector": ".doctor_desc p:last-child", 
                "type": "text"
            },
            {
                "name": "case_summary", 
                "selector": ".case_summary.position1", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "case_summary_structured", 
                "selector": ".case_summary.position1 .situation p", 
                "type": "multiple",
                "fields": [
                    {
                        "name": "label", 
                        "selector": "var", 
                        "type": "text"
                    },
                    {
                        "name": "content", 
                        "selector": "span", 
                        "type": "text"
                    }
                ]
            },
            {
                "name": "case_introduction", 
                "selector": ".case_study.position2", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "diagnosis_treatment", 
                "selector": ".case_study.position3", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "analysis_summary", 
                "selector": ".case_study.position4", 
                "type": "text",
                "transformers": ["clean_text"]
            },
            {
                "name": "tags", 
                "selector": ".doctors_excel a.on span", 
                "type": "text"
            },
            {
                "name": "department", 
                "selector": ".breadcrumbs a:last-child", 
                "type": "text"
            },
            {
                "name": "images", 
                "selector": ".case_focus_map img", 
                "type": "multiple",
                "fields": [
                    {
                        "name": "src", 
                        "selector": "", 
                        "type": "attribute", 
                        "attribute": "src"
                    },
                    {
                        "name": "alt", 
                        "selector": "", 
                        "type": "attribute", 
                        "attribute": "alt"
                    }
                ]
            }
        ]
    }
    
    return schema


def get_simple_case_extraction_schema() -> Dict:
    """
    简化的病例提取Schema，处理可能的选择器变化
    """
    
    schema = {
        "name": "爱爱医病例详情_简化版",
        "baseSelector": "body",
        "fields": [
            {
                "name": "page_title", 
                "selector": "title", 
                "type": "text"
            },
            {
                "name": "case_title", 
                "selector": "h2", 
                "type": "text"
            },
            {
                "name": "publisher_info", 
                "selector": ".doctor_desc, .doctor_desc_left", 
                "type": "text"
            },
            {
                "name": "case_summary", 
                "selector": ".case_summary, .case_summary.position1, .situation", 
                "type": "text"
            },
            {
                "name": "case_content", 
                "selector": ".case_study, .case_study.position2, .case_study.position3, .case_study.position4", 
                "type": "text"
            },
            {
                "name": "main_content", 
                "selector": ".case_details_left, .case_details_cont", 
                "type": "text"
            }
        ]
    }
    
    return schema
