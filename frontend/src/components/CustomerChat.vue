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

    <div v-show="isOpen" class="chatkit-wrapper" :class="{ 'maximized': isMaximized }">
      <div class="chatkit-header">
        <h3>Zava Assistant</h3>
        <div class="header-buttons">
          <button @click="toggleMaximize" class="maximize-btn" :aria-label="isMaximized ? 'Minimize chat' : 'Maximize chat'">
            <svg v-if="!isMaximized" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path>
            </svg>
          </button>
          <button @click="toggleChat" class="close-btn" aria-label="Close chat">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
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
import { authStore } from '../stores/auth';

const isOpen = ref(false);
const isMaximized = ref(false);
const chatkitMount = ref(null);
let reactRoot = null;

const toggleChat = () => {
  isOpen.value = !isOpen.value;
};

const toggleMaximize = () => {
  isMaximized.value = !isMaximized.value;
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
          url: '/api/chatkit',
          domainKey: import.meta.env.VITE_CHATKIT_DOMAIN_KEY || '',
          fetch: async (input, init) => {
            const token = authStore.getToken();

            const headers = new Headers(init?.headers || {});
            if (token) {
              headers.set('Authorization', `Bearer ${token}`);
            }

            const modifiedInit = {
              ...init,
              headers,
            };

            return fetch(input, modifiedInit);
          },
        },
        startScreen: {
          greeting: `Hello ${authStore.user?.name || 'Guest'}, what can I help you with today?`,
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
  transition: all 0.3s ease;
}

.chatkit-wrapper.maximized {
  width: calc(100vw - 40px);
  height: calc(100vh - 40px);
  max-width: none;
  border-radius: 12px;
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

.header-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.maximize-btn,
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

.maximize-btn:hover,
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
