import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI 

# --- 1. CẤU HÌNH MÔI TRƯỜNG & API KEY ---
# Load biến môi trường từ file .env
load_dotenv()

# [THAY ĐỔI] Lấy Key của Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Kiểm tra API Key 
if not GROQ_API_KEY:
    print("⚠️ CẢNH BÁO: Không tìm thấy GROQ_API_KEY trong file .env")

# [THAY ĐỔI] Tên mô hình của Groq
# Các model phổ biến của Groq:
# - "llama3-8b-8192" (Nhanh, nhẹ, tương đương model cũ của bạn)
# - "llama3-70b-8192" (Thông minh hơn, nhưng nặng hơn)
# - "mixtral-8x7b-32768" (Cửa sổ ngữ cảnh lớn)

MODEL_NAME = "llama-3.3-70b-versatile"
# --- 2. CẤU HÌNH MODEL ---
generation_config = {
  "temperature": 0.1, # Groq thường cần temp thấp để ổn định
  "max_tokens": 1000,
}

# --- 3. PROMPT TEMPLATE CHO RAG ---
# (Giữ nguyên Prompt tiếng Việt cưỡng chế mà chúng ta đã tối ưu)
custom_prompt_template = """
Bạn là một trợ lý RAG (Retrieval-Augmented Generation) thông minh. Nhiệm vụ của bạn là hỗ trợ người dùng dựa trên tài liệu được cung cấp.

QUY TẮC QUAN TRỌNG NHẤT (BẮT BUỘC TUÂN THỦ):
1. NGÔN NGỮ: Câu trả lời phải HOÀN TOÀN BẰNG TIẾNG VIỆT. Nếu tài liệu là tiếng Anh, hãy dịch ý hiểu và trả lời bằng tiếng Việt.
2. CHỈ dùng Context: Chỉ trả lời dựa trên thông tin trong Context. Không bịa đặt.
3. Xử lý khi không tìm thấy: Nếu không có thông tin trong Context, hãy trả lời: "Tôi không tìm thấy thông tin này trong tài liệu."

History: {history_global}

Context: {context}

Question: {question}
(Lưu ý: Hãy trả lời câu hỏi trên bằng tiếng Việt chi tiết và rõ ràng)

Câu trả lời:
"""

def set_custom_prompt():
  prompt = PromptTemplate(template=custom_prompt_template,
                          input_variables=['history_global','context', 'question'])
  return prompt

# --- 4. LỚP BOT ---
class OpenRouterRAGBot: # Tên class giữ nguyên để không phải sửa file khác
    def __init__(self):
        if not GROQ_API_KEY:
            self.chain = None
            return

        # [THAY ĐỔI] Cấu hình kết nối sang Groq
        self.model = ChatOpenAI(
            model=MODEL_NAME,
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1", # URL của Groq
            temperature=generation_config["temperature"],
            max_tokens=generation_config["max_tokens"],
            # Groq không cần default_headers như OpenRouter, nên bỏ đi cũng được
        )
        
        self.prompt = set_custom_prompt()
        self.chain = self.prompt | self.model | StrOutputParser()

    def response(self, user_question: str, chat_history: str, context_data: str):
        if not self.chain:
            return "Lỗi hệ thống: Chưa cấu hình GROQ API Key."

        try:
            return self.chain.invoke({
                "history_global": chat_history,
                "context": context_data,
                "question": user_question
            })
        except Exception as e:
            print(f"❌ Lỗi khi gọi API Groq: {e}") 
            return f"Lỗi kết nối AI: {str(e)}"

# --- 5. KHỞI TẠO BOT ---
rag_bot = OpenRouterRAGBot()