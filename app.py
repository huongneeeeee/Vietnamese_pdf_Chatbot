import json
import os
import shutil
import tempfile
from flask import Flask, render_template, request, jsonify
# [SỬA LẠI] Import từ pdf_processor thay vì document_processor
from pdf_processor import DocumentDatabaseManager 
from bot_logic import chatBotMode
from text_processor import TextProcessor
import database as db 

# Đổi tên thư mục lưu trữ để tránh xung đột
vector_db_path = "vectorstores"
hash_store_path = "vectorstores/hashes.json"
pdf_data_path = '' # Temp dir

app = Flask(__name__)

text_processor = TextProcessor()
# [SỬA] Dùng DocumentDatabaseManager từ pdf_processor
manager = DocumentDatabaseManager(pdf_data_path, vector_db_path, hash_store_path)

# Cache để lưu các DB đã load
loaded_vector_dbs_cache = {} 
bot = chatBotMode(vector_dbs=loaded_vector_dbs_cache)

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

# --- FILE MANAGEMENT API ---
@app.route('/get_uploaded_files', methods=['GET'])
def get_uploaded_files_endpoint():
    session_id = request.args.get('session_id')
    if not session_id: return jsonify({'files': []})
    files = db.get_files_by_session(session_id)
    return jsonify({'files': files})

@app.route('/remove_file', methods=['POST'])
def remove_file_endpoint():
    data = request.json
    filename = data.get('filename')
    session_id = data.get('session_id')
    if filename and session_id:
        db.remove_file_from_session(session_id, filename)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Missing info'}), 400

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'pdf_docs' not in request.files: return jsonify({'error': 'No file part'}), 400
    files = request.files.getlist('pdf_docs')
    session_id = request.form.get('session_id')

    if not session_id: return jsonify({'error': 'Session ID missing'}), 400

    successful_files = []
    errors = []

    with tempfile.TemporaryDirectory() as temp_dir:
        # Cập nhật đường dẫn temp cho manager (Lưu ý: thuộc tính này phải có trong DocumentDatabaseManager)
        manager.data_path = temp_dir 
        
        for file in files:
            try:
                file_path = os.path.join(temp_dir, file.filename)
                file.save(file_path)
                
                # Xử lý file
                if not manager.is_file_exists(file_path):
                    print(f"Processing new file: {file.filename}...")
                    db_instance = manager.update_db(file_path)
                    if db_instance:
                        loaded_vector_dbs_cache[file.filename] = db_instance
                    else:
                        errors.append(f"Lỗi xử lý {file.filename}")
                else:
                    print(f"File {file.filename} already processed. Linking to session.")
                    if file.filename not in loaded_vector_dbs_cache:
                        db_instance = manager.load_existing_db(file.filename)
                        if db_instance:
                            loaded_vector_dbs_cache[file.filename] = db_instance

                # Gắn file vào session
                if file.filename in loaded_vector_dbs_cache or manager.is_file_exists(file_path):
                     db.add_file_to_session(session_id, file.filename, file_path)
                     successful_files.append(file.filename)

            except Exception as e:
                print(f"Error uploading {file.filename}: {e}")
                errors.append(f"Lỗi {file.filename}: {str(e)}")
    
    current_session_files = db.get_files_by_session(session_id)
    return jsonify({
        'processed_files': current_session_files,
        'errors': errors
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_question = data.get('question')
    chat_history = data.get('history', "")
    session_id = data.get('session_id')

    session_files = db.get_files_by_session(session_id)
    if not session_files:
        return jsonify({'response': 'Bạn chưa tải tài liệu nào lên cuộc trò chuyện này.', 'context': ''})

    valid_pdfs_for_chat = []
    for fname in session_files:
        if fname not in loaded_vector_dbs_cache:
            db_instance = manager.load_existing_db(fname)
            if db_instance:
                loaded_vector_dbs_cache[fname] = db_instance
        
        if fname in loaded_vector_dbs_cache:
            valid_pdfs_for_chat.append(fname)

    if not valid_pdfs_for_chat:
        return jsonify({'response': 'Lỗi: Không tìm thấy dữ liệu vector của file.', 'context': ''})

    # Gọi Bot
    result = bot.process_question(
        user_question=user_question,
        selected_pdfs=valid_pdfs_for_chat, 
        chat_history_str=chat_history
    )
    
    final_response = result['response']
    
    # Định dạng nguồn đẹp hơn
    if result['sources']:
        final_response = f"{final_response}\n\n**Nguồn tham khảo:** {', '.join(result['sources'])}"

    if session_id:
        db.save_message(session_id, user_query=user_question, bot_response=final_response)
    
    # Trả về JSON
    return jsonify({
        'response': final_response, 
        'context': result['context']
    })

@app.route('/clean', methods=['POST'])
def clean_all():
    try:
        if os.path.exists("vectorstores"):
            shutil.rmtree("vectorstores")
        if os.path.exists("original_text"):
            shutil.rmtree("original_text")
        loaded_vector_dbs_cache.clear()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    # Tải lại DB khi khởi động
    if os.path.exists(hash_store_path):
         with open(hash_store_path, 'r') as f:
             hashes = json.load(f)
             for h, path in hashes.items():
                 filename = os.path.basename(path)
                 print(f"Reloading {filename}...")
                 db_instance = manager.load_existing_db(filename)
                 if db_instance:
                     loaded_vector_dbs_cache[filename] = db_instance
    
    app.run(debug=True, port=5000)