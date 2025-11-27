import hashlib
import os
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from embedding import custom_embeddings
from text_processor import TextProcessor

text_processor = TextProcessor()

# [QUAN TRỌNG] Đổi tên class thành DocumentDatabaseManager để khớp với app.py
class DocumentDatabaseManager:
    def __init__(self, data_path, vector_db_path, hash_store_path):
        self.data_path = data_path
        self.vector_db_path = vector_db_path
        self.hash_store_path = hash_store_path
        if not os.path.exists(self.vector_db_path):
            os.makedirs(self.vector_db_path)

    def calculate_file_hash(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(4096), b""):
                hasher.update(block)
        return hasher.hexdigest()

    def load_existing_hashes(self):
        try:
            if os.path.exists(self.hash_store_path):
                with open(self.hash_store_path, 'r') as f:
                    return json.load(f)
        except json.JSONDecodeError:
            pass
        return {}

    def save_hashes(self, hashes):
        try:
            with open(self.hash_store_path, 'w') as f:
                json.dump(hashes, f)
        except IOError as e:
            print(f"Error saving hashes: {e}")

    def get_loader(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return PyPDFLoader(file_path)
        elif ext == '.docx':
            return Docx2txtLoader(file_path)
        elif ext == '.txt':
            return TextLoader(file_path, encoding='utf-8')
        else:
            print(f"Unsupported file type: {ext}")
            return None

    def process_document(self, document):
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ".", "!", "?", ""],
            chunk_size=512,
            chunk_overlap=128,
            length_function=len
        )
        chunks = text_splitter.split_documents([document])
        return chunks

    def load_existing_db(self, file_name):
        file_name_clean = text_processor.remove_accents(os.path.splitext(file_name)[0])
        db_path = os.path.join(self.vector_db_path, file_name_clean)
        
        if os.path.exists(db_path):
            try:
                return FAISS.load_local(db_path, custom_embeddings, allow_dangerous_deserialization=True)
            except Exception as e:
                print(f"Error loading database for {file_name}: {e}")
        return None

    def is_file_exists(self, file_path):
        if not os.path.exists(file_path): return False
        file_hash = self.calculate_file_hash(file_path)
        existing_hashes = self.load_existing_hashes()
        return file_hash in existing_hashes

    def update_db(self, file_path):
        if not os.path.exists(file_path): return None

        file_hash = self.calculate_file_hash(file_path)
        existing_hashes = self.load_existing_hashes()

        if file_hash in existing_hashes:
            print(f"File {file_path} already exists.")
            return None

        loader = self.get_loader(file_path)
        if not loader: return None
            
        try:
            documents = loader.load()
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")
            return None

        output_dir = 'original_text'
        os.makedirs(output_dir, exist_ok=True)
        file_name = os.path.basename(file_path)
        file_name_without_ext = text_processor.remove_accents(os.path.splitext(file_name)[0])
        output_file_name = f"{file_name_without_ext}.txt"
        output_file_path = os.path.join(output_dir, output_file_name)

        all_text = "\n".join(doc.page_content for doc in documents)
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(all_text)

        chunks = []
        for doc in documents:
            page_chunks = self.process_document(doc)
            chunks.extend(page_chunks)

        if chunks:
            db = FAISS.from_documents(chunks, custom_embeddings)
            db_path = os.path.join(self.vector_db_path, file_name_without_ext)
            db.save_local(db_path)
            
            existing_hashes[file_hash] = file_path
            self.save_hashes(existing_hashes)
            return db
        return None

    def delete_file_data(self, file_name):
        existing_hashes = self.load_existing_hashes()
        hash_to_remove = None
        for h, path in existing_hashes.items():
            if os.path.basename(path) == file_name:
                hash_to_remove = h
                break
        
        if hash_to_remove:
            del existing_hashes[hash_to_remove]
            self.save_hashes(existing_hashes)

        file_name_clean = text_processor.remove_accents(os.path.splitext(file_name)[0])
        db_path = os.path.join(self.vector_db_path, file_name_clean)
        txt_path = os.path.join("original_text", f"{file_name_clean}.txt")
        
        import shutil
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        if os.path.exists(txt_path):
            os.remove(txt_path)
        return True

class ContextRetriever:
    def __init__(self, context_dir='original_text'):
        self.context_dir = context_dir

    def read_text_file(self, file_name):
        if not file_name.endswith('.txt'):
            file_name += '.txt'
        file_path = os.path.join(self.context_dir, file_name)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
        except IOError: pass
        return ""

    def expand_context(self, file_name_clean, context, num_words=150):
        all_text = self.read_text_file(file_name_clean)
        if not all_text: return context
        idx = all_text.find(context)
        if idx != -1:
            start = max(0, idx - num_words * 5)
            end = min(len(all_text), idx + len(context) + num_words * 5)
            return "..." + all_text[start:end] + "..."
        return context

    def get_file_name(self, metadata):
        source = metadata.get('source', '')
        file_name = os.path.basename(source)
        return TextProcessor().remove_accents(os.path.splitext(file_name)[0])