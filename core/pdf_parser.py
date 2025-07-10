# -*- coding: utf-8 -*-
"""
@author: wayman
@contact: 8236278419@qq.com
@file: pdf_parser.py
@desc: 使用 minerU API 解析PDF文件 (最终生产版本 - 使用 requests)
"""
import os
import sys
import time
import json
import requests
import hashlib
import io
import zipfile

# 将项目根目录添加到Python的模块搜索路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PDF_REPORTS_DIR, MINERU_API_KEY, PROCESSED_REPORTS_DIR

# API端点
BASE_URL = 'https://mineru.net/api/v4'
BATCH_URLS_URL = f'{BASE_URL}/file-urls/batch'
# 使用新的批量结果获取端点
BATCH_RESULT_URL_TEMPLATE = f'{BASE_URL}/extract-results/batch/{{}}'
# 不再需要单独创建任务和轮询单个任务
# TASK_URL = f'{BASE_URL}/extract/task'
# RESULT_URL_TEMPLATE = f'{BASE_URL}/extract/task/{{}}'

def _download_and_extract_zip(zip_url: str) -> dict:
    """从给定的URL下载ZIP文件，在内存中解压，并返回解析后的JSON内容。"""
    try:
        print(f" -> 正在下载并解压结果: {zip_url}")
        response = requests.get(zip_url, verify=False)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            # 假设压缩包里有且仅有一个我们需要的json文件
            json_filename = next((name for name in zip_file.namelist() if name.endswith('.json')), None)
            if not json_filename:
                print(" -> 错误: 在ZIP文件中没有找到 .json 文件。")
                return None
            
            with zip_file.open(json_filename) as json_file:
                content = json_file.read()
                return json.loads(content)

    except requests.exceptions.RequestException as e:
        print(f" -> 下载ZIP文件时出错: {e}")
    except zipfile.BadZipFile:
        print(" -> 下载的文件不是一个有效的ZIP文件。")
    except Exception as e:
        print(f" -> 处理ZIP文件时发生未知错误: {e}")
    return None

def _get_batch_result(batch_id: str, headers: dict, num_files: int):
    """
    使用requests轮询并获取批量任务的结果。
    当所有文件的状态都为 'done' 或包含错误信息时，返回结果。
    """
    result_url = BATCH_RESULT_URL_TEMPLATE.format(batch_id)
    max_wait_time = 600  # 延长到10分钟以处理大文件
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(result_url, headers=headers, verify=False)
            response.raise_for_status() 
            response_data = response.json()
            
            task_info = response_data.get('data', {})
            results_list = task_info.get('extract_result', [])

            # 检查是否所有任务都已完成（成功或失败）
            if len(results_list) == num_files:
                all_finished = all(
                    item.get('state') == 'done' or item.get('err_msg')
                    for item in results_list
                )
                if all_finished:
                    print("批量任务处理完成。")
                    return results_list
            
            # 提供更详细的进度信息
            finished_count = sum(1 for item in results_list if item.get('state') == 'done' or item.get('err_msg'))
            print(f"批量任务 {batch_id} 仍在处理中 ({finished_count}/{num_files} 完成), 15秒后重试...")
            time.sleep(15)

        except requests.exceptions.RequestException as e:
            print(f"查询批量任务 {batch_id} 结果时出错: {e}")
            time.sleep(15)
    print(f"批量任务 {batch_id} 等待超时。")
    return None

def save_json_result(filename: str, data: dict):
    """将解析结果保存为JSON文件"""
    if not os.path.exists(PROCESSED_REPORTS_DIR):
        os.makedirs(PROCESSED_REPORTS_DIR)
    
    base_name = os.path.splitext(filename)[0]
    json_path = os.path.join(PROCESSED_REPORTS_DIR, f"{base_name}.json")
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f" -> 结果已保存到: {json_path}")

