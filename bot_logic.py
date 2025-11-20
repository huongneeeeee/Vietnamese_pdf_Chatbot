import json
import os
from datetime import datetime
from RAG_chatbot import rag_bot 
from document_processor import ContextRetriever 
from text_processor import TextProcessor
from operator import itemgetter

retriever = ContextRetriever("original_text")
text_processor = TextProcessor()
HISTORY_FILE = "chat_history_log.json"

def save_history(user_q, bot_a, sources):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": user_q,
        "answer": bot_a,
        "sources": sources
    }
    data = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except: pass
    data.append(entry)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class chatBotMode:
    def __init__(self, vector_dbs: dict = None):
        self.vector_dbs = vector_dbs if vector_dbs is not None else {}
        # [MỚI] Bộ nhớ đệm lưu context của câu hỏi trước
        self.last_context = None
        self.last_sources = []

    def process_question(self, user_question: str, selected_files: list = None, chat_history_str: str = ""):
        """
        Xử lý câu hỏi:
        - Nếu là câu hỏi chỉnh sửa (sai, dịch, làm lại...) -> Dùng lại Context cũ.
        - Nếu là câu hỏi mới -> Tìm kiếm Context mới.
        """
        
        # 1. Kiểm tra ý định "Chỉnh sửa / Refinement"
        refinement_keywords = [
            "trả lời lại", "làm lại", "viết lại",
            "không đúng", "sai rồi", "chưa đúng", "nhầm rồi",
            "tiếng việt", "vietnamese", "tiếng anh", "english", "dịch",
            "answer again", "incorrect", "wrong", "translate"
        ]
        
        is_refinement = any(k in user_question.lower() for k in refinement_keywords)
        
        context_str = ""
        sources_details = []

        # 2. Quyết định luồng xử lý (Tìm mới hay Dùng lại)
        if is_refinement and self.last_context:
            print(f"🔄 Phát hiện yêu cầu chỉnh sửa: '{user_question}'. Tái sử dụng Context cũ.")
            context_str = self.last_context
            sources_details = self.last_sources
        else:
            # --- LUỒNG TÌM KIẾM MỚI (Retrieval) ---
            
            # Lọc DB
            if not selected_files:
                target_dbs = self.vector_dbs
            else:
                target_dbs = {name: db for name, db in self.vector_dbs.items() if name in selected_files}

            if not target_dbs:
                # Nếu đang hỏi chỉnh sửa mà chưa có context cũ, và cũng không chọn file -> Lỗi
                return {"response": "Vui lòng chọn tài liệu để bắt đầu.", "sources": []}

            # Tìm kiếm Vector
            results = []
            for db_name, db in target_dbs.items():
                # Tìm k=3 đoạn giống nhất
                docs_scores = db.similarity_search_with_score(user_question, k=3)
                results.extend([(doc, score, db_name) for doc, score in docs_scores])

            if not results:
                 # Nếu không tìm thấy gì, thử trả lời bằng kiến thức rỗng (để Prompt xử lý Not Found)
                 pass 
            else:
                # Lấy top 4 đoạn tốt nhất từ tất cả các file
                top_docs = sorted(results, key=itemgetter(1))[:4]

                context_parts = []
                
                for doc, score, db_name in top_docs:
                    file_clean = retriever.get_file_name(doc.metadata)
                    
                    # Mở rộng ngữ cảnh
                    expanded_text = retriever.expand_context(file_clean, doc.page_content)
                    context_parts.append(expanded_text)

                    # Lưu thông tin nguồn
                    page = doc.metadata.get('page', 0)
                    sources_details.append({
                        "file": db_name,
                        "page": int(page) + 1 if page is not None else 1,
                        "content_snippet": doc.page_content 
                    })

                context_str = "\n SEPARATED \n".join(context_parts)
                
                # [QUAN TRỌNG] Lưu lại Context và Sources vào bộ nhớ đệm
                self.last_context = context_str
                self.last_sources = sources_details

        # 3. Gọi AI trả lời (Generation)
        response_text = rag_bot.response(user_question, chat_history_str, context_str)

        # 4. Lưu Log
        save_history(user_question, response_text, [s['file'] for s in sources_details])

        # 5. Trả về kết quả
        return {
            "response": response_text,
            "context_used": context_str,
            "sources": sources_details
        }