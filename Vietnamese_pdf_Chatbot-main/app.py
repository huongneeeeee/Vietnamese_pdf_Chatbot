import os
import shutil
import tempfile
from flask import Flask, render_template, request, jsonify
from pdf_processor import PDFDatabaseManager
from bot_logic import chatBotMode
from text_processor import TextProcessor
import database as db 

# --- CẤU HÌNH ---
vector_db_path = "vectorstores/db_faiss"
hash_store_path = "vectorstores/hashes.json"
pdf_data_path = ''

app = Flask(__name__)

# --- KHỞI TẠO ---
text_processor = TextProcessor()
manager = PDFDatabaseManager(pdf_data_path, vector_db_path, hash_store_path)

# Lưu trữ trạng thái DB trong RAM
global_vector_dbs = {}
bot = chatBotMode(vector_dbs=global_vector_dbs)

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

# 1. NHÓM SESSION & HISTORY
@app.route('/get_sessions', methods=['GET'])
def get_sessions():
    sessions = db.get_all_sessions()
    return jsonify(sessions)

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
    if not session_id:
        return jsonify([])
    history = db.get_history(session_id)
    return jsonify(history)

# 2. NHÓM QUẢN LÝ FILE
@app.route('/get_uploaded_files', methods=['GET'])
def get_uploaded_files_endpoint():
    """Trả về danh sách các file đang có trong bộ nhớ (RAM)"""
    return jsonify({'files': list(global_vector_dbs.keys())})

@app.route('/remove_file', methods=['POST'])
def remove_file_endpoint():
    """Xóa một file cụ thể khỏi RAM"""
    data = request.json
    filename = data.get('filename')
    
    if filename and filename in global_vector_dbs:
        del global_vector_dbs[filename]
        print(f"Deleted {filename} from memory.")
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'File not found'}), 400

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'pdf_docs' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('pdf_docs')
    if not files:
        return jsonify({'error': 'No selected file'}), 400

    successful_files = []
    errors = []

    with tempfile.TemporaryDirectory() as temp_dir:
        manager.pdf_data_path = temp_dir
        
        for file in files:
            try:
                file_path = os.path.join(temp_dir, file.filename)
                file.save(file_path)
                
                if not manager.is_pdf_exists(file_path):
                    print(f"Processing {file.filename}...")
                    db_instance = manager.update_db(file_path)
                    if db_instance is not None:
                        global_vector_dbs[file.filename] = db_instance
                        successful_files.append(file.filename)
                    else:
                        errors.append(f"Lỗi xử lý {file.filename}")
                else:
                    print(f"{file.filename} already exists.")
                    if file.filename not in global_vector_dbs:
                        db_instance = manager.load_existing_db(file.filename)
                        if db_instance:
                            global_vector_dbs[file.filename] = db_instance
                    successful_files.append(file.filename)
            except Exception as e:
                print(f"Error uploading {file.filename}: {e}")
                errors.append(f"Lỗi {file.filename}: {str(e)}")
                        
    return jsonify({
        'processed_files': list(global_vector_dbs.keys()),
        'errors': errors
    })

# 3. NHÓM CHAT & CLEAN
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'question' not in data:
        return jsonify({'error': 'Invalid request'}), 400

    user_question = data.get('question')
    selected_pdfs = data.get('selected_pdfs', []) 
    chat_history = data.get('history', "")
    session_id = data.get('session_id')

    if not global_vector_dbs:
        return jsonify({'response': 'Lỗi: Vui lòng tải lên tài liệu trước.', 'context': ''})
    if not selected_pdfs:
        return jsonify({'response': 'Lỗi: Vui lòng chọn ít nhất một file để hỏi.', 'context': ''})

    response, context = bot.process_question(
        user_question=user_question,
        selected_pdfs=selected_pdfs,
        chat_history_str=chat_history
    )
    
    if session_id:
        db.save_message(session_id, user_query=user_question, bot_response=response)
    
    return jsonify({'response': response, 'context': context})


@app.route('/clean', methods=['POST'])
def clean_data_endpoint():
    try:
        session_id = request.json.get('session_id')
        
        if os.path.exists("vectorstores"):
            try:
                shutil.rmtree("vectorstores")
            except PermissionError:
                pass
        if os.path.exists("original_text"):
            try:
                shutil.rmtree("original_text")
            except PermissionError:
                pass
        
        global_vector_dbs.clear()
        
        if session_id:
            db.clear_history(session_id)
        
        return jsonify({'status': 'success', 'message': 'Dữ liệu đã được xóa.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    if os.path.exists(vector_db_path):
        print("Loading existing databases logic (skipped for clean start)...")
    app.run(debug=True, port=5000)