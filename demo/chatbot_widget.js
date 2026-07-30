// chatbot_widget.js
// Self-contained widget logic for Allintos

(function() {
    // Configuration
    const API_URL = 'http://127.0.0.1:8080/api/chat'; // Change this for production
    const SESSION_KEY = 'ag_chatbot_session_id';

    // Widget HTML Structure (injected dynamically so it's a single drop-in JS file)
    const widgetHTML = `
        <div id="ag-chatbot-container">
            <div id="ag-chatbot-window">
                
                <!-- Hero Header Area -->
                <div class="ag-chat-hero">
                    <button class="ag-chat-close" id="ag-chat-close" title="Kapat">
                        <svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                    <h2 class="ag-chat-hero-title">Merhaba! 👋<br>Size nasıl yardımcı olabiliriz?</h2>
                </div>
                
                <!-- Chat Messages Area -->
                <div class="ag-chat-messages-container">
                    <div class="ag-chat-messages" id="ag-chat-messages">
                        <div class="ag-message ag-message-bot">Allintos Bilgi Merkezi'ne hoş geldiniz. Lütfen sorunuzu yazın.</div>
                        
                        <div class="ag-typing-container" id="ag-typing-indicator">
                            <div class="ag-typing-bubble">
                                <div class="ag-typing-dot"></div>
                                <div class="ag-typing-dot"></div>
                                <div class="ag-typing-dot"></div>
                            </div>
                        </div>
                    </div>

                    <div class="ag-chat-input-container">
                        <input type="text" class="ag-chat-input" id="ag-chat-input" placeholder="Mesajınızı yazın..." autocomplete="off">
                        <button class="ag-chat-send" id="ag-chat-send" title="Gönder">
                            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                        </button>
                    </div>
                    <div class="ag-watermark">Powered by <span>Allintos AI</span></div>
                </div>
                
            </div>

            <!-- Floating Toggle Button -->
            <button id="ag-chatbot-toggle" title="Sohbet">
                <svg class="ag-icon-chat" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.029 2 11c0 2.85 1.48 5.391 3.793 7.027L5 22l4.086-2.043C10.015 20.26 10.985 20.4 12 20.4c5.523 0 10-4.029 10-9s-4.477-9-10-9z"/></svg>
            </button>
        </div>
    `;

    // Inject into body when DOM is ready
    function initWidget() {
        if (document.getElementById('ag-chatbot-container')) return; // Already initialized

        // Add HTML
        const wrapper = document.createElement('div');
        wrapper.innerHTML = widgetHTML;
        document.body.appendChild(wrapper.firstElementChild);

        // Bind Elements
        const toggleBtn = document.getElementById('ag-chatbot-toggle');
        const closeBtn = document.getElementById('ag-chat-close');
        const chatWindow = document.getElementById('ag-chatbot-window');
        const chatInput = document.getElementById('ag-chat-input');
        const sendBtn = document.getElementById('ag-chat-send');
        const messagesContainer = document.getElementById('ag-chat-messages');
        const typingIndicator = document.getElementById('ag-typing-indicator');

        // Toggle Chat
        function toggleChat() {
            chatWindow.classList.toggle('ag-open');
            toggleBtn.classList.toggle('ag-open');
            if (chatWindow.classList.contains('ag-open')) {
                chatInput.focus();
                scrollToBottom();
            }
        }

        toggleBtn.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', toggleChat);

        // Send Message Handlers
        sendBtn.addEventListener('click', handleSend);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSend();
            }
        });

        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function getSessionId() {
            return sessionStorage.getItem(SESSION_KEY);
        }

        function setSessionId(id) {
            if (id) {
                sessionStorage.setItem(SESSION_KEY, id);
            }
        }

        function getCurrentTime() {
            const now = new Date();
            return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        }

        function addMessage(text, isUser = false, url = null) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `ag-message ${isUser ? 'ag-message-user' : 'ag-message-bot'}`;
            
            // Text content container
            const textDiv = document.createElement('div');
            textDiv.className = 'ag-message-content';
            textDiv.textContent = text; // Safe against XSS
            msgDiv.appendChild(textDiv);

            if (!isUser && url) {
                const link = document.createElement('a');
                link.className = 'ag-link';
                link.href = url;
                link.target = '_blank';
                link.textContent = 'İlgili Sayfa →';
                msgDiv.appendChild(link);
            }

            // Timestamp
            const timeDiv = document.createElement('div');
            timeDiv.className = 'ag-timestamp';
            timeDiv.textContent = getCurrentTime();
            msgDiv.appendChild(timeDiv);

            // Insert before typing indicator
            messagesContainer.insertBefore(msgDiv, typingIndicator);
            scrollToBottom();
        }

        async function handleSend() {
            const text = chatInput.value.trim();
            if (!text) return;

            // Optimistic UI update
            addMessage(text, true);
            chatInput.value = '';
            chatInput.disabled = true;
            sendBtn.disabled = true;

            // Show typing indicator
            typingIndicator.classList.add('ag-active');
            scrollToBottom();

            // Prepare payload
            const payload = {
                message: text,
                session_id: getSessionId() || null
            };

            try {
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }

                const data = await response.json();
                
                // Save session ID if provided by backend
                if (data.session_id) {
                    setSessionId(data.session_id);
                }

                // Hide typing
                typingIndicator.classList.remove('ag-active');

                // Add bot message
                addMessage(data.reply || "Bir hata oluştu.", false, data.url);

            } catch (error) {
                console.error("Chatbot Error:", error);
                typingIndicator.classList.remove('ag-active');
                addMessage("Üzgünüm, şu anda sunucuya bağlanılamıyor. Lütfen daha sonra tekrar deneyin.", false);
            } finally {
                chatInput.disabled = false;
                sendBtn.disabled = false;
                chatInput.focus();
            }
        }
    }

    // Auto-init if DOM already loaded, else wait
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }

})();
