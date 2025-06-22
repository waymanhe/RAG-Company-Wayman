# -*- coding: utf-8 -*-
"""
@author: hmd
@license: (C) Copyright 2021-2027, JMD.
@contact: 931725379@qq.com
@software: 
@file: intent_recognizer.py
@time: 2024/7/29 10:00
@desc: 封装意图识别逻辑，根据用户问题返回不同的Prompt模板
"""
import os
import sys

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PROMPT_TEMPLATE

class IntentRecognizer:
    """
    一个简单的意图识别器，根据用户问题返回不同的Prompt模板和系统指令。
    """
    def __init__(self):
        """
        初始化时，定义所有支持的意图及其配置。
        """
        # 定义不同意图的Prompt配置
        self.intents = {
            "SWOT_ANALYSIS": {
                "keywords": ["优势", "劣势", "机会", "挑战"],
                "match_all": True, # 要求所有关键词都出现
                "system_prompt": "你是一个专业的商业分析师。请根据上下文，以JSON格式返回分析结果，不要包含任何解释性文字。",
                "prompt_template": """
请根据以下背景信息：
---
{context}
---
分析问题："{question}"。
请严格按照以下JSON格式返回，如果某一项没有信息，请返回空列表[]:
{{
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["劣势1", "劣势2"],
  "opportunities": ["机会1", "机会2"],
  "challenges": ["挑战1", "挑战2"]
}}
"""
            }
            # 未来可以添加更多意图，例如： "FINANCIAL_SUMMARY": { ... }
        }
        
        # 定义默认意图的配置
        self.default_intent = {
            "system_prompt": "你是一个专业的、有问必答的AI投资顾问，请根据下面提供的上下文来回答用户问题。",
            "prompt_template": PROMPT_TEMPLATE
        }

    def recognize(self, query: str) -> dict:
        """
        识别用户问题的意图。

        :param query: 用户问题字符串。
        :return: 一个包含'system_prompt'和'prompt_template'的字典。
        """
        query_lower = query.lower()
        
        for intent_name, config in self.intents.items():
            keywords = config["keywords"]
            # 检查是需要匹配所有关键词还是任意一个
            match_condition = all if config.get("match_all", False) else any
            
            if match_condition(keyword in query_lower for keyword in keywords):
                print(f"识别到意图: {intent_name}，切换到JSON输出模式。")
                return {
                    "system_prompt": config["system_prompt"],
                    "prompt_template": config["prompt_template"]
                }

        # 如果没有匹配到任何特定意图，则返回默认配置
        print("未识别到特定意图，使用默认模式。")
        return self.default_intent

if __name__ == '__main__':
    # 测试意图识别器
    recognizer = IntentRecognizer()

    # 测试默认意图
    query1 = "中芯国际的营收情况怎么样？"
    intent1 = recognizer.recognize(query1)
    print(f"\n问题: {query1}")
    print(f"系统指令: {intent1['system_prompt']}")
    print("-" * 20)

    # 测试SWOT分析意图
    query2 = "请帮我分析一下中芯国际的优势、劣势、机会和挑战。"
    intent2 = recognizer.recognize(query2)
    print(f"\n问题: {query2}")
    print(f"系统指令: {intent2['system_prompt']}")
    print("-" * 20) 