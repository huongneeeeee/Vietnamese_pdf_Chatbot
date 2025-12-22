import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI 

# --- 1. CẤU HÌNH MÔI TRƯỜNG & API KEY ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("⚠️ CẢNH BÁO: Không tìm thấy GROQ_API_KEY trong file .env")

MODEL_NAME = "llama-3.3-70b-versatile"

# --- 2. CẤU HÌNH MODEL ---
generation_config = {
  "temperature": 0.3, # Tăng nhẹ để văn phong tự nhiên hơn khi tóm tắt
  "max_tokens": 1500, # Tăng token để trả lời dài hơn khi tổng hợp
}

# --- 3. PROMPT TEMPLATE (TỐI ƯU CHO TỔNG HỢP & TIẾNG VIỆT) ---
custom_prompt_template = """
Bạn là một trợ lý AI chuyên nghiệp, chuyên hỗ trợ người dùng Việt Nam tổng hợp và tra cứu thông tin từ tài liệu.

Dưới đây là các đoạn thông tin (Context) được trích xuất từ các tài liệu khác nhau:

---------------------
{context}
---------------------

Lịch sử chat:

{history_global}

Câu hỏi của người dùng: 
{question}

NHIỆM VỤ CỦA BẠN (BẮT BUỘC TUÂN THỦ):
1. **NGÔN NGỮ:** CÂU TRẢ LỜI PHẢI 100% BẰNG TIẾNG VIỆT. Dù câu hỏi là tiếng Anh hay ngôn ngữ nào khác, bạn vẫn phải trả lời bằng tiếng Việt.
2. **TỔNG HỢP:** Nếu thông tin nằm rải rác ở nhiều đoạn văn hoặc nhiều file khác nhau, hãy xâu chuỗi chúng lại thành một câu trả lời mạch lạc, logic. Đừng chỉ liệt kê rời rạc.
3. **HIỂU Ý:** Nếu câu hỏi quá ngắn (ví dụ: "tóm tắt", "summary"), hãy hiểu là người dùng muốn tóm tắt nội dung chính của các tài liệu được cung cấp.
4. **TRUNG THỰC:** Chỉ dùng thông tin trong Context. Nếu không tìm thấy thông tin, hãy trả lời: "Xin lỗi, tôi không tìm thấy thông tin này trong các tài liệu bạn đã chọn."

Câu trả lời (Tiếng Việt):
"""

def set_custom_prompt():
  return PromptTemplate(template=custom_prompt_template, input_variables=['history_global','context', 'question'])

# --- 4. LỚP BOT ---
class OpenRouterRAGBot: 
    def __init__(self):
        if not GROQ_API_KEY:
            self.chain = None
            return

        self.model = ChatOpenAI(
            model=MODEL_NAME,
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            temperature=generation_config["temperature"],
            max_tokens=generation_config["max_tokens"],
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