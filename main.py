# -*- coding: utf-8 -*-
"""
@author: wayman
@contact: 8236278419@qq.com
@file: main.py
@desc: RAG应用的主入口，使用FastAPI提供Web服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager

# 导入我们的核心服务
from core.qa_service import QAService

# --- 数据模型定义 ---
class AskRequest(BaseModel):
    query: str
    top_k: int = 20
    rerank_top_n: int = 5

# --- 应用生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时执行
    print("应用启动... 正在初始化QA服务...")
    app.state.qa_service = QAService()
    print("QA服务初始化完成。")
    
    yield
    
    # 应用关闭时执行 (如果需要)
    print("应用关闭。")


# --- FastAPI应用初始化 ---
app = FastAPI(
    title="RAG 企业知识库问答 API",
    description="一个基于RAG架构的、可与企业知识库进行问答的API服务。",
    version="1.0.0",
    lifespan=lifespan  # 使用新的lifespan参数
)

# --- 中间件配置 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API路由定义 ---
@app.get("/", summary="根路径")
async def root():
    return {"message": "欢迎使用RAG企业知识库问答API！服务运行正常。"}

@app.post("/api/ask", summary="执行完整的RAG问答流程")
async def ask_question(request: AskRequest):
    """
    接收用户问题，执行完整的检索、重排和生成流程，返回结构化的答案。
    """
    qa_service: QAService = app.state.qa_service
    # 注意：我们将在这里直接调用一个非流式的ask方法
    result = qa_service.ask(
        query=request.query, 
        top_k=request.top_k, 
        rerank_top_n=request.rerank_top_n
    )
    return result

# --- 启动服务 ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 