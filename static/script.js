document.addEventListener("DOMContentLoaded", () => {
    
    // === 1. SỬA LỖI ID Ở ĐÂY (pdf-uploader -> pdf_docs) ===
    const pdfUploader = document.getElementById("pdf_docs"); 
    const uploadButton = document.getElementById("upload-button");
    const uploadSpinner = document.getElementById("upload-spinner");
    const uploadStatus = document.getElementById("upload-status");
    const pdfListDiv = document.getElementById("pdf-list");

    const chatMessages = document.getElementById("chat-messages");
    const userInput = document.getElementById("user-input");
    const sendButton = document.getElementById("send-button");
    const thinkingIndicator = document.getElementById("thinking-indicator");
    const cleanButton = document.getElementById("clean-button");

    // State
    let chatHistory = ""; 
    let selectedPDFs = new Set(); 
    let processedFiles = [];

    // === UPLOAD ===
    async function handleUpload(e) {
        // Ngăn chặn hành vi mặc định nếu nút nằm trong form
        if(e) e.preventDefault();

        if (!pdfUploader || pdfUploader.files.length === 0) {
            alert("Vui lòng chọn file!");
            return;
        }

        const formData = new FormData();
        for (const file of pdfUploader.files) {
            formData.append("pdf_docs", file);
        }

        // Hiển thị trạng thái đang xử lý
        if(uploadSpinner) uploadSpinner.style.display = "block";
        if(uploadButton) uploadButton.disabled = true;
        if(uploadStatus) {
            uploadStatus.textContent = "Đang xử lý...";
            uploadStatus.style.color = "#333";
        }

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error(`Upload failed: ${response.status}`);

            const data = await response.json();
            processedFiles = data.processed_files;
            
            if(uploadStatus) {
                uploadStatus.innerHTML = `<strong>Thành công:</strong> ${processedFiles.length} file.`;
                uploadStatus.style.color = "#005A9C";
            }
            
            updatePDFList(processedFiles);
        
        } catch (error) {
            console.error("Upload error:", error);
            if(uploadStatus) {
                uploadStatus.textContent = "Lỗi upload file!";
                uploadStatus.style.color = "#e74c3c";
            }
        } finally {
            if(uploadSpinner) uploadSpinner.style.display = "none";
            if(uploadButton) uploadButton.disabled = false;
            if(pdfUploader) pdfUploader.value = ""; // Reset input
        }
    }

    // === UPDATE LIST (Checkbox + Delete) ===
    function updatePDFList(files) {
        if(!pdfListDiv) return;
        pdfListDiv.innerHTML = "";
        
        if (!files || files.length === 0) {
            pdfListDiv.innerHTML = '<p class="info-text">Chưa có file nào.</p>';
            return;
        }

        files.forEach(fileName => {
            const div = document.createElement("div");
            div.className = "pdf-item";

            const label = document.createElement("label");
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.value = fileName;
            checkbox.checked = true; 
            selectedPDFs.add(fileName);

            checkbox.addEventListener("change", (e) => {
                if (e.target.checked) selectedPDFs.add(fileName);
                else selectedPDFs.delete(fileName);
            });

            const span = document.createElement("span");
            span.textContent = fileName;
            span.title = fileName;

            label.appendChild(checkbox);
            label.appendChild(span);

            const delBtn = document.createElement("button");
            delBtn.className = "delete-btn";
            delBtn.innerHTML = '<i class="fas fa-times"></i>';
            delBtn.onclick = () => deleteFile(fileName);

            div.appendChild(label);
            div.appendChild(delBtn);
            pdfListDiv.appendChild(div);
        });
    }

    // === DELETE FILE ===
    async function deleteFile(filename) {
        if(!confirm(`Bạn muốn xóa file "${filename}"?`)) return;

        try {
            const res = await fetch('/delete_file', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ filename: filename })
            });
            const data = await res.json();
            if(data.status === 'success') {
                processedFiles = processedFiles.filter(f => f !== filename);
                selectedPDFs.delete(filename);
                updatePDFList(processedFiles);
            } else {
                alert("Lỗi xóa file: " + data.message);
            }
        } catch(err) {
            console.error(err);
            alert("Lỗi kết nối!");
        }
    }

    // === CHAT ===
    async function sendMessage(text = null) {
        const question = text || userInput.value.trim();
        if (!question) return;

        const activeFiles = Array.from(selectedPDFs);
        if (activeFiles.length === 0 && processedFiles.length > 0) {
            alert("Vui lòng tick chọn ít nhất 1 file để chat!");
            return;
        }

        addMessageToChat(question, "user");
        if(!text && userInput) userInput.value = "";
        
        if(thinkingIndicator) thinkingIndicator.style.display = "block";
        scrollToBottom();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    selected_pdfs: activeFiles,
                    history: chatHistory
                })
            });

            const data = await response.json();
            chatHistory += `User: ${question}\nBot: ${data.response}\n`;
            addBotResponse(data);

        } catch (error) {
            console.error("Chat error:", error);
            addMessageToChat("Lỗi kết nối đến server.", "bot", true);
        } finally {
            if(thinkingIndicator) thinkingIndicator.style.display = "none";
        }
    }

    function addMessageToChat(text, sender, isError = false) {
        if(!chatMessages) return;
        const div = document.createElement("div");
        div.className = `message-bubble ${sender}`;
        if(isError) div.style.color = "#e74c3c";
        div.innerHTML = formatText(text);
        chatMessages.appendChild(div);
        scrollToBottom();
    }

    function addBotResponse(data) {
        if(!chatMessages) return;
        let content = formatText(data.response);

        if (data.sources && data.sources.length > 0) {
            const unique = [...new Set(data.sources.map(s => s.file + (s.page ? ` (Trang ${s.page})` : '')))];
            content += `<div class="source-box"><i class="fas fa-book-open"></i> <strong>Nguồn:</strong> ${unique.join(', ')}</div>`;
        }

        let suggestionsHtml = '';
        if (data.followup) {
            const lines = data.followup.split('\n');
            lines.forEach(line => {
                const clean = line.replace(/^-\s*/, '').trim();
                if(clean) {
                    suggestionsHtml += `<button class="suggestion-btn" onclick="window.triggerSuggestion('${clean.replace(/'/g, "\\'")}')">${clean}</button>`;
                }
            });
        }
        if(suggestionsHtml) {
            content += `<div class="follow-up-container">${suggestionsHtml}</div>`;
        }

        const div = document.createElement("div");
        div.className = "message-bubble bot";
        div.innerHTML = content;
        chatMessages.appendChild(div);
        scrollToBottom();
    }

    function formatText(text) {
        if(!text) return "";
        let formatted = text.replace(/\n/g, '<br>');
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
        return formatted;
    }

    function scrollToBottom() {
        if(chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    window.triggerSuggestion = function(text) {
        sendMessage(text);
    };

    if(cleanButton) {
        cleanButton.addEventListener("click", async () => {
            if (!confirm("Bạn có chắc muốn xóa TOÀN BỘ dữ liệu?")) return;
            try {
                const res = await fetch('/clean', { method: 'POST' });
                const d = await res.json();
                if(d.status === 'success') {
                    alert("Dữ liệu đã được xóa.");
                    location.reload();
                }
            } catch(e) { alert("Lỗi clean data"); }
        });
    }

    if(uploadButton) {
        uploadButton.addEventListener("click", (e) => {
            handleUpload(e);
        });
    }
    
    if(sendButton) sendButton.addEventListener("click", () => sendMessage());
    
    if(userInput) {
        userInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendMessage();
        });
    }
});