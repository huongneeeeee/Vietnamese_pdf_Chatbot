document.addEventListener("DOMContentLoaded", () => {
    
    // === DOM ELEMENTS ===
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

    // === STATE ===
    let chatHistory = []; 
    let selectedPDFs = new Set();
    let currentSessionId = null; 

    // === INIT FUNCTION ===
    function init() {
        const savedSession = localStorage.getItem("current_session_id");
        if (savedSession) {
            currentSessionId = savedSession;
        } else {
            createNewSessionId(); 
        }

        loadSidebarSessions(); 
        loadChatContent(currentSessionId);
        
        // MỚI: Tải danh sách file upload khi vào trang
        loadUploadedFiles(); 
    }

    function createNewSessionId() {
        currentSessionId = "sess_" + Math.random().toString(36).substr(2, 9);
        localStorage.setItem("current_session_id", currentSessionId);
        return currentSessionId;
    }

    // === MỚI: TẢI DANH SÁCH FILE TỪ SERVER ===
    async function loadUploadedFiles() {
        try {
            const response = await fetch('/get_uploaded_files');
            const data = await response.json();
            if (data.files) {
                updatePDFList(data.files);
            }
        } catch (error) {
            console.error("Failed to load uploaded files:", error);
        }
    }

    // === LOGIC: SIDEBAR SESSIONS ===
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
                delBtn.onclick = (e) => {
                    e.stopPropagation(); 
                    deleteSession(sess.session_id);
                };
                item.appendChild(delBtn);

                item.onclick = () => switchSession(sess.session_id);
                
                chatHistoryList.appendChild(item);
            });
        } catch (err) {
            console.error("Error loading sessions:", err);
        }
    }

    async function handleNewChat() {
        createNewSessionId();
        chatMessages.innerHTML = ""; 
        chatHistory = []; 
        loadSidebarSessions(); 
    }

    // === LOGIC: CLEAN / RESET ALL ===
    async function handleCleanData() {
        const isConfirmed = confirm("CẢNH BÁO: Bạn có chắc chắn muốn xoá tất cả dữ liệu?\n\nHành động này sẽ:\n- Xóa toàn bộ lịch sử chat.\n- Xóa toàn bộ file đã upload.\n- Không thể hoàn tác.");

        if (!isConfirmed) return;

        try {
            const response = await fetch('/clean', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: currentSessionId })
            });
            const data = await response.json();

            if (data.status === 'success') {
                alert("Đã xóa dữ liệu thành công! Trang web sẽ được tải lại.");
                location.reload(); 
            } else {
                alert(`Lỗi: ${data.message}`);
            }
        } catch (error) {
            console.error("Clean error:", error);
            alert("Đã xảy ra lỗi khi kết nối với server.");
        }
    }

    // === LOGIC: UPLOAD ===
    async function handleUpload() {
        if (pdfUploader.files.length === 0) return;
        const formData = new FormData();
        for (const file of pdfUploader.files) formData.append("pdf_docs", file);
        
        uploadSpinner.style.display = "block";
        uploadButton.disabled = true; 
        
        try {
            const response = await fetch('/upload', { method: 'POST', body: formData });
            const data = await response.json();
            
            if (data.errors && data.errors.length > 0) {
                alert("Một số file bị lỗi:\n" + data.errors.join("\n"));
            }
            updatePDFList(data.processed_files);
            uploadStatus.textContent = `Đã xử lý xong ${data.processed_files.length} file.`;
        } catch (e) { 
            console.error(e); 
            uploadStatus.textContent = "Lỗi upload.";
        }
        finally { 
            uploadSpinner.style.display = "none"; 
            uploadButton.disabled = false;
        }
    }

    // === LOGIC: RENDER DANH SÁCH FILE ===
    function updatePDFList(pdfFiles) {
        if (!pdfFiles || pdfFiles.length === 0) {
             pdfListDiv.innerHTML = '<p class="info-text">Chưa có file nào.</p>';
             selectedPDFs.clear();
             return;
        }
        pdfListDiv.innerHTML = "";
        
        pdfFiles.forEach(fileName => {
            const div = document.createElement("div");
            div.className = "pdf-item"; 

            const leftSpan = document.createElement("span");
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox"; 
            checkbox.value = fileName; 
            checkbox.checked = true; 
            
            checkbox.addEventListener("change", (e) => {
                if (e.target.checked) selectedPDFs.add(fileName);
                else selectedPDFs.delete(fileName);
            });
            
            leftSpan.appendChild(checkbox);
            leftSpan.appendChild(document.createTextNode(` ${fileName}`));
            
            const deleteBtn = document.createElement("button");
            deleteBtn.className = "delete-file-btn";
            deleteBtn.innerHTML = "✕"; 
            deleteBtn.onclick = async () => {
                if (!confirm(`Bạn muốn hủy file "${fileName}"?`)) return;
                try {
                    await fetch('/remove_file', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename: fileName })
                    });
                    selectedPDFs.delete(fileName);
                    div.remove();
                    if (pdfListDiv.children.length === 0) {
                        pdfListDiv.innerHTML = '<p class="info-text">Chưa có file nào.</p>';
                    }
                } catch (e) { console.error("Delete error", e); }
            };

            div.appendChild(leftSpan);
            div.appendChild(deleteBtn);
            pdfListDiv.appendChild(div);
            selectedPDFs.add(fileName);
        });
    }

    // === LOGIC: CHUYỂN SESSION, XÓA SESSION, LOAD CHAT, GỬI TIN ===
    function switchSession(sessionId) {
        if (currentSessionId === sessionId) return; 
        currentSessionId = sessionId;
        localStorage.setItem("current_session_id", currentSessionId);
        loadChatContent(sessionId);
        loadSidebarSessions(); 
    }

    async function deleteSession(sessionId) {
        if (!confirm("Bạn có chắc muốn xóa cuộc trò chuyện này?")) return;
        
        await fetch('/delete_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });

        if (sessionId === currentSessionId) {
            handleNewChat();
        } else {
            loadSidebarSessions();
        }
    }

    async function loadChatContent(sessionId) {
        chatMessages.innerHTML = ""; 
        chatHistory = []; 
        
        try {
            const res = await fetch(`/get_history?session_id=${sessionId}`);
            const historyData = await res.json();

            historyData.forEach(msg => {
                addMessageToChat(msg.content.replace(/\n/g, '<br>'), msg.role === 'user' ? 'user' : 'bot');
                const rolePrefix = msg.role === 'user' ? 'User: ' : 'Bot: ';
                chatHistory.push(rolePrefix + msg.content);
            });
        } catch (err) {
            console.error("Failed to load chat content:", err);
        }
    }

    async function sendMessage() {
        const question = userInput.value.trim();
        if (!question) return;

        addMessageToChat(question, "user");
        userInput.value = ""; 
        chatHistory.push(`User: ${question}`);
        thinkingIndicator.style.display = "block";

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    selected_pdfs: Array.from(selectedPDFs),
                    history: chatHistory.join("\n"),
                    session_id: currentSessionId 
                })
            });

            const data = await response.json();
            
            chatHistory.push(`Bot: ${data.response}`);
            addMessageToChat(data.response.replace(/\n/g, '<br>'), "bot");

            loadSidebarSessions(); // Reload tiêu đề nếu là chat mới

        } catch (error) {
            console.error("Chat error:", error);
            addMessageToChat("Sorry, an error occurred.", "bot");
        } finally {
            thinkingIndicator.style.display = "none";
        }
    }
    
    function addMessageToChat(message, sender) {
        const messageBubble = document.createElement("div");
        messageBubble.className = `message-bubble ${sender}`;
        messageBubble.innerHTML = message; 
        chatMessages.appendChild(messageBubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // === EVENTS ===
    newChatBtn.addEventListener("click", handleNewChat);
    uploadButton.addEventListener("click", handleUpload);
    if (cleanButton) cleanButton.addEventListener("click", handleCleanData);
    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", (e) => { if (e.key === "Enter") sendMessage(); });
    
    init();
});