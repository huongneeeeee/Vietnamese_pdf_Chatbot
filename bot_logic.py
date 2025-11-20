from RAG_chatbot import rag_bot 
from pdf_processor import ContextRetriever
from text_processor import TextProcessor
from operator import itemgetter

# Khởi tạo các đối tượng này một lần (Global variables module-level)
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
            return "Vui lòng tải lên hoặc chọn ít nhất một tài liệu để truy vấn.", ""

        # --- BƯỚC 2: TÌM KIẾM (RETRIEVAL) ---
        results = []
        
        # --- SỬA LẠI: Nới lỏng ngưỡng lọc (Tăng từ 0.8 lên 1.5 hoặc cao hơn) ---
        # Với L2 Distance: Càng thấp càng giống. 
        # 0.0 là giống hệt. > 1.0 là bắt đầu khác biệt nhiều.
        SIMILARITY_THRESHOLD = 1.6  

        for db_name, db in target_dbs.items():
            # Lấy nhiều đoạn hơn (k=4) để có nhiều thông tin hơn cho việc tóm tắt
            docs_scores = db.similarity_search_with_score(user_question, k=3)
            
            for doc, score in docs_scores:
                # In ra để debug xem điểm số thực tế là bao nhiêu
                print(f"Source: {db_name} - Score: {score}") 
                
                if score < SIMILARITY_THRESHOLD: 
                    results.extend([(doc, score, db_name)])

        if not results:
            # Fallback: Nếu không tìm thấy đoạn nào khớp ID, thử lấy đại 3 đoạn đầu tiên nếu câu hỏi chứa từ "tóm tắt"
            # Đây là mẹo để xử lý câu hỏi "Tóm tắt"
            keywords = ["tóm tắt", "summary", "nội dung chính", "tổng quan"]
            if any(k in user_question.lower() for k in keywords):
                # Lấy đại diện từ DB đầu tiên
                first_db = next(iter(target_dbs.values()))
                docs_scores = first_db.similarity_search_with_score("giới thiệu", k=3) # Tìm đoạn giới thiệu
                results.extend([(doc, 0.0, "Fallback") for doc, score in docs_scores])
            else:
                 return "Tôi không tìm thấy thông tin nào đủ liên quan (điểm tương đồng thấp) để trả lời.", ""

        # Lấy 3 đoạn tốt nhất
        top_docs = sorted(results, key=itemgetter(1))[:3]

        metadatas = []
        expanded_contexts = []

        for doc, score, db_name in top_docs:
            file_name = retriever.get_file_name(doc.metadata)
            doc.metadata['source_db'] = db_name
            metadatas.append(doc.metadata) 

            file_name_remove_accents = text_processor.remove_accents(file_name)
            expanded_context = retriever.expand_context(file_name_remove_accents, doc.page_content)
            expanded_contexts.append(expanded_context)

        context_str = "\n SEPARATED \n".join(expanded_contexts)

        # --- BƯỚC 3: GỌI GEMINI/LLM ---
        response = rag_bot.response(
            user_question=user_question,
            chat_history=chat_history_str,
            context_data=context_str
        ).strip()

        # --- BƯỚC 4: XỬ LÝ NGUỒN ---
        sources_list = []
        for meta in metadatas:
            file_name = meta.get('source_db', 'Unknown File')
            page_number = meta.get('page') 
            if page_number is not None:
                sources_list.append(f"{file_name} (Trang {int(page_number) + 1})")
            else:
                sources_list.append(f"{file_name}")
        
        unique_sources = list(set(sources_list))
        response_with_sources = f"**Nguồn tham khảo:** {', '.join(unique_sources)}\n\n{response}"

        return response_with_sources, context_str
    
    