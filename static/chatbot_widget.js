// chatbot_widget.js
// Self-contained widget logic for Allintos

(function() {
    const translations = {
        tr: {
            heroTitle: 'Merhaba!<br>Size nasıl yardımcı olabiliriz?',
            welcomeMessage: "Allintos Bilgi Merkezi'ne hoş geldiniz. Lütfen sorunuzu yazın.",
            linkRelatedPage: 'İlgili Sayfa →',
            inputPlaceholder: 'Mesajınızı yazın...',
            closeButtonTitle: 'Kapat',
            refreshButtonTitle: 'Yeni sohbet',
            refreshButtonAriaLabel: 'Oturumu yenile ve yeni sohbet başlat',
            sendButtonTitle: 'Gönder',
            toggleButtonTitle: 'Sohbet',
            toggleBrand: 'ALLINTOS',
            closeButtonAriaLabel: 'Sohbet penceresini kapat',
            sendButtonAriaLabel: 'Mesajı gönder',
            toggleButtonAriaLabel: 'Sohbet penceresini aç',
            typingIndicatorAriaLabel: 'Yanıt yazılıyor',
            errorGeneric: 'Bir hata oluştu.',
            errorConnection:
                'Üzgünüm, şu anda sunucuya bağlanılamıyor. Lütfen daha sonra tekrar deneyin.',
        },
        en: {
            heroTitle: 'Hello!<br>How can we help you?',
            welcomeMessage:
                'Welcome to Allintos Knowledge Center. Please type your question.',
            linkRelatedPage: 'Related Page →',
            inputPlaceholder: 'Type your message...',
            closeButtonTitle: 'Close',
            refreshButtonTitle: 'New chat',
            refreshButtonAriaLabel: 'Refresh session and start a new chat',
            sendButtonTitle: 'Send',
            toggleButtonTitle: 'Open chat',
            toggleBrand: 'ALLINTOS',
            closeButtonAriaLabel: 'Close chat window',
            sendButtonAriaLabel: 'Send message',
            toggleButtonAriaLabel: 'Open chat window',
            typingIndicatorAriaLabel: 'Typing a reply',
            errorGeneric: 'An error occurred.',
            errorConnection:
                'Sorry, we cannot connect to the server right now. Please try again later.',
        },
    };

    const INACTIVITY_MS = 20 * 60 * 1000;
    const SESSION_KEY = 'ag_chatbot_session_id';
    const STATE_KEY = 'ag_chatbot_state';

    function getWidgetScriptElement() {
        return document.querySelector('script[src*="chatbot_widget.js"]');
    }

    function normalizeLanguage(value) {
        if (!value) return null;
        const v = String(value).trim().toLowerCase();
        if (v === 'en' || v.startsWith('en-')) return 'en';
        if (v === 'tr' || v.startsWith('tr-')) return 'tr';
        return null;
    }

    /** Sinem: script data-language; Allintos: html lang. Çelişkide sayfa dili (html) kazanır. */
    function resolveLanguage() {
        const scriptEl = getWidgetScriptElement();
        const scriptLang = normalizeLanguage(scriptEl?.dataset?.language);
        const htmlLang = normalizeLanguage(document.documentElement.lang);
        if (htmlLang && scriptLang && htmlLang !== scriptLang) {
            return htmlLang;
        }
        return scriptLang || htmlLang || 'tr';
    }

    function readStateJson() {
        try {
            const raw = sessionStorage.getItem(STATE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            console.warn('[Chatbot] state parse error', e);
            return null;
        }
    }

    function isStateExpired(state) {
        if (!state || typeof state.lastActivityAt !== 'number') {
            return false;
        }
        return Date.now() - state.lastActivityAt > INACTIVITY_MS;
    }

    function loadState() {
        const state = readStateJson();
        if (!state) {
            return null;
        }
        if (isStateExpired(state)) {
            sessionStorage.removeItem(STATE_KEY);
            sessionStorage.removeItem(SESSION_KEY);
            return null;
        }
        return state;
    }

    function saveState(state) {
        sessionStorage.setItem(STATE_KEY, JSON.stringify(state));
    }

    function clearStorage() {
        sessionStorage.removeItem(SESSION_KEY);
        sessionStorage.removeItem(STATE_KEY);
    }

    let backendUrl = 'http://127.0.0.1:8082';
    const scriptEl = getWidgetScriptElement();
    if (scriptEl && scriptEl.src) {
        try {
            backendUrl = new URL(scriptEl.src).origin;
        } catch (e) {
            console.error('URL parse hatası', e);
        }
    }
    const API_URL = backendUrl + '/api/chat';

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = backendUrl + '/demo/chatbot_widget.css';
    document.head.appendChild(link);

    function buildWidgetHTML(lang) {
        const text = translations[lang] || translations.tr;
        return `
        <div id="ag-chatbot-container">
            <div id="ag-chatbot-window">

                <div class="ag-chat-hero">
                    <button class="ag-chat-refresh" id="ag-chat-refresh"
                        type="button"
                        title="${text.refreshButtonTitle}"
                        aria-label="${text.refreshButtonAriaLabel}">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a9 9 0 1 1-2.64-6.36" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><polyline points="21 3 21 9 15 9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </button>
                    <button class="ag-chat-close" id="ag-chat-close"
                        title="${text.closeButtonTitle}"
                        aria-label="${text.closeButtonAriaLabel}">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                    <h2 class="ag-chat-hero-title" id="ag-chat-hero-title">${text.heroTitle}</h2>
                </div>

                <div class="ag-chat-messages-container">
                    <div class="ag-chat-messages" id="ag-chat-messages">
                        <div class="ag-message ag-message-bot" id="ag-welcome-msg">${text.welcomeMessage}</div>

                        <div class="ag-typing-container" id="ag-typing-indicator"
                            aria-label="${text.typingIndicatorAriaLabel}" aria-live="polite">
                            <div class="ag-typing-bubble">
                                <div class="ag-typing-dot"></div>
                                <div class="ag-typing-dot"></div>
                                <div class="ag-typing-dot"></div>
                            </div>
                        </div>
                    </div>

                    <div class="ag-chat-input-container">
                        <input type="text" class="ag-chat-input" id="ag-chat-input"
                            placeholder="${text.inputPlaceholder}" autocomplete="off">
                        <button class="ag-chat-send" id="ag-chat-send"
                            title="${text.sendButtonTitle}"
                            aria-label="${text.sendButtonAriaLabel}">
                            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                        </button>
                    </div>
                </div>

            </div>

            <button id="ag-chatbot-toggle"
                title="${text.toggleButtonTitle}"
                aria-label="${text.toggleButtonAriaLabel}">
                <span class="ag-toggle-brand" id="ag-toggle-brand">${text.toggleBrand}</span>
            </button>
        </div>
    `;
    }

    function applyTranslations(lang) {
        const t = translations[lang] || translations.tr;
        const heroTitle = document.getElementById('ag-chat-hero-title');
        const welcomeMsg = document.getElementById('ag-welcome-msg');
        const chatInputEl = document.getElementById('ag-chat-input');
        const closeBtn = document.getElementById('ag-chat-close');
        const refreshBtn = document.getElementById('ag-chat-refresh');
        const sendBtn = document.getElementById('ag-chat-send');
        const toggleBtn = document.getElementById('ag-chatbot-toggle');
        const typingIndicator = document.getElementById('ag-typing-indicator');

        if (heroTitle) heroTitle.innerHTML = t.heroTitle;
        if (welcomeMsg) welcomeMsg.textContent = t.welcomeMessage;
        if (chatInputEl) chatInputEl.placeholder = t.inputPlaceholder;
        if (closeBtn) {
            closeBtn.title = t.closeButtonTitle;
            closeBtn.setAttribute('aria-label', t.closeButtonAriaLabel);
        }
        if (refreshBtn) {
            refreshBtn.title = t.refreshButtonTitle;
            refreshBtn.setAttribute('aria-label', t.refreshButtonAriaLabel);
        }
        if (sendBtn) {
            sendBtn.title = t.sendButtonTitle;
            sendBtn.setAttribute('aria-label', t.sendButtonAriaLabel);
        }
        if (toggleBtn) {
            toggleBtn.title = t.toggleButtonTitle;
            toggleBtn.setAttribute('aria-label', t.toggleButtonAriaLabel);
        }
        const toggleBrand = document.getElementById('ag-toggle-brand');
        if (toggleBrand) toggleBrand.textContent = t.toggleBrand;
        if (typingIndicator) {
            typingIndicator.setAttribute('aria-label', t.typingIndicatorAriaLabel);
        }
    }

    function initWidget() {
        if (document.getElementById('ag-chatbot-container')) return;

        let currentLang = resolveLanguage();

        const wrapper = document.createElement('div');
        wrapper.innerHTML = buildWidgetHTML(currentLang);
        document.body.appendChild(wrapper.firstElementChild);

        const toggleBtn = document.getElementById('ag-chatbot-toggle');
        const closeBtn = document.getElementById('ag-chat-close');
        const refreshBtn = document.getElementById('ag-chat-refresh');
        const chatWindow = document.getElementById('ag-chatbot-window');
        const chatInput = document.getElementById('ag-chat-input');
        const sendBtn = document.getElementById('ag-chat-send');
        const messagesContainer = document.getElementById('ag-chat-messages');
        const typingIndicator = document.getElementById('ag-typing-indicator');

        let chatState = {
            lastActivityAt: Date.now(),
            lang: currentLang,
            messages: [],
        };

        function freshState() {
            return {
                lastActivityAt: Date.now(),
                lang: currentLang,
                messages: [],
            };
        }

        function clearDomMessages() {
            document.querySelectorAll('.ag-message').forEach(msg => {
                if (msg.id !== 'ag-welcome-msg') {
                    msg.remove();
                }
            });
        }

        function resetSession() {
            typingIndicator.classList.remove('ag-active');
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.value = '';
            clearAll();
            const welcomeMsg = document.getElementById('ag-welcome-msg');
            const t = translations[currentLang] || translations.tr;
            if (welcomeMsg) {
                welcomeMsg.textContent = t.welcomeMessage;
            }
            scrollToBottom();
            chatInput.focus();
        }

        function clearAll() {
            clearStorage();
            chatState = freshState();
            clearDomMessages();
        }

        function touchActivity() {
            chatState.lastActivityAt = Date.now();
            chatState.lang = currentLang;
            saveState(chatState);
        }

        function checkInactivity() {
            const raw = readStateJson();
            if (raw && isStateExpired(raw)) {
                clearAll();
                return true;
            }
            return false;
        }

        function restoreFromStorage() {
            const stored = loadState();
            if (!stored) {
                chatState = freshState();
                return;
            }
            if (stored.lang && stored.lang !== currentLang) {
                clearAll();
                return;
            }
            chatState = {
                lastActivityAt: stored.lastActivityAt || Date.now(),
                lang: stored.lang || currentLang,
                messages: Array.isArray(stored.messages) ? stored.messages : [],
            };
            chatState.messages.forEach(m => {
                addMessage(m.text, m.role === 'user', m.url || null, {
                    skipPersist: true,
                    ts: m.ts || null,
                });
            });
        }

        function syncLanguageFromHost() {
            const nextLang = resolveLanguage();
            if (nextLang === currentLang) return;

            currentLang = nextLang;
            applyTranslations(currentLang);
            clearAll();
        }

        function watchHostLanguageChanges() {
            if (typeof MutationObserver === 'undefined') return;

            const observer = new MutationObserver(() => {
                syncLanguageFromHost();
            });

            observer.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['lang'],
            });

            const widgetScript = getWidgetScriptElement();
            if (widgetScript) {
                observer.observe(widgetScript, {
                    attributes: true,
                    attributeFilter: ['data-language'],
                });
            }
        }

        function toggleChat() {
            syncLanguageFromHost();

            chatWindow.classList.toggle('ag-open');
            toggleBtn.classList.toggle('ag-open');
            if (chatWindow.classList.contains('ag-open')) {
                setTimeout(() => { chatInput.focus(); }, 150);
                scrollToBottom();
            }
        }

        toggleBtn.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', toggleChat);
        refreshBtn.addEventListener('click', resetSession);

        sendBtn.addEventListener('click', handleSend);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSend();
            }
        });

        watchHostLanguageChanges();

        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function getSessionId() {
            return sessionStorage.getItem(SESSION_KEY);
        }

        function setSessionId(id) {
            if (id) {
                sessionStorage.setItem(SESSION_KEY, String(id));
            }
        }

        function getCurrentTime() {
            const now = new Date();
            return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        }

        function cleanBotReplyText(text) {
            if (!text) return text;
            return text
                .replace(/https?:\/\/\S+/gi, '')
                .replace(/\s*İlgili forma buradan ulaşabilirsiniz\s*:?\s*$/i, '')
                .replace(/\s*(buradan ulaşabilirsiniz|devam etmek için|you can proceed here|you may be redirected to)\s*:?\s*$/i, '')
                .replace(/\s{2,}/g, ' ')
                .replace(/\s+([.,;:])\s*/g, '$1 ')
                .trim();
        }

        function addMessage(messageText, isUser = false, url = null, options = {}) {
            const { skipPersist = false, ts = null } = options;
            const t = translations[currentLang] || translations.tr;
            const displayText = isUser ? messageText : cleanBotReplyText(messageText);
            const msgDiv = document.createElement('div');
            msgDiv.className = `ag-message ${isUser ? 'ag-message-user' : 'ag-message-bot'}`;

            const textDiv = document.createElement('div');
            textDiv.className = 'ag-message-content';
            textDiv.textContent = displayText;
            msgDiv.appendChild(textDiv);

            if (!isUser && url) {
                const linkEl = document.createElement('a');
                linkEl.className = 'ag-link';
                linkEl.href = url;
                linkEl.target = '_blank';
                linkEl.rel = 'noopener noreferrer';
                linkEl.textContent = t.linkRelatedPage;
                msgDiv.appendChild(linkEl);
            }

            const timeDiv = document.createElement('div');
            timeDiv.className = 'ag-timestamp';
            const displayTs = ts || getCurrentTime();
            timeDiv.textContent = displayTs;
            msgDiv.appendChild(timeDiv);

            messagesContainer.insertBefore(msgDiv, typingIndicator);
            scrollToBottom();

            if (!skipPersist) {
                chatState.messages.push({
                    role: isUser ? 'user' : 'bot',
                    text: displayText,
                    url: url || null,
                    ts: displayTs,
                });
                touchActivity();
            }
        }

        async function handleSend() {
            syncLanguageFromHost();
            checkInactivity();

            const t = translations[currentLang] || translations.tr;
            const messageText = chatInput.value.trim();
            if (!messageText) return;

            touchActivity();
            addMessage(messageText, true);
            chatInput.value = '';
            chatInput.disabled = true;
            sendBtn.disabled = true;

            typingIndicator.classList.add('ag-active');
            scrollToBottom();

            const sessionRaw = getSessionId();
            const payload = {
                message: messageText,
                session_id: sessionRaw ? parseInt(sessionRaw, 10) : null,
                lang: currentLang,
            };

            try {
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }

                const data = await response.json();

                if (data.session_id) {
                    setSessionId(data.session_id);
                }

                typingIndicator.classList.remove('ag-active');
                addMessage(data.reply || t.errorGeneric, false, data.url);
            } catch (error) {
                console.error('Chatbot Error:', error);
                typingIndicator.classList.remove('ag-active');
                addMessage(t.errorConnection, false);
            } finally {
                chatInput.disabled = false;
                sendBtn.disabled = false;
                chatInput.focus();
            }
        }

        restoreFromStorage();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }
})();
