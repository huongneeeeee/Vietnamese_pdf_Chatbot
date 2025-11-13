import os
import shutil
import tempfile
from flask import Flask, render_template, request, jsonify
from pdf_processor import PDFDatabaseManager
from bot_logic import chatBotMode
from text_processor import TextProcessor

vector_db_path = "vectorstores/db_faiss"
hash_store_path = "vectorstores/hashes.json"
pdf_data_path = ''

# --- Khởi tạo Flask App ---
app = Flask(__name__)

# --- Khởi tạo các đối tượng xử lý ---
text_processor = TextProcessor()
manager = PDFDatabaseManager(pdf_data_path, vector_db_path, hash_store_path)

# --- TRẠNG THÁI CỦA SERVER ---
global_vector_dbs = {}
bot = chatBotMode(vector_dbs=global_vector_dbs)


# === CÁC API ENDPOINTS ===

@app.route('/')
def index():
    """Cung cấp file giao diện chính (frontend)"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """Xử lý việc tải file PDF lên"""
    if 'pdf_docs' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('pdf_docs')
    if not files:
        return jsonify({'error': 'No selected file'}), 400

    with tempfile.TemporaryDirectory() as temp_dir:
        manager.pdf_data_path = temp_dir
        
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            file.save(file_path)
            
            # Logic xử lý PDF 
            if not manager.is_pdf_exists(file_path):
                print(f"Processing {file.filename}...")
                db = manager.update_db(file_path)
                if db is not None:
                    global_vector_dbs[file.filename] = db
            else:
                print(f"{file.filename} already exists.")
                # Tải DB đã tồn tại nếu chưa có trong bộ nhớ
                if file.filename not in global_vector_dbs:
                    db = manager.load_existing_db(file.filename)
                    if db:
                        global_vector_dbs[file.filename] = db
                        
    # Trả về danh sách các file PDF hiện có
    return jsonify({'processed_files': list(global_vector_dbs.keys())})


@app.route('/chat', methods=['POST'])
def chat():
    """Xử lý một câu hỏi chat từ người dùng"""
    data = request.json
    if not data or 'question' not in data:
        return jsonify({'error': 'Invalid request'}), 400

    user_question = data.get('question')
    selected_pdfs = data.get('selected_pdfs', []) 
    chat_history = data.get('history', "")      
    if not global_vector_dbs:
        return jsonify({'response': 'Lỗi: Vui lòng tải lên tệp PDF trước.', 'context': ''})
    if not selected_pdfs:
        return jsonify({'response': 'Lỗi: Vui lòng chọn ít nhất một tệp PDF để truy vấn.', 'context': ''})

    # Gọi hàm process_question 
    response, context = bot.process_question(
        user_question=user_question,
        selected_pdfs=selected_pdfs,
        chat_history_str=chat_history
    )
    
    return jsonify({'response': response, 'context': context})


@app.route('/clean', methods=['POST'])
def clean_data_endpoint():
    """Xóa dữ liệu cũ (giống hàm clean_data)"""
    try:
        if os.path.exists("vectorstores"):
            shutil.rmtree("vectorstores")
        if os.path.exists("original_text"):
            shutil.rmtree("original_text")
        
        # Reset trạng thái server
        global_vector_dbs.clear()
        
        return jsonify({'status': 'success', 'message': 'Dữ liệu đã được xóa.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Chạy Server ---
if __name__ == "__main__":
    # Tải các DB đã tồn tại trong 'vectorstores' lên bộ nhớ khi khởi động
    if os.path.exists(vector_db_path):
        print("Loading existing databases...")
        # Lấy tên file từ file hash (hoặc quét thư mục)
        if os.path.exists(hash_store_path):
             pass 
    
    app.run(debug=True, port=5000)