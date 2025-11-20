import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI 

# --- 1. CẤU HÌNH MÔI TRƯỜNG & API KEY ---
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
YOUR_SITE_URL = os.getenv("YOUR_SITE_URL", "http://localhost:5000")
YOUR_SITE_NAME = os.getenv("YOUR_SITE_NAME", "My Flask RAG Bot")

# [CẬP NHẬT] Tên model mới theo yêu cầu
MODEL_NAME = "meta-llama/llama-3.3-70b-instruct:free"

# --- 2. CẤU HÌNH MODEL ---
generation_config = {
  "temperature": 0.1,
  "max_tokens": 1000,
}

# --- 3. PROMPT TEMPLATE (GIỮ NGUYÊN LOGIC THÔNG MINH) ---
custom_prompt_template = """
You are an AI assistant that answers strictly based on the provided data.
I will provide you with text segments (Context) extracted from documents.

YOUR MISSION:
1. Answer the question based ONLY on the information in the "Context" provided below.
2. DO NOT use outside knowledge.

3. LANGUAGE & PRIORITY RULES (CRITICAL):
   - PRIORITY 1 (HIGHEST): If the user explicitly asks to answer in a specific language (e.g., "answer in English", "trả lời bằng tiếng Việt"), YOU MUST OBEY that request.
   - PRIORITY 2: If no specific language is requested, match the language of the User Question.

4. NOT FOUND RULE:
   - If the info is missing in Context, reply exactly:
     (In English): "This information is not found in the provided documents."
     (In Vietnamese): "Thông tin này không có trong tài liệu bạn cung cấp."

Context:
{context}

Chat History:
{history_global}

User Question: 
{question}

Answer:
"""

# Prompt gợi ý câu hỏi (nếu cần dùng lại sau này)
followup_prompt_template = """
Based on the answer below, generate 3 short follow-up questions.
Rules:
1. List exactly 3 questions.
2. Format: One question per line, starting with a dash (-).
3. Language: Match the language of the "Previous Answer".

Previous Answer: 
{answer}

Suggested Questions:
"""

def set_custom_prompt():
  return PromptTemplate(template=custom_prompt_template, input_variables=['history_global','context', 'question'])

def set_followup_prompt():
  return PromptTemplate(template=followup_prompt_template, input_variables=['answer'])

class OpenRouterRAGBot:
    def __init__(self):
        if not OPENROUTER_API_KEY:
            self.chain = None
            print("⚠️ Lỗi: Chưa cấu hình OPENROUTER_API_KEY trong file .env")
            return

        # [QUAY LẠI] Sử dụng ChatOpenAI của LangChain
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
        
        # Tạo Chain: Prompt -> Model -> String Output
        self.prompt = set_custom_prompt()
        self.chain = self.prompt | self.model | StrOutputParser()
        
        # Chain tạo gợi ý (Optional)
        self.followup_prompt = set_followup_prompt()
        self.followup_chain = self.followup_prompt | self.model | StrOutputParser()

    def response(self, user_question: str, chat_history: str, context_data: str):
        """
        Hàm xử lý chính: Nhận input -> Chạy Chain -> Trả về text
        """
        if not self.chain: return "Lỗi hệ thống: Chưa cấu hình API Key."
        
        # Kiểm tra Context rỗng để tiết kiệm token
        if not context_data or context_data.strip() == "":
             q_lower = user_question.lower()
             # Logic báo lỗi nhanh theo ngôn ngữ
             if "in english" in q_lower or "speak english" in q_lower:
                 return "This information is not found in the provided documents."
             if "tiếng việt" in q_lower:
                 return "Thông tin này không có trong tài liệu bạn cung cấp."
             
             is_english = any(w in q_lower for w in ['what', 'how', 'who', 'when', 'where', 'why', 'is', 'are'])
             return "This information is not found in the provided documents." if is_english else "Thông tin này không có trong tài liệu bạn cung cấp."

        try:
            # Gọi LangChain invoke
            return self.chain.invoke({
                "history_global": chat_history,
                "context": context_data,
                "question": user_question
            })
        except Exception as e:
            print(f"❌ Lỗi API: {e}")
            return "Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu."

    def generate_followup(self, answer_text):
        if not self.chain: return ""
        try:
            return self.followup_chain.invoke({"answer": answer_text})
        except:
            return ""

# Khởi tạo bot
rag_bot = OpenRouterRAGBot()