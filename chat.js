// Chatbot Widget JavaScript
class ChatbotWidget {
    constructor() {
        this.isOpen = false;
        this.isLoading = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.hideNotification();
    }

    bindEvents() {
        const toggle = document.getElementById('chatbot-toggle');
        const minimize = document.getElementById('chatbot-minimize');
        const send = document.getElementById('chatbot-send');
        const input = document.getElementById('chatbot-input');

        if (toggle) {
            toggle.addEventListener('click', () => this.toggleChatbot());
        }

        if (minimize) {
            minimize.addEventListener('click', () => this.closeChatbot());
        }

        if (send) {
            send.addEventListener('click', () => this.sendMessage());
        }

        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Close chatbot when clicking outside
        document.addEventListener('click', (e) => {
            const widget = document.getElementById('chatbot-widget');
            if (widget && !widget.contains(e.target) && this.isOpen) {
                this.closeChatbot();
            }
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeChatbot();
            }
        });
    }

    toggleChatbot() {
        if (this.isOpen) {
            this.closeChatbot();
        } else {
            this.openChatbot();
        }
    }

    openChatbot() {
        const container = document.getElementById('chatbot-container');
        const toggle = document.getElementById('chatbot-toggle');
        const chatIcon = toggle?.querySelector('.chatbot-icon');
        const closeIcon = toggle?.querySelector('.chatbot-close-icon');
        const input = document.getElementById('chatbot-input');

        if (container) {
            container.classList.add('chatbot-open');
            this.isOpen = true;
        }

        if (chatIcon) chatIcon.style.display = 'none';
        if (closeIcon) closeIcon.style.display = 'flex';

        this.hideNotification();

        // Focus input after animation
        setTimeout(() => {
            if (input) input.focus();
        }, 300);
    }

    closeChatbot() {
        const container = document.getElementById('chatbot-container');
        const toggle = document.getElementById('chatbot-toggle');
        const chatIcon = toggle?.querySelector('.chatbot-icon');
        const closeIcon = toggle?.querySelector('.chatbot-close-icon');

        if (container) {
            container.classList.remove('chatbot-open');
            this.isOpen = false;
        }

        if (chatIcon) chatIcon.style.display = 'flex';
        if (closeIcon) closeIcon.style.display = 'none';
    }

    async sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input?.value.trim();

        if (!message || this.isLoading) return;

        // Add user message
        this.addMessage(message, true);
        input.value = '';

        // Set loading state
        this.setLoading(true);
        this.addLoadingMessage();

        try {
            const response = await fetch('includes/bot_handler.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }

            // Remove loading and add bot response
            this.removeLoadingMessage();
            this.addMessage(data.reply || 'Sorry, I didn\'t receive a proper response.');

        } catch (error) {
            console.error('Chatbot Error:', error);
            this.removeLoadingMessage();
            this.showError(`Error: ${error.message}. Please try again.`);
        } finally {
            this.setLoading(false);
            if (input) input.focus();
        }
    }

    addMessage(content, isUser = false) {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chatbot-message ${isUser ? 'chatbot-user' : 'chatbot-bot'}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'chatbot-message-content';
        messageContent.textContent = content;
        
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        
        this.scrollToBottom();
    }

    addLoadingMessage() {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-bot';
        messageDiv.id = 'chatbot-loading-message';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'chatbot-message-content chatbot-loading';
        messageContent.innerHTML = `
            Thinking<span class="chatbot-loading-dots">
                <span class="chatbot-loading-dot"></span>
                <span class="chatbot-loading-dot"></span>
                <span class="chatbot-loading-dot"></span>
            </span>
        `;
        
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    removeLoadingMessage() {
        const loadingMessage = document.getElementById('chatbot-loading-message');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    showError(message) {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (!messagesContainer) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'chatbot-error';
        errorDiv.textContent = message;
        messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();
    }

    setLoading(loading) {
        this.isLoading = loading;
        const sendButton = document.getElementById('chatbot-send');
        const input = document.getElementById('chatbot-input');

        if (sendButton) {
            sendButton.disabled = loading;
        }

        if (input) {
            input.disabled = loading;
        }
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chatbot-messages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    showNotification() {
        const notification = document.getElementById('chatbot-notification');
        if (notification) {
            notification.style.display = 'flex';
        }
    }

    hideNotification() {
        const notification = document.getElementById('chatbot-notification');
        if (notification) {
            notification.style.display = 'none';
        }
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatbotWidget();
});

// Global function to show notification (can be called from other scripts)
function showChatbotNotification() {
    const notification = document.getElementById('chatbot-notification');
    if (notification) {
        notification.style.display = 'flex';
    }
}