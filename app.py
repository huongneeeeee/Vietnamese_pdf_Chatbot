import os
import shutil
import tempfile
from flask import Flask, render_template, request, jsonify
from pdf_processor import PDFDatabaseManager
from bot_logic import chatBotMode
from text_processor import TextProcessor
import database as db 

vector_db_path = "vectorstores/db_faiss"
hash_store_path = "vectorstores/hashes.json"
pdf_data_path = ''

app = Flask(__name__)

text_processor = TextProcessor()
manager = PDFDatabaseManager(pdf_data_path, vector_db_path, hash_store_path)

# CACHE: Lưu trữ các DB đã load vào RAM để dùng chung (tiết kiệm RAM)
# Tuy nhiên, Bot chỉ được phép truy cập các DB mà Session cho phép.
loaded_vector_dbs_cache = {} 
bot = chatBotMode(vector_dbs=loaded_vector_dbs_cache) # Bot vẫn nhận dict này, nhưng ta sẽ filter khi chat

@app.route('/')
def index():
    return render_template('index.html')

# --- SESSION & HISTORY API ---
@app.route('/get_sessions', methods=['GET'])
def get_sessions():
    return jsonify(db.get_all_sessions())

@app.route('/delete_session', methods=['POST'])
def delete_session_endpoint():
    data = request.json
    session_id = data.get('session_id')
    if session_id:
        db.delete_session(session_id)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@app.route('/get_history', methods=['GET'])
def get_chat_history():
    session_id = request.args.get('session_id')
    if not session_id: return jsonify([])
    return jsonify(db.get_history(session_id))

# --- FILE MANAGEMENT API (CÓ SESSION) ---

@app.route('/get_uploaded_files', methods=['GET'])
def get_uploaded_files_endpoint():
    """
    Trả về danh sách file CHỈ CỦA session hiện tại.
    """
    session_id = request.args.get('session_id') # Frontend phải gửi session_id lên
    if not session_id:
        return jsonify({'files': []})
    
    files = db.get_files_by_session(session_id)
    return jsonify({'files': files})

@app.route('/remove_file', methods=['POST'])
def remove_file_endpoint():
    """Gỡ file khỏi session hiện tại"""
    data = request.json
    filename = data.get('filename')
    session_id = data.get('session_id') # Frontend gửi lên
    
    if filename and session_id:
        # 1. Xóa liên kết trong DB
        db.remove_file_from_session(session_id, filename)
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Missing info'}), 400

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'pdf_docs' not in request.files: return jsonify({'error': 'No file part'}), 400
    files = request.files.getlist('pdf_docs')
    session_id = request.form.get('session_id') # Frontend gửi session_id qua FormData

    if not session_id: return jsonify({'error': 'Session ID missing'}), 400

    successful_files = []
    errors = []

    with tempfile.TemporaryDirectory() as temp_dir:
        manager.pdf_data_path = temp_dir
        
        for file in files:
            try:
                file_path = os.path.join(temp_dir, file.filename)
                file.save(file_path)
                
                # 1. Xử lý Vector (Nếu file chưa từng tồn tại trên hệ thống)
                if not manager.is_pdf_exists(file_path):
                    print(f"Processing new file: {file.filename}...")
                    db_instance = manager.update_db(file_path)
                    if db_instance:
                        loaded_vector_dbs_cache[file.filename] = db_instance
                    else:
                        errors.append(f"Lỗi xử lý {file.filename}")
                else:
                    print(f"File {file.filename} already processed. Linking to session.")
                    # Nếu đã có trên đĩa, load vào RAM cache nếu chưa có
                    if file.filename not in loaded_vector_dbs_cache:
                        db_instance = manager.load_existing_db(file.filename)
                        if db_instance:
                            loaded_vector_dbs_cache[file.filename] = db_instance

                # 2. QUAN TRỌNG: Gắn file vào Session trong Database
                # Dù file cũ hay mới, ta đều gắn nó vào session hiện tại
                if file.filename in loaded_vector_dbs_cache or manager.is_pdf_exists(file_path):
                     db.add_file_to_session(session_id, file.filename, file_path) # Lưu DB
                     successful_files.append(file.filename)

            except Exception as e:
                print(f"Error uploading {file.filename}: {e}")
                errors.append(f"Lỗi {file.filename}: {str(e)}")
    
    # Trả về danh sách file của session này
    current_session_files = db.get_files_by_session(session_id)
    return jsonify({
        'processed_files': current_session_files,
        'errors': errors
    })

# --- CHAT & CLEAN ---

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_question = data.get('question')
    chat_history = data.get('history', "")
    session_id = data.get('session_id')

    # 1. Lấy danh sách file thuộc session này từ DB
    session_files = db.get_files_by_session(session_id)
    
    if not session_files:
        return jsonify({'response': 'Bạn chưa tải tài liệu nào lên cuộc trò chuyện này.', 'context': ''})

    # 2. Chuẩn bị "selected_pdfs" là các file của session này
    # Đồng thời đảm bảo các file này đã được load vào RAM Cache
    valid_pdfs_for_chat = []
    for fname in session_files:
        if fname not in loaded_vector_dbs_cache:
            # Lazy load: Nếu chưa có trong RAM thì load từ đĩa lên
            db_instance = manager.load_existing_db(fname)
            if db_instance:
                loaded_vector_dbs_cache[fname] = db_instance
        
        if fname in loaded_vector_dbs_cache:
            valid_pdfs_for_chat.append(fname)

    if not valid_pdfs_for_chat:
        return jsonify({'response': 'Lỗi: Không tìm thấy dữ liệu vector của file.', 'context': ''})

    # 3. Gọi Bot, truyền danh sách file của session vào selected_pdfs
    response, context = bot.process_question(
        user_question=user_question,
        selected_pdfs=valid_pdfs_for_chat, # Chỉ tìm trong file của session
        chat_history_str=chat_history
    )
    
    if session_id:
        db.save_message(session_id, user_query=user_question, bot_response=response)
    
    return jsonify({'response': response, 'context': context})


@app.route('/clean', methods=['POST'])
def clean_data_endpoint():
    # Hàm này bây giờ chỉ dùng khi muốn "Reset All System" thật sự
    try:
        if os.path.exists("vectorstores"):
            try: shutil.rmtree("vectorstores")
            except: pass
        os.makedirs("vectorstores", exist_ok=True)
        
        if os.path.exists("original_text"):
            try: shutil.rmtree("original_text")
            except: pass
        
        loaded_vector_dbs_cache.clear()
        # Reset lại DB bằng cách xóa file db hoặc truncate bảng (ở đây ta xóa hết)
        # Lưu ý: Code này xóa sạch sẽ mọi thứ của mọi người dùng
        # Trong thực tế production nên cẩn thận.
        
        return jsonify({'status': 'success', 'message': 'Hệ thống đã được reset.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    os.makedirs("vectorstores", exist_ok=True)
    os.makedirs("original_text", exist_ok=True)
    app.run(debug=True, port=5000)