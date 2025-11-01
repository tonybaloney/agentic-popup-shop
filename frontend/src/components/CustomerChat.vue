<template>
  <div class="chatkit-container">
    <button 
      v-if="!isOpen" 
      class="chat-toggle-btn"
      @click="toggleChat"
      aria-label="Open chat"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    </button>

    <div v-show="isOpen" class="chatkit-wrapper">
      <div class="chatkit-header">
        <h3>Zava Assistant</h3>
        <button @click="toggleChat" class="close-btn" aria-label="Close chat">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div ref="chatkitMount" class="chatkit-widget"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount, watch } from 'vue';
import { createRoot } from 'react-dom/client';
import React from 'react';
import { ChatKit, useChatKit } from '@openai/chatkit-react';

const isOpen = ref(false);
const chatkitMount = ref(null);
let reactRoot = null;

const toggleChat = () => {
  isOpen.value = !isOpen.value;
};

watch(isOpen, async (newValue) => {
  if (newValue && chatkitMount.value && !reactRoot) {
    initializeChatKit();
  }
});

const initializeChatKit = () => {
  if (!chatkitMount.value || reactRoot) return;

  try {
    // Create a React root
    reactRoot = createRoot(chatkitMount.value);

    // Define the React component
    const ChatKitWrapper = () => {
      const { control } = useChatKit({
        api: {
          getClientSecret: async (existing) => {
            if (existing) {
              console.log('Refreshing ChatKit session');
            }

            const response = await fetch('/api/chatkit/session', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionStorage.getItem('authToken')}`
              }
            });

            if (!response.ok) {
              throw new Error('Failed to create ChatKit session');
            }

            const data = await response.json();
            return data.client_secret;
          }
        }
      });

      return React.createElement(ChatKit, {
        control: control,
        className: 'chatkit-instance'
      });
    };

    // Render the React component
    reactRoot.render(React.createElement(ChatKitWrapper));
    console.log('ChatKit initialized successfully');
  } catch (error) {
    console.error('Failed to initialize ChatKit:', error);
    if (chatkitMount.value) {
      chatkitMount.value.innerHTML = '<div style="padding: 20px; text-align: center; color: #e53e3e;"><p>Unable to load chat.</p><p style="font-size: 14px; margin-top: 10px;">Please make sure ChatKit backend is configured.</p></div>';
    }
  }
};

onBeforeUnmount(() => {
  if (reactRoot) {
    reactRoot.unmount();
    reactRoot = null;
  }
});
</script>

<style scoped>
.chatkit-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
}

.chat-toggle-btn {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.chat-toggle-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
}

.chatkit-wrapper {
  width: 380px;
  height: 600px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chatkit-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.chatkit-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.chatkit-widget {
  flex: 1;
  overflow: hidden;
}

@media (max-width: 768px) {
  .chatkit-wrapper {
    width: calc(100vw - 40px);
    height: calc(100vh - 100px);
    max-width: 380px;
  }
}
</style>
