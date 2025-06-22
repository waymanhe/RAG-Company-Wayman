import os
import sys
import json
from typing import Dict

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.knowledge_base_manager import KnowledgeBaseManager
from core.llm_service import QwenLLM
from config import PROMPT_TEMPLATE

class QAService:
    def __init__(self):
        """
        初始化问答服务, 加载所需的组件。
        """
        print("正在初始化问答服务...")
        self.llm = QwenLLM()
        self.kb_manager = KnowledgeBaseManager()
        self.db = self.kb_manager.load_db()
        print("问答服务初始化完成。")

    def search_documents(self, query: str, top_k: int, rerank_top_n: int) -> list:
        """
        仅执行文档检索和重排步骤。

        :param query: 用户提出的问题。
        :param top_k: 向量检索时召回的文档数量。
        :param rerank_top_n: Reranker模型筛选出的最相关文档数量。
        :return: 一个包含文档内容和元数据的字典列表。
        """
        print(f"步骤1: 正在从向量数据库中检索 {top_k} 个相关文档...")
        retrieved_docs = self.db.similarity_search_with_score(query, k=top_k)
        
        if not retrieved_docs:
            print("警告: 向量检索未找到任何相关文档。")
            return []
        
        print(f"检索完成，共找到 {len(retrieved_docs)} 个文档。")

        if rerank_top_n > 0:
            print(f"步骤2: Rerank模型正在对召回的文档进行重排 (取前{rerank_top_n}个)...")
            reranked_docs_content = self.llm.get_rerank_documents(query, [doc.page_content for doc, score in retrieved_docs], top_n=rerank_top_n)
            
            # Rerank后只返回了文本内容，我们需要找到原始文档以保留元数据
            final_docs = []
            if reranked_docs_content:
                for content in reranked_docs_content:
                    original_doc_tuple = next(((doc, score) for doc, score in retrieved_docs if doc.page_content == content), None)
                    if original_doc_tuple:
                        original_doc, score = original_doc_tuple
                        final_docs.append({
                            "page_content": original_doc.page_content,
                            "metadata": {**original_doc.metadata, 'score': score}
                        })
            
            if not final_docs: # Fallback if rerank fails
                print("警告: Rerank后没有返回任何文档或无法匹配原始文档，将使用原始检索结果。")
                final_docs = [{"page_content": doc.page_content, "metadata": {**doc.metadata, 'score': score}} for doc, score in retrieved_docs]

        else:
            print("步骤2: 已跳过Rerank。")
            final_docs = [{"page_content": doc.page_content, "metadata": {**doc.metadata, 'score': score}} for doc, score in retrieved_docs]
        
        print("文档检索与重排完成。")
        return final_docs

    def generate_answer(self, query: str, documents: list) -> Dict:
        """
        根据提供的文档生成最终答案和思考过程。

        :param query: 用户提出的问题。
        :param documents: 用于生成答案的上下文文档列表 (字典格式)。
        :return: LLM生成的包含思考过程的结构化JSON对象。
        """
        print("步骤3: 正在构建最终的Prompt...")
        
        doc_contents = [doc["page_content"] for doc in documents]
        
        context = "\n\n---\n\n".join(doc_contents)
        final_prompt = PROMPT_TEMPLATE.format(question=query, context=context)

        print("步骤4: 正在请求大语言模型生成最终答案...")
        raw_response = self.llm.get_chat_completion(prompt=final_prompt, system_prompt="")
        print("答案生成完毕。")
        
        # 增强调试：打印LLM返回的原始字符串
        print("--- LLM 原始返回 ---")
        print(raw_response)
        print("--------------------")
        
        # 解析LLM返回的JSON字符串
        try:
            json_str = raw_response.strip().removeprefix("```json").removesuffix("```")
            
            # 增强清洗逻辑：同时处理qwen-turbo可能生成的`\%`和`\\%`两种非法转义
            cleaned_json_str = json_str.replace('\\\\%', '%').replace('\\%', '%')
            
            parsed_response = json.loads(cleaned_json_str)
            parsed_response['raw_context'] = documents
            return parsed_response
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"错误: 解析LLM返回的JSON失败 - {e}")
            # 返回一个错误结构，以便前端可以优雅地处理
            return {
                "reasoning_steps": ["无法解析模型的响应。"],
                "reasoning_summary": "模型返回的格式不正确，请稍后重试。",
                "relevant_context": raw_response, # 返回原始响应以便调试
                "final_answer": "抱歉，处理您的请求时发生错误。",
                "raw_context": documents
            }

    def ask(self, query: str, top_k: int = 5, rerank_top_n: int = 3) -> Dict:
        """
        接收问题, 执行完整的RAG流程, 并返回结构化的答案。
        """
        print(f"\n--- 接收到问题: {query} ---")
        final_docs = self.search_documents(query, top_k, rerank_top_n)
        
        if not final_docs:
            return {
                "reasoning_steps": [],
                "reasoning_summary": "未能找到相关文档。",
                "relevant_context": "",
                "final_answer": "抱歉，我在知识库中没有找到与您问题相关的信息。",
                "raw_context": []
            }
        
        answer = self.generate_answer(query, final_docs)
        return answer

def run_batch_mode(qa_service: QAService):
    """
    运行批量问答模式。
    """
    print("\n--- 启动批量问答模式 ---")
    questions_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_data", "questions.json")
    answers_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_data", "answers.json")

    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
    except FileNotFoundError:
        print(f"错误: 问题文件未找到于 {questions_path}")
        return
    except json.JSONDecodeError:
        print(f"错误: 问题文件 {questions_path} 格式不正确。")
        return

    results = []
    total_questions = len(questions)
    print(f"共找到 {total_questions} 个问题，开始逐一处理...")

    for i, item in enumerate(questions):
        question_text = item.get("text")
        if not question_text:
            continue
        
        print(f"\n--- 正在处理问题 {i+1}/{total_questions} ---")
        answer = qa_service.ask(question_text)
        results.append(answer)

    with open(answers_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"\n--- ✅ 批量问答完成！结果已保存到 {answers_path} ---")


def run_interactive_mode(qa_service: QAService):
    """
    运行交互式问答模式。
    """
    while True:
        question = input("\n您好，我是您的AI投资顾问，请输入您的问题 (输入 '退出' 结束): ")
        if question.lower() == '退出':
            print("感谢您的使用，再见！")
            break
        
        answer = qa_service.ask(question)
        print("\n" + "="*50)
        print(f"答案: {answer['final_answer']}")
        print(f"思考过程: {', '.join(answer['reasoning_steps'])}")
        print(f"相关上下文: {answer['relevant_context']}")


if __name__ == '__main__':
    # --- 模式选择 ---
    # "interactive": 手动交互式提问
    # "batch": 自动处理 'stock_data/questions.json' 文件
    MODE = "batch" 
    # -----------------

    # 初始化服务
    qa_service = QAService()

    if MODE == "interactive":
        run_interactive_mode(qa_service)
    elif MODE == "batch":
        run_batch_mode(qa_service)
    else:
        print(f"错误: 未知的运行模式 '{MODE}'。请选择 'interactive' 或 'batch'。") 