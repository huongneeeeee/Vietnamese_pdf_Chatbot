# Vietnamese PDF Chatbot (RAG Technology)

> **Hệ thống Chatbot hỗ trợ truy vấn văn bản tiếng Việt sử dụng công nghệ Retrieval-Augmented Generation (RAG)**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Backend-green)
![Llama-3](https://img.shields.io/badge/AI-Llama--3-orange)
![Groq](https://img.shields.io/badge/Inference-Groq_LPU-purple)
![LangChain](https://img.shields.io/badge/Orchestration-LangChain-blueviolet)

## 📖 Giới thiệu
Dự án này là một ứng dụng Web Chatbot thông minh, cho phép người dùng tải lên các tài liệu (PDF, DOCX, TXT) và đặt câu hỏi liên quan đến nội dung tài liệu đó. Hệ thống sử dụng kiến trúc **RAG (Retrieval-Augmented Generation)** kết hợp với mô hình ngôn ngữ lớn **Llama-3** để đưa ra câu trả lời chính xác, trung thực và tự nhiên bằng tiếng Việt.

## Tính năng nổi bật

### Trí tuệ nhân tạo & Xử lý ngôn ngữ
* **LLM mạnh mẽ:** Tích hợp **Llama-3-70b** thông qua **Groq API** (chạy trên chip LPU) cho tốc độ phản hồi cực nhanh.
* **Tối ưu tiếng Việt:** Sử dụng mô hình Embedding chuyên biệt `hiieu/halong_embedding` để hiểu sâu ngữ nghĩa tiếng Việt.
* **Prompt Engineering:** Áp dụng kỹ thuật *Instruction Tuning* để đảm bảo Bot luôn trả lời tiếng Việt và trung thực với tài liệu.
* **Query Rewriting:** Tự động viết lại các câu hỏi ngắn/thiếu ý để tăng độ chính xác khi tìm kiếm.

### Hiệu năng & Tối ưu hóa
* **Vector Database:** Sử dụng **FAISS** để tìm kiếm tương đồng (Similarity Search) tốc độ cao.
* **Chống trùng lặp (Hashing):** Sử dụng thuật toán **SHA-256** để kiểm tra mã băm của file. Nếu file đã tồn tại, hệ thống tái sử dụng Vector cũ -> Tiết kiệm tài nguyên và thời gian xử lý.
* **Lọc nhiễu (Noise Filtering):** Loại bỏ các đoạn văn bản không liên quan dựa trên ngưỡng tương đồng (`threshold = 1.8`).

### Quản lý dữ liệu & Phiên làm việc
* **Session Management:** Sử dụng **SQLite** để lưu trữ lịch sử chat và trạng thái phiên làm việc. Đảm bảo F5 không mất dữ liệu.
* **Quản lý file:** Hỗ trợ tải lên nhiều file cùng lúc và chọn/bỏ chọn file ngữ cảnh linh hoạt.

## Cài đặt và Chạy dự án

### 1. Yêu cầu hệ thống
* Python 3.8 trở lên
* Git

### 2. Clone dự án
```bash
git clone [https://github.com/your-username/Vietnamese_pdf_Chatbot.git](https://github.com/your-username/Vietnamese_pdf_Chatbot.git)
cd Vietnamese_pdf_Chatbot