def parse_pdf_documents_requests(pdf_directory: str = PDF_REPORTS_DIR):
    """
    使用 requests 库和 minerU 的批量流程，解析指定目录下的所有PDF文件。
    新流程：1. 批量申请URL -> 2. 上传文件 -> 3. 批量获取结果
    """
    pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"在目录 '{pdf_directory}' 中没有找到PDF文件。")
        return

    print(f"准备使用 minerU API (批量流程) 解析以下 {len(pdf_files)} 个PDF文件...")

    headers = {
        "Authorization": f"Bearer {MINERU_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # --- 步骤 1/3: 批量申请文件上传地址 ---
        print("\n--- 步骤 1/3: 批量申请文件上传地址 ---")
        
        # 创建一个从 data_id (hash) 到原始文件名的映射
        data_id_map = {}
        files_to_request = []
        for fname in pdf_files:
            # 使用文件名的MD5哈希作为唯一且简短的 data_id
            hasher = hashlib.md5()
            hasher.update(fname.encode('utf-8'))
            data_id = hasher.hexdigest()
            data_id_map[data_id] = fname
            files_to_request.append({"name": fname, "is_ocr": True, "data_id": data_id})

        batch_payload = {
            "files": files_to_request,
            "enable_table": True,
            "enable_formula": True,
            "model_version": "v2"
        }
        
        response = requests.post(BATCH_URLS_URL, headers=headers, json=batch_payload, verify=False)
        response.raise_for_status()
        batch_response_data = response.json()

        if batch_response_data.get("code") != 0:
            print(f"申请上传地址失败: {batch_response_data.get('msg')}")
            return
        
        response_data_field = batch_response_data.get('data', {})
        upload_urls_info = response_data_field.get('file_urls', [])
        batch_id = response_data_field.get('batch_id')

        if not batch_id or len(upload_urls_info) != len(pdf_files):
            print("错误：返回的数据不完整（batch_id 或 URL数量不匹配）。")
            return
            
        print(f"成功获取 {len(upload_urls_info)} 个文件的上传地址, Batch ID: {batch_id}")

        # --- 步骤 2/3: 上传所有文件 ---
        print("\n--- 步骤 2/3: 开始上传所有文件 ---")
        upload_map = {} # 这个map现在可以不创建，但保留以防万一
        for i, (filename, url_info) in enumerate(zip(pdf_files, upload_urls_info)):
            filepath = os.path.join(pdf_directory, filename)
            print(f"正在上传: {filename}...")
            
            # 将文件读入内存再上传，以确保使用 Content-Length
            with open(filepath, 'rb') as f:
                file_content = f.read()
                upload_response = requests.put(url_info, data=file_content, verify=False)
                upload_response.raise_for_status()
            upload_map[filename] = url_info # 保留赋值

        print("所有文件上传成功。")
        
        # --- 步骤 3/3: 轮询获取所有任务的结果 ---
        print(f"\n--- 步骤 3/3: 获取批量任务 (Batch ID: {batch_id}) 的解析结果 ---")
        results = _get_batch_result(batch_id, {"Authorization": headers["Authorization"]}, len(pdf_files))
        
        successful_files = 0
        if results is not None:
            for res_item in results:
                data_id = res_item.get("data_id")
                filename = data_id_map.get(data_id)
                
                if filename:
                    error_message = res_item.get("err_msg")
                    if error_message:
                        print(f" -> 文件 '{filename}' 解析失败: {error_message}")
                    elif res_item.get("state") == "done":
                        zip_url = res_item.get("full_zip_url")
                        if zip_url:
                            result_data = _download_and_extract_zip(zip_url)
                            if result_data:
                                save_json_result(filename, result_data)
                                successful_files += 1
                            else:
                                print(f" -> 未能从ZIP文件中提取 '{filename}' 的结果。")
                        else:
                            print(f" -> 文件 '{filename}' 状态为 'done' 但缺少 'full_zip_url'。")
                    else:
                        print(f" -> 文件 '{filename}' 处于未知状态: {res_item.get('state')}")
                else:
                    print(f"警告：收到一个无法识别的data_id的结果: {data_id}")
        else:
            print("未能获取任何批量解析结果。")
        
        if successful_files == len(pdf_files):
            print(f"\n--- ✅ 所有 {successful_files} 个文件均已成功解析并保存 ---")
        else:
            print(f"\n--- ⚠️ 完成，但有 {len(pdf_files) - successful_files} 个文件解析失败 ---")

    except requests.exceptions.RequestException as e:
        print(f"\n在处理过程中发生网络错误: {e}")
    except Exception as e:
        print(f"\n在处理过程中发生未知错误: {e}")


if __name__ == '__main__':
    if not any(f.endswith(".pdf") for f in os.listdir(PDF_REPORTS_DIR)):
        print(f"'{PDF_REPORTS_DIR}' 目录为空，请先放置PDF文件。")
    else:
        parse_pdf_documents_requests() 