document.addEventListener("DOMContentLoaded", () => {
    
    const pdfUploader = document.getElementById("pdf-uploader");
    const uploadButton = document.getElementById("upload-button");
    const uploadSpinner = document.getElementById("upload-spinner");
    const uploadStatus = document.getElementById("upload-status");
    const pdfListDiv = document.getElementById("pdf-list");
    
    const chatMessages = document.getElementById("chat-messages");
    const userInput = document.getElementById("user-input");
    const sendButton = document.getElementById("send-button");
    const thinkingIndicator = document.getElementById("thinking-indicator");
    const cleanButton = document.getElementById("clean-button"); 
    
    const chatHistoryList = document.getElementById("chat-history-list");
    const newChatBtn = document.getElementById("new-chat-btn");

    let chatHistory = []; 
    let selectedPDFs = new Set();
    let currentSessionId = null; 

    function init() {
        const savedSession = localStorage.getItem("current_session_id");
        if (savedSession) {
            currentSessionId = savedSession;
        } else {
            createNewSessionId(); 
        }
        refreshInterface();
    }

    function refreshInterface() {
        loadSidebarSessions(); 
        loadChatContent(currentSessionId);
        loadUploadedFiles(currentSessionId); // Load file của session hiện tại
    }

    function createNewSessionId() {
        currentSessionId = "sess_" + Math.random().toString(36).substr(2, 9);
        localStorage.setItem("current_session_id", currentSessionId);
        return currentSessionId;
    }

    // === 1. LOAD FILE CỦA SESSION ===
    async function loadUploadedFiles(sessionId) {
        try {
            // Gửi session_id lên để lấy đúng file
            const response = await fetch(`/get_uploaded_files?session_id=${sessionId}`);
            const data = await response.json();
            updatePDFList(data.files || []);
        } catch (error) {
            console.error("Failed to load uploaded files:", error);
        }
    }

    // === 2. NÚT CUỘC TRÒ CHUYỆN MỚI (ĐÚNG Ý BẠN) ===
    async function handleNewChat() {
        // Logic: Chỉ tạo ID mới, giao diện mới. KHÔNG XÓA DỮ LIỆU CŨ.
        createNewSessionId();
        
        // Reset giao diện
        chatMessages.innerHTML = ""; 
        chatHistory = [];
        pdfUploader.value = "";
        if (uploadStatus) uploadStatus.textContent = "";
        
        // Reset danh sách file về rỗng (vì session mới chưa có file)
        updatePDFList([]); 
        
        // Cập nhật sidebar để bỏ highlight cái cũ
        loadSidebarSessions();
    }

    // === 3. CHUYỂN SESSION (KHI BẤM LỊCH SỬ) ===
    function switchSession(sessionId) {
        if (currentSessionId === sessionId) return; 
        currentSessionId = sessionId;
        localStorage.setItem("current_session_id", currentSessionId);
        
        // Khi chuyển session, load lại cả Chat và File của session đó
        loadChatContent(sessionId);
        loadUploadedFiles(sessionId); // <--- QUAN TRỌNG: File cũ sẽ hiện lại
        loadSidebarSessions(); 
    }

    // === 4. UPLOAD FILE (GẮN VỚI SESSION) ===
    async function handleUpload() {
        if (pdfUploader.files.length === 0) return;
        
        const formData = new FormData();
        for (const file of pdfUploader.files) formData.append("pdf_docs", file);
        // Gửi kèm Session ID
        formData.append("session_id", currentSessionId); 
        
        uploadSpinner.style.display = "block";
        uploadButton.disabled = true; 
        
        try {
            const response = await fetch('/upload', { method: 'POST', body: formData });
            const data = await response.json();
            
            if (data.errors && data.errors.length > 0) alert("Lỗi:\n" + data.errors.join("\n"));
            
            updatePDFList(data.processed_files);
            uploadStatus.textContent = `Đã thêm ${data.processed_files.length} file vào cuộc trò chuyện này.`;
        } catch (e) { 
            console.error(e); 
            uploadStatus.textContent = "Lỗi upload.";
        }
        finally { 
            uploadSpinner.style.display = "none"; 
            uploadButton.disabled = false;
        }
    }

    // === 5. XÓA FILE LẺ (KHỎI SESSION) ===
    function updatePDFList(pdfFiles) {
        if (!pdfFiles || pdfFiles.length === 0) {
             pdfListDiv.innerHTML = '<p class="info-text">Chưa có file nào trong đoạn chat này.</p>';
             selectedPDFs.clear();
             return;
        }
        pdfListDiv.innerHTML = "";
        
        pdfFiles.forEach(fileName => {
            const div = document.createElement("div");
            div.className = "pdf-item"; 

            const leftSpan = document.createElement("span");
            leftSpan.textContent = fileName; // Không cần checkbox nữa vì mặc định chat với tất cả file trong session
            
            const deleteBtn = document.createElement("button");
            deleteBtn.className = "delete-file-btn";
            deleteBtn.innerHTML = "✕"; 
            deleteBtn.onclick = async () => {
                if (!confirm(`Gỡ file "${fileName}" khỏi cuộc trò chuyện này?`)) return;
                try {
                    await fetch('/remove_file', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            filename: fileName,
                            session_id: currentSessionId // Gửi ID để xóa đúng chỗ
                        })
                    });
                    // Reload list
                    loadUploadedFiles(currentSessionId);
                } catch (e) { console.error("Delete error", e); }
            };

            div.appendChild(leftSpan);
            div.appendChild(deleteBtn);
            pdfListDiv.appendChild(div);
        });
    }

    // === CÁC HÀM CƠ BẢN KHÁC (Sidebar, Chat, Clean...) ===
    
    async function loadSidebarSessions() {
        try {
            const res = await fetch('/get_sessions');
            const sessions = await res.json();
            chatHistoryList.innerHTML = "";
            sessions.forEach(sess => {
                const item = document.createElement("div");
                item.className = `history-item ${sess.session_id === currentSessionId ? 'active' : ''}`;
                const titleSpan = document.createElement("span");
                titleSpan.textContent = sess.title || "Cuộc trò chuyện mới";
                item.appendChild(titleSpan);
                const delBtn = document.createElement("button");
                delBtn.className = "delete-chat-btn";
                delBtn.innerHTML = "×";
                delBtn.onclick = (e) => { e.stopPropagation(); deleteSession(sess.session_id); };
                item.appendChild(delBtn);
                item.onclick = () => switchSession(sess.session_id);
                chatHistoryList.appendChild(item);
            });
        } catch (err) { console.error(err); }
    }

    async function deleteSession(sessionId) {
        if (!confirm("Xóa vĩnh viễn cuộc trò chuyện này?")) return;
        await fetch('/delete_session', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        if (sessionId === currentSessionId) handleNewChat();
        else loadSidebarSessions();
    }

    async function loadChatContent(sessionId) {
        chatMessages.innerHTML = ""; chatHistory = [];
        try {
            const res = await fetch(`/get_history?session_id=${sessionId}`);
            const historyData = await res.json();
            historyData.forEach(msg => {
                addMessageToChat(msg.content.replace(/\n/g, '<br>'), msg.role === 'user' ? 'user' : 'bot');
                chatHistory.push((msg.role === 'user' ? 'User: ' : 'Bot: ') + msg.content);
            });
        } catch (err) { console.error(err); }
    }

    async function sendMessage() {
        const question = userInput.value.trim();
        if (!question) return;
        addMessageToChat(question, "user");
        userInput.value = ""; chatHistory.push(`User: ${question}`);
        thinkingIndicator.style.display = "block";
        try {
            const response = await fetch('/chat', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    session_id: currentSessionId // Chỉ cần gửi session ID, backend tự tìm file
                })
            });
            const data = await response.json();
            chatHistory.push(`Bot: ${data.response}`);
            addMessageToChat(data.response.replace(/\n/g, '<br>'), "bot");
            loadSidebarSessions();
        } catch (error) { addMessageToChat("Lỗi hệ thống.", "bot"); } 
        finally { thinkingIndicator.style.display = "none"; }
    }
    
    function addMessageToChat(message, sender) {
        const div = document.createElement("div"); div.className = `message-bubble ${sender}`;
        div.innerHTML = message; chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function handleCleanData() { // Nút Reset All Hệ Thống
        if (!confirm("CẢNH BÁO: Xóa TOÀN BỘ dữ liệu của TẤT CẢ các phiên chat?")) return;
        try { await fetch('/clean', { method: 'POST' }); location.reload(); } catch(e) {}
    }

    newChatBtn.addEventListener("click", handleNewChat);
    uploadButton.addEventListener("click", handleUpload);
    if (cleanButton) cleanButton.addEventListener("click", handleCleanData);
    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", (e) => { if (e.key === "Enter") sendMessage(); });
    
    init();
});