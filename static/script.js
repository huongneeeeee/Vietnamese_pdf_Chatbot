// Chờ cho toàn bộ nội dung trang được tải
document.addEventListener("DOMContentLoaded", () => {
    
    // === Lấy các phần tử DOM ===
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

    // === Trạng thái (State) của Frontend ===
    let chatHistory = []; // Lưu trữ lịch sử chat dưới dạng chuỗi
    let selectedPDFs = new Set(); // Lưu tên các file PDF được chọn

    // === CÁC HÀM XỬ LÝ ===

    /**
     * Xử lý upload file PDF
     */
    async function handleUpload() {
        if (pdfUploader.files.length === 0) {
            uploadStatus.textContent = "Please select files to upload.";
            return;
        }

        const formData = new FormData();
        for (const file of pdfUploader.files) {
            formData.append("pdf_docs", file);
        }

        uploadSpinner.style.display = "block";
        uploadButton.disabled = true;
        uploadStatus.textContent = "Processing...";

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed with status: ${response.status}`);
            }

            const data = await response.json();
            uploadStatus.textContent = `Success! ${data.processed_files.length} files processed.`;
            updatePDFList(data.processed_files);
        
        } catch (error) {
            console.error("Upload error:", error);
            uploadStatus.textContent = "Upload failed. Please try again.";
        } finally {
            uploadSpinner.style.display = "none";
            uploadButton.disabled = false;
        }
    }

    /**
     * Cập nhật danh sách checkbox PDF
     */
    function updatePDFList(pdfFiles) {
        if (pdfFiles.length === 0) {
            pdfListDiv.innerHTML = '<p class="info-text">No PDFs uploaded yet.</p>';
            return;
        }

        pdfListDiv.innerHTML = ""; // Xóa nội dung cũ
        
        pdfFiles.forEach(fileName => {
            const isChecked = selectedPDFs.has(fileName); // Giữ trạng thái cũ nếu có
            
            const label = document.createElement("label");
            label.className = "pdf-item";
            
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.value = fileName;
            checkbox.checked = true; // Mặc định chọn luôn file mới upload
            
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(` ${fileName}`));
            pdfListDiv.appendChild(label);

            // Cập nhật Set trạng thái
            selectedPDFs.add(fileName); // Mặc định chọn

            // Thêm listener cho checkbox
            checkbox.addEventListener("change", (e) => {
                if (e.target.checked) {
                    selectedPDFs.add(fileName);
                } else {
                    selectedPDFs.delete(fileName);
                }
            });
        });
    }

    /**
     * Gửi tin nhắn chat
     */
    async function sendMessage() {
        const question = userInput.value.trim();
        if (!question) return;

        // Hiển thị tin nhắn người dùng
        addMessageToChat(question, "user");
        userInput.value = ""; // Xóa input

        // Thêm câu hỏi vào lịch sử
        chatHistory.push(`User: ${question}`);

        // Hiển thị "Thinking..."
        thinkingIndicator.style.display = "block";

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    selected_pdfs: Array.from(selectedPDFs), // Chuyển Set thành Array
                    history: chatHistory.join("\n") // Gửi lịch sử
                })
            });

            if (!response.ok) {
                throw new Error(`Chat request failed: ${response.status}`);
            }

            const data = await response.json();
            
            // Thêm câu trả lời của bot vào lịch sử
            chatHistory.push(`Bot: ${data.response}`);
            
            // Hiển thị câu trả lời của bot
            // Dùng innerHTML để render Markdown (đơn giản)
            addMessageToChat(data.response.replace(/\n/g, '<br>'), "bot");

        } catch (error) {
            console.error("Chat error:", error);
            addMessageToChat("Sorry, an error occurred. Please try again.", "bot");
        } finally {
            thinkingIndicator.style.display = "none"; // Ẩn "Thinking..."
        }
    }

    /**
     * Thêm tin nhắn vào giao diện chat
     */
    function addMessageToChat(message, sender) {
        const messageBubble = document.createElement("div");
        messageBubble.className = `message-bubble ${sender}`;
        
        // Dùng innerHTML để render các tag <br> và <strong>
        messageBubble.innerHTML = message; 
        
        chatMessages.appendChild(messageBubble);
        
        // Tự động cuộn xuống dưới
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    /**
     * Xử lý dọn dẹp dữ liệu
     */
    async function handleCleanData() {
        if (!confirm("Are you sure you want to delete all data? This cannot be undone.")) {
            return;
        }

        try {
            const response = await fetch('/clean', { method: 'POST' });
            const data = await response.json();

            if (data.status === 'success') {
                alert("Data cleaned successfully! The page will now reload.");
                location.reload(); // Tải lại trang
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            console.error("Clean error:", error);
            alert("An error occurred while cleaning data.");
        }
    }

    // === GÁN CÁC EVENT LISTENERS ===
    uploadButton.addEventListener("click", handleUpload);
    sendButton.addEventListener("click", sendMessage);
    cleanButton.addEventListener("click", handleCleanData);
    
    // Cho phép gửi bằng phím Enter
    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendMessage();
        }
    });

});