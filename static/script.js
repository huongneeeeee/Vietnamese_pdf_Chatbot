document.addEventListener("DOMContentLoaded", () => {
    
    // DOM ELEMENTS
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
    let selectedPDFs = new Set(); // Set lưu trữ các file được tick
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
        loadUploadedFiles(currentSessionId); 
    }

    function createNewSessionId() {
        currentSessionId = "sess_" + Math.random().toString(36).substr(2, 9);
        localStorage.setItem("current_session_id", currentSessionId);
        return currentSessionId;
    }

    // === TẢI DANH SÁCH FILE (CÓ CHECKBOX) ===
    async function loadUploadedFiles(sessionId) {
        try {
            const response = await fetch(`/get_uploaded_files?session_id=${sessionId}`);
            const data = await response.json();
            updatePDFList(data.files || []);
        } catch (error) { console.error(error); }
    }

    function updatePDFList(pdfFiles) {
        pdfListDiv.innerHTML = "";
        selectedPDFs.clear(); // Reset danh sách chọn
        
        if (!pdfFiles || pdfFiles.length === 0) {
             pdfListDiv.innerHTML = '<p class="info-text">Chưa có file nào trong đoạn chat này.</p>';
             return;
        }
        
        pdfFiles.forEach(fileName => {
            const div = document.createElement("div");
            div.className = "pdf-item"; 

            // 1. CHECKBOX
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "file-checkbox";
            checkbox.value = fileName;
            checkbox.checked = true; // Mặc định tick
            selectedPDFs.add(fileName); 

            checkbox.addEventListener("change", (e) => {
                if (e.target.checked) selectedPDFs.add(fileName);
                else selectedPDFs.delete(fileName);
            });

            // 2. TÊN FILE
            const span = document.createElement("span");
            span.textContent = fileName;
            span.title = fileName;
            
            // 3. NÚT XÓA
            const deleteBtn = document.createElement("button");
            deleteBtn.className = "delete-file-btn";
            deleteBtn.innerHTML = "✕"; 
            deleteBtn.onclick = async () => {
                if (!confirm(`Gỡ file "${fileName}" khỏi cuộc trò chuyện này?`)) return;
                try {
                    await fetch('/remove_file', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename: fileName, session_id: currentSessionId })
                    });
                    if(selectedPDFs.has(fileName)) selectedPDFs.delete(fileName);
                    loadUploadedFiles(currentSessionId);
                } catch (e) { console.error(e); }
            };

            div.appendChild(checkbox);
            div.appendChild(span);
            div.appendChild(deleteBtn);
            pdfListDiv.appendChild(div);
        });
    }

    // === UPLOAD ===
    async function handleUpload() {
        if (pdfUploader.files.length === 0) return;
        
        const formData = new FormData();
        for (const file of pdfUploader.files) formData.append("pdf_docs", file);
        formData.append("session_id", currentSessionId); 
        
        uploadSpinner.style.display = "block";
        uploadButton.disabled = true; 
        
        try {
            const response = await fetch('/upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.errors && data.errors.length > 0) alert("Lỗi:\n" + data.errors.join("\n"));
            
            updatePDFList(data.processed_files);
            uploadStatus.textContent = `Đã thêm ${data.processed_files.length} file.`;
            uploadStatus.style.color = "green";
        } catch (e) { 
            console.error(e); 
            uploadStatus.textContent = "Lỗi upload.";
            uploadStatus.style.color = "red";
        } finally { 
            uploadSpinner.style.display = "none"; 
            uploadButton.disabled = false;
        }
    }

    // === CHAT ===
    async function sendMessage() {
        const question = userInput.value.trim();
        if (!question) return;

        // Kiểm tra tick chọn file
        if (selectedPDFs.size === 0) {
            alert("Vui lòng tick chọn ít nhất 1 file để hỏi!");
            return;
        }

        addMessageToChat(question, "user");
        userInput.value = ""; 
        chatHistory.push(`User: ${question}`);
        thinkingIndicator.style.display = "block";
        
        try {
            const response = await fetch('/chat', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    session_id: currentSessionId,
                    selected_pdfs: Array.from(selectedPDFs) // Gửi danh sách đã chọn
                })
            });
            const data = await response.json();
            chatHistory.push(`Bot: ${data.response}`);
            addMessageToChat(data.response.replace(/\n/g, '<br>'), "bot");
            loadSidebarSessions();
        } catch (error) { 
            addMessageToChat("Lỗi hệ thống.", "bot"); 
        } finally { 
            thinkingIndicator.style.display = "none"; 
        }
    }
    
    function addMessageToChat(message, sender) {
        const div = document.createElement("div"); div.className = `message-bubble ${sender}`;
        div.innerHTML = message; chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // === SESSION MANAGEMENT ===
    async function handleNewChat() {
        createNewSessionId();
        chatMessages.innerHTML = ""; 
        chatHistory = [];
        pdfUploader.value = "";
        uploadStatus.textContent = "";
        updatePDFList([]); 
        loadSidebarSessions();
    }

    function switchSession(sessionId) {
        if (currentSessionId === sessionId) return; 
        currentSessionId = sessionId;
        localStorage.setItem("current_session_id", currentSessionId);
        loadChatContent(sessionId);
        loadUploadedFiles(sessionId); 
        loadSidebarSessions(); 
    }

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
                
                const delBtn = document.createElement("button");
                delBtn.className = "delete-chat-btn";
                delBtn.innerHTML = "×";
                delBtn.onclick = (e) => { e.stopPropagation(); deleteSession(sess.session_id); };
                
                item.appendChild(titleSpan);
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

    async function handleCleanData() { 
        if (!confirm("CẢNH BÁO: Xóa TOÀN BỘ dữ liệu của TẤT CẢ các phiên chat?")) return;
        try { await fetch('/clean', { method: 'POST' }); location.reload(); } catch(e) {}
    }

    // Event Listeners
    newChatBtn.addEventListener("click", handleNewChat);
    uploadButton.addEventListener("click", handleUpload);
    if (cleanButton) cleanButton.addEventListener("click", handleCleanData);
    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", (e) => { if (e.key === "Enter") sendMessage(); });
    
    init();
});