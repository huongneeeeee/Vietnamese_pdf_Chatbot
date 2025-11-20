import json
import os
import shutil
import tempfile
from flask import Flask, render_template, request, jsonify
# [SỬA] Import class mới
from document_processor import DocumentDatabaseManager 
from bot_logic import chatBotMode
from text_processor import TextProcessor

vector_db_path = "vectorstores"
hash_store_path = "vectorstores/hashes.json"
pdf_data_path = '' # Temp dir

app = Flask(__name__)

text_processor = TextProcessor()
# [SỬA] Dùng DocumentDatabaseManager
manager = DocumentDatabaseManager(pdf_data_path, vector_db_path, hash_store_path)

global_vector_dbs = {}
bot = chatBotMode(vector_dbs=global_vector_dbs)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'pdf_docs' not in request.files: # Tên field input giữ nguyên hoặc đổi tùy frontend
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('pdf_docs')
    if not files:
        return jsonify({'error': 'No selected file'}), 400

    with tempfile.TemporaryDirectory() as temp_dir:
        # Cập nhật lại đường dẫn temp cho manager
        manager.data_path = temp_dir 
        
        processed = []
        for file in files:
            if file.filename == '': continue
            
            file_path = os.path.join(temp_dir, file.filename)
            file.save(file_path)
            
            # Xử lý file (PDF, DOCX, TXT)
            if not manager.is_file_exists(file_path):
                print(f"Processing {file.filename}...")
                db = manager.update_db(file_path)
                if db:
                    global_vector_dbs[file.filename] = db
                    processed.append(file.filename)
            else:
                print(f"{file.filename} already exists.")
                if file.filename not in global_vector_dbs:
                    db = manager.load_existing_db(file.filename)
                    if db:
                        global_vector_dbs[file.filename] = db
                        
    return jsonify({'processed_files': list(global_vector_dbs.keys())})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_question = data.get('question')
    selected_files = data.get('selected_pdfs', []) 
    chat_history = data.get('history', "")      
    
    if not global_vector_dbs:
        return jsonify({'response': 'Vui lòng tải tài liệu lên trước.', 'sources': []})

    # Gọi bot logic mới (trả về dict)
    result = bot.process_question(
        user_question=user_question,
        selected_files=selected_files,
        chat_history_str=chat_history
    )
    
    # result bao gồm: response, sources (chi tiết), followup
    return jsonify(result)

# [MỚI] Endpoint xóa file cụ thể
@app.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.json
    filename = data.get('filename')
    
    if filename and filename in global_vector_dbs:
        # 1. Xóa khỏi RAM
        del global_vector_dbs[filename]
        # 2. Xóa khỏi Ổ cứng
        manager.delete_file_data(filename)
        return jsonify({'status': 'success', 'message': f'Deleted {filename}'})
    
    return jsonify({'status': 'error', 'message': 'File not found'})

@app.route('/clean', methods=['POST'])
def clean_all():
    try:
        if os.path.exists("vectorstores"):
            shutil.rmtree("vectorstores")
        if os.path.exists("original_text"):
            shutil.rmtree("original_text")
        global_vector_dbs.clear()
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
                 db = manager.load_existing_db(filename)
                 if db:
                     global_vector_dbs[filename] = db
    
    app.run(debug=True, port=5000)