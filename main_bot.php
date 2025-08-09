<?php
/**
 * Chatbot Widget Component
 * Include this file in any PHP page to add the chatbot
 * Usage: <?php include 'includes/chatbot_widget.php'; ?>
 */
?>

<!-- Chatbot Widget HTML -->
<div id="chatbot-widget" class="chatbot-widget">
    <!-- Chatbot Toggle Button -->
    <div id="chatbot-toggle" class="chatbot-toggle">
        <div class="chatbot-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12C2 13.54 2.38 14.99 3.06 16.26L2 22L7.74 20.94C9.01 21.62 10.46 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C10.74 20 9.54 19.65 8.53 19.05L8.19 18.83L4.91 19.69L5.77 16.41L5.55 16.07C4.95 15.06 4.6 13.86 4.6 12.6C4.6 7.91 8.31 4.2 13 4.2C17.69 4.2 21.4 7.91 21.4 12.6C21.4 17.29 17.69 21 13 21H12Z" fill="currentColor"/>
                <path d="M8.5 11.5H15.5V13H8.5V11.5Z" fill="currentColor"/>
                <path d="M8.5 8.5H15.5V10H8.5V8.5Z" fill="currentColor"/>
                <path d="M8.5 14.5H12.5V16H8.5V14.5Z" fill="currentColor"/>
            </svg>
        </div>
        <div class="chatbot-close-icon" style="display: none;">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </div>
        <div class="chatbot-notification" id="chatbot-notification">1</div>
    </div>

    <!-- Chatbot Container -->
    <div id="chatbot-container" class="chatbot-container">
        <div class="chatbot-header">
            <div class="chatbot-title">
                <h4>VeggieBot</h4>
                <p>Speak dirty</p>
            </div>
            <button id="chatbot-minimize" class="chatbot-minimize">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 8H12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </button>
        </div>
        
        <div class="chatbot-messages" id="chatbot-messages">
            <div class="chatbot-message chatbot-bot">
                <div class="chatbot-message-content">
                    Hello?? veggie...
                </div>
            </div>
        </div>
        
        <div class="chatbot-input-container">
            <div class="chatbot-input-wrapper">
                <input 
                    type="text" 
                    class="chatbot-input" 
                    id="chatbot-input" 
                    placeholder="Hi there"
                    maxlength="500"
                >
                <button class="chatbot-send" id="chatbot-send">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M2 21L23 12L2 3V10L17 12L2 14V21Z" fill="currentColor"/>
                    </svg>
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Include CSS and JS -->
<link rel="stylesheet" href="./css/bot_design.css">
<script src="./js/chat.js"></script>