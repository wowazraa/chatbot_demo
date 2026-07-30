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
                    <div class="ag-chat-hero-logo">ALLINTOS</div>
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
                </div>
                
            </div>

            <!-- Floating Toggle Button -->
            <button id="ag-chatbot-toggle" title="Sohbet">
                <svg class="ag-icon-chat" viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                <svg class="ag-icon-close" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
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
        const chatWindow = document.getElementById('ag-chatbot-window');
        const chatInput = document.getElementById('ag-chat-input');
        const sendBtn = document.getElementById('ag-chat-send');
        const messagesContainer = document.getElementById('ag-chat-messages');
        const typingIndicator = document.getElementById('ag-typing-indicator');

        // Toggle Chat
        toggleBtn.addEventListener('click', () => {
            chatWindow.classList.toggle('ag-open');
            toggleBtn.classList.toggle('ag-open');
            if (chatWindow.classList.contains('ag-open')) {
                chatInput.focus();
                scrollToBottom();
            }
        });

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

        function addMessage(text, isUser = false, url = null) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `ag-message ${isUser ? 'ag-message-user' : 'ag-message-bot'}`;
            msgDiv.textContent = text; // Safe against XSS

            if (!isUser && url) {
                const link = document.createElement('a');
                link.className = 'ag-link';
                link.href = url;
                link.target = '_blank';
                link.textContent = 'İlgili Sayfa →';
                msgDiv.appendChild(document.createElement('br'));
                msgDiv.appendChild(link);
            }

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
