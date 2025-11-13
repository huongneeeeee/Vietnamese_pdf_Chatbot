from RAG_chatbot import rag_bot 
from pdf_processor import ContextRetriever
from text_processor import TextProcessor
from operator import itemgetter

# Khởi tạo các đối tượng này một lần (Global variables module-level)
retriever = ContextRetriever("original_text")
text_processor = TextProcessor()

class chatBotMode:
    def __init__(self, vector_dbs: dict = None):
        """
        Khởi tạo bot với một dictionary chứa các vector DBs.
        vector_dbs: { "ten_file.pdf": FAISS_DB_OBJECT, ... }
        """
        self.vector_dbs = vector_dbs if vector_dbs is not None else {}

    def process_question(self, user_question: str, selected_pdfs: list = None, chat_history_str: str = ""):
        """
        Hàm thực hiện RAG.
        
        Args:
            user_question: Câu hỏi người dùng.
            selected_pdfs: Danh sách tên file PDF muốn hỏi (VD: ['file1.pdf']). Nếu None, hỏi tất cả.
            chat_history_str: Chuỗi lịch sử chat đã được format (User: ... \n Bot: ...).
            
        Returns:
            response_with_sources (str): Câu trả lời kèm nguồn.
            context_str (str): Nội dung context tìm được (để hiển thị nếu cần).
        """
        
        # --- BƯỚC 1: LỌC VECTOR DB ---
        # Nếu không chỉ định file nào, mặc định dùng tất cả file hiện có trong DB
        if not selected_pdfs:
            target_dbs = self.vector_dbs
        else:
            target_dbs = {name: db for name, db in self.vector_dbs.items() 
                          if name in selected_pdfs}

        if not target_dbs:
            return "Vui lòng tải lên hoặc chọn ít nhất một tài liệu PDF để truy vấn.", ""

        # --- BƯỚC 2: TÌM KIẾM (RETRIEVAL) ---
        results = []
        for db_name, db in target_dbs.items():
            # Tìm kiếm 2 đoạn giống nhất từ mỗi file
            docs_scores = db.similarity_search_with_score(user_question, k=2)
            results.extend([(doc, score, db_name) for doc, score in docs_scores])

        if not results:
             return "Tôi không tìm thấy thông tin nào liên quan trong tài liệu đã chọn.", ""

        # Lấy 2 đoạn tốt nhất từ TẤT CẢ các file gộp lại
        top_docs = sorted(results, key=itemgetter(1))[:2]

        metadatas = []
        expanded_contexts = []

        for doc, score, db_name in top_docs:
            # Lấy tên file gốc từ metadata
            file_name = retriever.get_file_name(doc.metadata)
            
            # Ghi đè source_db để đảm bảo chính xác
            doc.metadata['source_db'] = db_name
            metadatas.append(doc.metadata) 

            # Mở rộng context (nếu cần thiết theo logic cũ của bạn)
            file_name_remove_accents = text_processor.remove_accents(file_name)
            expanded_context = retriever.expand_context(file_name_remove_accents, doc.page_content)
            expanded_contexts.append(expanded_context)

        context_str = "\n SEPARATED \n".join(expanded_contexts)

        # --- BƯỚC 3: GỌI GEMINI/LLM ---
        # Gọi hàm response từ rag_bot (đã sửa ở bước trước)
        response = rag_bot.response(
            user_question=user_question,
            chat_history=chat_history_str,
            context_data=context_str
        ).strip()

        # --- BƯỚC 4: XỬ LÝ NGUỒN & SỐ TRANG ---
        sources_list = []
        for meta in metadatas:
            file_name = meta.get('source_db', 'Unknown File')
            
            # Lấy số trang (LangChain thường đánh index từ 0, nên cộng 1)
            page_number = meta.get('page') 

            if page_number is not None:
                # Chuyển sang int rồi cộng 1
                sources_list.append(f"{file_name} (Trang {int(page_number) + 1})")
            else:
                sources_list.append(f"{file_name}")
        
        # Loại bỏ nguồn trùng lặp
        unique_sources = list(set(sources_list))
        
        # Format kết quả cuối cùng
        response_with_sources = f"**Nguồn tham khảo:** {', '.join(unique_sources)}\n\n{response}"

        return response_with_sources, context_str