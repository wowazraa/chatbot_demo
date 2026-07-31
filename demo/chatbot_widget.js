// chatbot_widget.js
// Self-contained widget logic for Allintos

(function() {
    const API_URL = '/api/chat'; // Changed to relative path
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
                    <div class="ag-lang-toggle" id="ag-lang-toggle" style="position: absolute; right: 65px; top: 23px; background: rgba(255,255,255,0.2); border-radius: 12px; padding: 2px; display: flex; gap: 4px; cursor: pointer;">
                        <span class="ag-lang-option active" data-lang="TR" style="padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 10px; color: white;">TR</span>
                        <span class="ag-lang-option" data-lang="EN" style="padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 10px; color: white; opacity: 0.7;">EN</span>
                    </div>
                    <h2 class="ag-chat-hero-title" id="ag-chat-hero-title">Merhaba! 👋<br>Size nasıl yardımcı olabiliriz?</h2>
                </div>
                
                <!-- Chat Messages Area -->
                <div class="ag-chat-messages-container">
                    <div class="ag-chat-messages" id="ag-chat-messages">
                        <div class="ag-message ag-message-bot" id="ag-welcome-msg">Allintos Bilgi Merkezi'ne hoş geldiniz. Lütfen sorunuzu yazın.</div>
                        
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
                    </div>
                </div>
                
            </div>

            <!-- Floating Toggle Button -->
            <button id="ag-chatbot-toggle" title="Sohbet">
                <span style="font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 11px; letter-spacing: 0.5px; line-height: 1; text-align: center;">Allintos</span>
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

        let currentLang = "TR";
        
        // Language Toggle logic
        const langToggle = document.getElementById('ag-lang-toggle');
        if (langToggle) {
            langToggle.addEventListener('click', (e) => {
                if (e.target.classList.contains('ag-lang-option')) {
                    document.querySelectorAll('.ag-lang-option').forEach(el => {
                        el.classList.remove('active');
                        el.style.opacity = '0.7';
                    });
                    e.target.classList.add('active');
                    e.target.style.opacity = '1';
                    
                    const newLang = e.target.getAttribute('data-lang');
                    if (currentLang !== newLang) {
                        currentLang = newLang;
                        sessionStorage.removeItem(SESSION_KEY); // Reset session on language change
                        
                        // Ekrandaki eski mesajları temizle (karşılama mesajı hariç)
                        const messages = document.querySelectorAll('.ag-message');
                        messages.forEach(msg => {
                            if (msg.id !== 'ag-welcome-msg') {
                                msg.remove();
                            }
                        });
                    }
                    
                    // Update static UI texts based on selection
                    const heroTitle = document.getElementById('ag-chat-hero-title');
                    const welcomeMsg = document.getElementById('ag-welcome-msg');
                    const chatInputEl = document.getElementById('ag-chat-input');
                    
                    if (currentLang === 'EN') {
                        if (heroTitle) heroTitle.innerHTML = 'Hello! 👋<br>How can we help you?';
                        if (welcomeMsg) welcomeMsg.textContent = "Welcome to Allintos Knowledge Center. Please type your question.";
                        if (chatInputEl) chatInputEl.placeholder = "Type your message...";
                    } else {
                        if (heroTitle) heroTitle.innerHTML = 'Merhaba! 👋<br>Size nasıl yardımcı olabiliriz?';
                        if (welcomeMsg) welcomeMsg.textContent = "Allintos Bilgi Merkezi'ne hoş geldiniz. Lütfen sorunuzu yazın.";
                        if (chatInputEl) chatInputEl.placeholder = "Mesajınızı yazın...";
                    }
                }
            });
        }

        // Toggle Chat
        function toggleChat() {
            chatWindow.classList.toggle('ag-open');
            toggleBtn.classList.toggle('ag-open');
            if (chatWindow.classList.contains('ag-open')) {
                setTimeout(() => { chatInput.focus(); }, 150);
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
                session_id: getSessionId() || null,
                lang: currentLang
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
                addMessage(data.response_message || "Bir hata oluştu.", false, data.redirect_url);

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
