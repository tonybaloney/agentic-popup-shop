<template>
  <div class="chat-window-overlay" @click="closeChat">
    <div class="chat-window" @click.stop>
      <div class="chat-header">
        <h3>Chat with Zava Shop AI</h3>
        <button @click="closeChat" class="close-button">&times;</button>
      </div>
      
      <div class="chat-messages" ref="messagesContainer">
        <div v-for="(msg, index) in messages" :key="index" class="message" :class="msg.role">
          <div class="message-content">
            <span class="message-text">{{ msg.content }}</span>
            <span v-if="msg.isStreaming" class="typing-indicator">▊</span>
          </div>
        </div>
        
        <div v-if="isWaiting" class="message assistant">
          <div class="message-content">
            <span class="typing-dots">
              <span></span><span></span><span></span>
            </span>
          </div>
        </div>
      </div>
      
      <div class="chat-input-container">
        <textarea
          v-model="inputMessage"
          @keydown.enter.prevent="sendMessage"
          placeholder="Type your message..."
          rows="2"
          :disabled="isStreaming"
        ></textarea>
        <button @click="sendMessage" :disabled="!inputMessage.trim() || isStreaming">
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { authStore } from '../stores/auth';

export default {
  name: 'SimpleChatWindow',
  emits: ['close'],
  data() {
    return {
      messages: [],
      inputMessage: '',
      isStreaming: false,
      isWaiting: false,
      threadId: null,
      eventSource: null
    };
  },
  methods: {
    closeChat() {
      if (this.eventSource) {
        this.eventSource.close();
      }
      this.$emit('close');
    },
    
    async sendMessage() {
      const message = this.inputMessage.trim();
      if (!message || this.isStreaming) return;
      
      // Add user message to chat
      this.messages.push({
        role: 'user',
        content: message,
        isStreaming: false
      });
      
      this.inputMessage = '';
      this.isStreaming = true;
      this.isWaiting = true;
      this.scrollToBottom();
      
      try {
        const token = authStore.getToken();
        if (!token) {
          throw new Error('No authentication token found');
        }
        
        // Use EventSource for SSE
        const url = new URL('/api/chat/stream', window.location.origin);
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: message,
            thread_id: this.threadId
          })
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Read the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMessageIndex = -1;
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              if (data === '[DONE]') {
                this.isWaiting = false;
                this.isStreaming = false;
                if (assistantMessageIndex >= 0) {
                  this.messages[assistantMessageIndex].isStreaming = false;
                }
                continue;
              }
              
              try {
                const event = JSON.parse(data);
                
                if (event.type === 'thread_created') {
                  this.threadId = event.data.thread_id;
                }
                else if (event.type === 'user_message') {
                  // User message already added
                }
                else if (event.type === 'assistant_message_start') {
                  this.isWaiting = false;
                  // Create new assistant message
                  assistantMessageIndex = this.messages.length;
                  this.messages.push({
                    role: 'assistant',
                    content: '',
                    isStreaming: true
                  });
                }
                else if (event.type === 'assistant_message_chunk') {
                  if (assistantMessageIndex >= 0) {
                    this.messages[assistantMessageIndex].content += event.data.chunk;
                    this.scrollToBottom();
                  }
                }
                else if (event.type === 'assistant_message_end') {
                  if (assistantMessageIndex >= 0) {
                    this.messages[assistantMessageIndex].isStreaming = false;
                  }
                }
                else if (event.type === 'error') {
                  const errorMsg = event.data.message || event.data.error || 'Unknown error';
                  console.error('Chat error:', errorMsg);
                  this.messages.push({
                    role: 'assistant',
                    content: `Error: ${errorMsg}`,
                    isStreaming: false
                  });
                }
              } catch (parseError) {
                console.error('Error parsing SSE data:', parseError, data);
              }
            }
          }
        }
      } catch (error) {
        console.error('Error sending message:', error);
        const errorMessage = error.message || error.toString() || 'Unknown error occurred';
        this.messages.push({
          role: 'assistant',
          content: `Sorry, there was an error: ${errorMessage}. Please try again.`,
          isStreaming: false
        });
      } finally {
        this.isStreaming = false;
        this.isWaiting = false;
        this.scrollToBottom();
      }
    },
    
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    }
  },
  
  mounted() {
    // Add welcome message
    this.messages.push({
      role: 'assistant',
      content: 'Hello! How can I help you today?',
      isStreaming: false
    });
  },
  
  beforeUnmount() {
    if (this.eventSource) {
      this.eventSource.close();
    }
  }
};
</script>

<style scoped>
.chat-window-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  z-index: 1000;
  padding: 20px;
}

.chat-window {
  background: white;
  width: 400px;
  max-width: 100%;
  height: 600px;
  max-height: calc(100vh - 40px);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 12px 12px 0 0;
}

.chat-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-button {
  background: transparent;
  border: none;
  color: white;
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.close-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  display: flex;
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message-content {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: #f1f3f5;
  color: #333;
  border-bottom-left-radius: 4px;
}

.message-text {
  display: inline;
}

.typing-indicator {
  display: inline-block;
  margin-left: 4px;
  animation: blink 1s infinite;
  color: rgba(255, 255, 255, 0.8);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.chat-input-container {
  padding: 16px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 10px;
  background: white;
}

.chat-input-container textarea {
  flex: 1;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
  resize: none;
  font-family: inherit;
}

.chat-input-container textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.chat-input-container button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: opacity 0.2s;
}

.chat-input-container button:hover:not(:disabled) {
  opacity: 0.9;
}

.chat-input-container button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #dee2e6;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #adb5bd;
}
</style>
