# -*- coding: utf-8 -*-
"""
@author: hmd
@license: (C) Copyright 2021-2027, JMD.
@contact: 931725379@qq.com
@software: 
@file: llm_service.py
@time: 2024/7/28 17:05
@desc: 封装与通义千问大模型相关的API调用
"""
import os
import sys

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dashscope
from http import HTTPStatus
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from config import DASHSCOPE_API_KEY, RERANK_MODEL_NAME, EMBEDDING_MODEL_NAME, GENERATION_MODEL_NAME

class QwenLLM:
    def __init__(self, api_key=DASHSCOPE_API_KEY):
        """
        初始化QwenLLM服务。
        """
        if api_key:
            dashscope.api_key = api_key
        else:
            raise ValueError("通义千问API Key未设置, 请在config.py中配置")

    def get_rerank_documents(self, query: str, documents: list[str], top_n: int = 3) -> list[str]:
        """
        使用通义千问的rerank API对文档列表进行重排。
        现在将实际调用API，而不是禁用它。
        """
        if not documents:
            return []
            
        try:
            # 使用在config.py中定义的RERANK_MODEL_NAME
            resp = dashscope.TextReRank.call(
                model=RERANK_MODEL_NAME,
                query=query,
                documents=documents,
                top_n=top_n
            )
            
            # 调试日志：打印API原始返回
            # print(f"--- Rerank API Response ---\n{resp}\n--------------------------")

            if resp.status_code == HTTPStatus.OK:
                # 最终解决方案：利用返回的index直接从原始documents列表中重构排序后的列表
                reranked_indices = [item.index for item in resp.output.results]
                reranked_docs = [documents[i] for i in reranked_indices]
                return reranked_docs
            else:
                print(f"错误: 调用Rerank API失败: {resp.code} - {resp.message}")
                # 在API失败时，返回原始文档的前 top_n 个作为备用
                return documents[:top_n]
        except Exception as e:
            print(f"调用Rerank API时发生异常: {e}")
            # 在发生异常时，也返回原始文档的前 top_n 个作为备用
            return documents[:top_n]

    def get_text_embedding(self, text: str):
        """
        获取单个文本的embedding向量。

        :param text: 输入文本
        :return: 文本的embedding向量，或在失败时返回None
        """
        try:
            resp = dashscope.TextEmbedding.call(
                model=EMBEDDING_MODEL_NAME,
                input=text
            )
            if resp.status_code == HTTPStatus.OK:
                # 返回第一个embedding结果
                return resp.output['embeddings'][0]['embedding']
            else:
                print(f"通义千问Embedding API调用失败: {resp.code} - {resp.message}")
                return None
        except Exception as e:
            print(f"调用Embedding API时发生异常: {e}")
            return None

    @retry(
        wait=wait_exponential(min=1, max=10),  # 等待时间指数增长，1s到10s
        stop=stop_after_attempt(3),  # 最多重试3次
        retry=retry_if_exception_type(Exception)  # 任何Exception都重试
    )
    def get_text_embeddings_batch(self, texts: list[str]) -> list[list[float]] | None:
        """
        获取批量文本的embedding向量。增加了重试机制。

        :param texts: 输入文本列表
        :return: 文本的embedding向量列表，或在失败时返回None
        """
        try:
            resp = dashscope.TextEmbedding.call(
                model=EMBEDDING_MODEL_NAME,
                input=texts
            )
            if resp.status_code == HTTPStatus.OK:
                # 提取所有embedding向量
                embeddings = [record['embedding'] for record in resp.output['embeddings']]
                return embeddings
            else:
                print(f"通义千问Embedding API批量调用失败: {resp.code} - {resp.message}")
                return None
        except Exception as e:
            print(f"调用Embedding API批量接口时发生异常: {e}")
            raise  # 重新抛出异常以触发tenacity的重试

    def get_chat_completion(self, prompt: str, system_prompt: str = "You are a helpful assistant."):
        """
        获取大模型的文本生成结果。

        :param prompt: 用户输入或组合后的prompt
        :param system_prompt: 系统级指令
        :return: 模型生成的文本内容，或在失败时返回空字符串
        """
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ]
        try:
            response = dashscope.Generation.call(
                model=GENERATION_MODEL_NAME,
                messages=messages,
                result_format='message',  # 设置返回格式为message
            )

            if response.status_code == HTTPStatus.OK:
                return response.output.choices[0].message.content
            else:
                print(f"通义千问Generation API调用失败: {response.code} - {response.message}")
                return ""
        except Exception as e:
            print(f"调用Generation API时发生异常: {e}")
            return ""

if __name__ == '__main__':
    # 简单测试
    llm = QwenLLM()

    # 测试Rerank
    print("--- 测试Rerank功能 ---")
    query_rerank = "全球最大的电商公司是哪家？"
    docs_rerank = [
        "阿里巴巴集团控股有限公司，简称阿里巴巴集团，是一家中国的跨国科技公司，专注于电子商务、零售、互联网和技术。",
        "亚马逊公司是一家位于美国西雅图的跨国电子商务企业。",
        "京东是中国一家自营式综合网络零售商。",
        "拼多多是中国大陆一家主打C2M模式的第三方社交电商平台。"
    ]
    reranked = llm.get_rerank_documents(query_rerank, docs_rerank, top_n=2)
    print(f"查询: {query_rerank}")
    print(f"重排后的文档: {reranked}")
    print("-" * 20)

    # 测试Embedding
    print("\n--- 测试Embedding功能 ---")
    text_to_embed = "你好，世界"
    embedding = llm.get_text_embedding(text_to_embed)
    if embedding:
        print(f"'{text_to_embed}' 的向量 (前5维): {embedding[:5]}...")
        print(f"向量维度: {len(embedding)}")
    print("-" * 20)

    # 测试Chat Completion
    print("\n--- 测试Chat Completion功能 ---")
    prompt_chat = "请介绍一下杭州"
    chat_response = llm.get_chat_completion(prompt_chat)
    print(f"查询: {prompt_chat}")
    print(f"回答: {chat_response}")
    print("-" * 20) 