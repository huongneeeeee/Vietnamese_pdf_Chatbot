import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI 

# --- 1. CẤU HÌNH MÔI TRƯỜNG & API KEY ---
# Load biến môi trường từ file .env
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
YOUR_SITE_URL = os.getenv("YOUR_SITE_URL", "http://localhost:5000")
YOUR_SITE_NAME = os.getenv("YOUR_SITE_NAME", "My Flask RAG Bot")

# Kiểm tra API Key 
if not OPENROUTER_API_KEY:
    print("⚠️ CẢNH BÁO: Không tìm thấy OPENROUTER_API_KEY trong file .env")

# Tên mô hình 
MODEL_NAME = "meta-llama/llama-3-8b-instruct"

# --- 2. CẤU HÌNH MODEL ---
generation_config = {
  "temperature": 0.05,
  "max_tokens": 1000,
}

# --- 3. PROMPT TEMPLATE CHO RAG ---
custom_prompt_template = """
Bạn là một trợ lý RAG (Retrieval-Augmented Generation). Nhiệm vụ của bạn là tổng hợp thông tin từ các đoạn Context được cung cấp để trả lời câu hỏi của người dùng.

HÃY TUÂN THỦ NGHIÊM NGẶT CÁC QUY TẮC SAU:

CHỈ dùng Context: Nguồn thông tin duy nhất là Context. Nghiêm cấm sử dụng kiến thức bên ngoài, suy đoán hoặc bịa đặt thông tin.

Xử lý khi không tìm thấy: Nếu thông tin không có trong Context, bạn PHẢI trả lời: "Tôi không có đủ thông tin để trả lời câu hỏi này. Vui lòng cung cấp thêm thông tin liên quan đến câu hỏi."

Trả lời đầy đủ: Đảm bảo câu trả lời tổng hợp đầy đủ tất cả các chi tiết liên quan đến câu hỏi từ Context. Liệt kê các ý nếu cần.

Xử lý nhiều Context: Bạn sẽ nhận được một hoặc nhiều đoạn Context, ngăn cách bởi "SEPARATED". Hãy đọc tất cả các đoạn để tìm thông tin.

Xử lý Lịch sử (History): Chỉ tham chiếu History nếu câu hỏi hiện tại có liên quan hoặc hỏi tiếp về cuộc trò chuyện trước đó (ví dụ: "viết thêm chi tiết").

History: {history_global}

Context: {context}

Question: {question}

Câu trả lời:
"""

def set_custom_prompt():
  """
  Hàm này tạo và trả về PromptTemplate của LangChain.
  """
  prompt = PromptTemplate(template=custom_prompt_template,
                          input_variables=['history_global','context', 'question'])
  return prompt

# --- 4. LỚP BOT ---
class OpenRouterRAGBot:
    def __init__(self):
        # Nếu không có key, không khởi tạo model để tránh lỗi crash app ngay lập tức
        if not OPENROUTER_API_KEY:
            self.chain = None
            return

        # Khởi tạo model của LangChain
        self.model = ChatOpenAI(
            model=MODEL_NAME,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=generation_config["temperature"],
            max_tokens=generation_config["max_tokens"],
            default_headers={
                "HTTP-Referer": YOUR_SITE_URL, 
                "X-Title": YOUR_SITE_NAME
            }
        )
        
        # Lấy prompt từ hàm của bạn
        self.prompt = set_custom_prompt()
        
        # Tạo CHUỖI (chain) xử lý: Prompt -> Model -> Trích xuất text
        self.chain = self.prompt | self.model | StrOutputParser()

    def response(self, user_question: str, chat_history: str, context_data: str):
        """
        Hàm này nhận các ĐẦU VÀO THÔ (question, history, context)
        và thực thi toàn bộ chuỗi RAG.
        """
        if not self.chain:
            return "Lỗi hệ thống: Chưa cấu hình API Key."

        try:
            return self.chain.invoke({
                "history_global": chat_history,
                "context": context_data,
                "question": user_question
            })
        except Exception as e:
            # In lỗi ra terminal server để debug
            print(f"❌ Lỗi khi gọi API OpenRouter: {e}") 
            return "Xin lỗi, đã có lỗi xảy ra khi kết nối với AI. Vui lòng thử lại sau."

# --- 5. KHỞI TẠO BOT ---
rag_bot = OpenRouterRAGBot()