from RAG_chatbot import rag_bot 
# Import từ pdf_processor (đúng theo tên file bạn đang dùng)
from pdf_processor import ContextRetriever 
from text_processor import TextProcessor
from operator import itemgetter

retriever = ContextRetriever("original_text")
text_processor = TextProcessor()

class chatBotMode:
    def __init__(self, vector_dbs: dict = None):
        self.vector_dbs = vector_dbs if vector_dbs is not None else {}

    def process_question(self, user_question: str, selected_pdfs: list = None, chat_history_str: str = ""):
        
        # --- BƯỚC 1: LỌC VECTOR DB ---
        if not selected_pdfs:
            target_dbs = self.vector_dbs
        else:
            target_dbs = {name: db for name, db in self.vector_dbs.items() 
                          if name in selected_pdfs}

        if not target_dbs:
            # [FIX] Thêm "context": "" để tránh KeyError
            return {"response": "Vui lòng tải lên hoặc chọn ít nhất một tài liệu để truy vấn.", "sources": [], "context": ""}

        # --- BƯỚC 2: TỐI ƯU CÂU HỎI (QUAN TRỌNG CHO CÂU HỎI NGẮN) ---
        search_query = user_question
        
        # Nếu câu hỏi quá ngắn (dưới 20 ký tự) và chứa từ khóa tóm tắt
        # Ta thay thế bằng câu query đầy đủ để tìm kiếm hiệu quả hơn
        if len(user_question.strip()) < 20:
            keywords = ["tóm tắt", "summary", "chính", "nội dung", "ý chính", "overview"]
            if any(k in user_question.lower() for k in keywords):
                search_query = "Tổng hợp nội dung chính, các ý quan trọng nhất và kết luận của tài liệu."
                print(f"🔄 Đã tối ưu câu hỏi ngắn: '{user_question}' -> '{search_query}'")
        
        print(f"🔎 Tìm kiếm với từ khóa: '{search_query}'")

        # --- BƯỚC 3: TÌM KIẾM (RETRIEVAL) ---
        results = []
        # Tăng ngưỡng tìm kiếm lên một chút để chấp nhận nhiều thông tin hơn cho việc tổng hợp
        SIMILARITY_THRESHOLD = 1.8  

        for db_name, db in target_dbs.items():
            # Tăng k lên 6 để lấy nhiều đoạn văn hơn từ nhiều file (phục vụ tổng hợp)
            docs_scores = db.similarity_search_with_score(search_query, k=6)
            for doc, score in docs_scores:
                if score < SIMILARITY_THRESHOLD: 
                    results.extend([(doc, score, db_name)])

        if not results:
             # Fallback: Nếu không tìm thấy gì nhưng người dùng muốn tóm tắt, 
             # thử lấy trang đầu tiên của file đầu tiên làm context (thường là giới thiệu)
             if "tóm tắt" in search_query.lower() or "nội dung" in search_query.lower():
                 first_db_name = next(iter(target_dbs))
                 first_db = target_dbs[first_db_name]
                 # Tìm kiếm rộng hơn
                 fallback_docs = first_db.similarity_search_with_score("giới thiệu", k=3)
                 results.extend([(doc, score, first_db_name) for doc, score in fallback_docs])
             
             if not results:
                return {"response": "Tôi không tìm thấy thông tin nào đủ liên quan trong file bạn upload để trả lời.", "sources": [], "context": ""}

        # Lấy top 6 đoạn tốt nhất (đã tăng từ 3 lên 6) để AI có đủ dữ liệu tổng hợp
        # Sắp xếp theo điểm số (score càng thấp càng giống)
        top_docs = sorted(results, key=itemgetter(1))[:6]

        metadatas = []
        expanded_contexts = []

        for doc, score, db_name in top_docs:
            file_name = retriever.get_file_name(doc.metadata)
            doc.metadata['source_db'] = db_name
            metadatas.append(doc.metadata) 

            file_name_remove_accents = text_processor.remove_accents(file_name)
            expanded_context = retriever.expand_context(file_name_remove_accents, doc.page_content)
            
            # Thêm tên file vào context để AI biết thông tin này đến từ đâu -> Giúp tổng hợp tốt hơn
            context_with_source = f"[Thông tin trích từ file: {db_name}]:\n{expanded_context}"
            expanded_contexts.append(context_with_source)

        context_str = "\n\n".join(expanded_contexts)

        # --- BƯỚC 4: GỌI AI ---
        response_text = rag_bot.response(
            user_question=user_question, # Gửi câu hỏi gốc của người dùng
            chat_history=chat_history_str,
            context_data=context_str
        ).strip()

        # --- BƯỚC 5: XỬ LÝ NGUỒN ---
        sources_list = []
        for meta in metadatas:
            file_name = meta.get('source_db', 'Unknown File')
            page_number = meta.get('page') 
            if page_number is not None:
                sources_list.append(f"{file_name} (Trang {int(page_number) + 1})")
            else:
                sources_list.append(f"{file_name}")
        
        unique_sources = list(set(sources_list))
        
        return {
            "response": response_text,
            "context": context_str,
            "sources": unique_sources
        }