<template>
  <div class="chat-box">
    <div class="chat-header">
      <h3>Conversation</h3>
      <span v-if="isConnected" class="connection-indicator">●</span>
    </div>
    <div class="chat-messages" ref="messagesContainer">
      <CampaignMessage
        v-for="(message, index) in allMessages"
        :key="index"
        :message="message"
        @approval-response="handleApprovalResponse"
      />
      <div ref="messagesEndRef"></div>
    </div>
    <form class="input-area" @submit.prevent="handleSubmit">
      <textarea
        id="message-input"
        placeholder="Enter your message..."
        v-model="inputValue"
        @keypress="handleKeyPress"
        :disabled="workflowStatus !== 'online'"
      />
      <button
        type="submit"
        :disabled="workflowStatus !== 'online' || !inputValue.trim()"
      >
        Send
      </button>
    </form>
  </div>
</template>

<script>
import { ref, computed, watch, nextTick } from 'vue';
import CampaignMessage from './CampaignMessage.vue';

export default {
  name: 'ChatBox',
  components: {
    CampaignMessage
  },
  props: {
    messages: {
      type: Array,
      default: () => []
    },
    isConnected: {
      type: Boolean,
      default: false
    },
    workflowStatus: {
      type: String,
      default: 'checking'
    }
  },
  emits: ['send-message'],
  setup(props, { emit }) {
    const inputValue = ref('');
    const messagesContainer = ref(null);
    const messagesEndRef = ref(null);

    const filteredMessages = computed(() => {
      return props.messages.filter(message => {
        // Filter out silent messages
        if (message.silent === true || message.sender === 'silent') {
          return false;
        }
        // Filter out approval/reject messages from user
        if (message.sender === 'user' && message.content) {
          const content = message.content.toLowerCase().trim();
          return content !== 'approve' && !content.startsWith('reject');
        }
        return true;
      });
    });

    // Create a permanent welcome message that acts like it came from the agent
    const welcomeMessage = {
      type: 'system',
      content: `Please enter campaign details to get started! 

**Example:** "Holiday sock promotion. The campaign leverages bold, festive visuals and engaging video formats to target the 25-34 age range, driving brand awareness on Instagram and TikTok over a 4-week period with a $10k budget."

I'll help you create a complete marketing campaign with visuals, content, and scheduling!`,
      timestamp: new Date().toISOString(),
      sender: 'Marketing Agent'
    };

    // Combine welcome message with filtered messages
    const allMessages = computed(() => {
      return [welcomeMessage, ...filteredMessages.value];
    });

    const currentTime = computed(() => {
      return new Date().toLocaleTimeString('en-US', { 
        hour12: true, 
        hour: 'numeric', 
        minute: '2-digit' 
      });
    });

    const scrollToBottom = () => {
      nextTick(() => {
        messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' });
      });
    };

    watch(() => props.messages, () => {
      scrollToBottom();
    }, { deep: true });

    const handleSubmit = () => {
      if (inputValue.value.trim() && props.workflowStatus === 'online') {
        emit('send-message', inputValue.value.trim());
        inputValue.value = '';
      }
    };

    const handleKeyPress = (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    };

    const handleApprovalResponse = (response) => {
      emit('send-message', response);
    };

    return {
      inputValue,
      messagesContainer,
      messagesEndRef,
      allMessages,
      currentTime,
      handleSubmit,
      handleKeyPress,
      handleApprovalResponse
    };
  }
};
</script>

<style scoped>
.chat-box {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
  border-right: 1px solid #d0d7de;
  min-height: 0;
}

.chat-header {
  padding: 1rem;
  border-bottom: 1px solid #d0d7de;
  background: #f6f8fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.chat-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1f2328;
}

.connection-indicator {
  color: #2da44e;
  font-size: 1.5rem;
  line-height: 1;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 0;
}

.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f6f8fa;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #d0d7de;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #afb8c1;
}

.input-area {
  padding: 1rem;
  border-top: 1px solid #d0d7de;
  background: #f6f8fa;
  display: flex;
  gap: 0.75rem;
  flex-shrink: 0;
}

#message-input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.95rem;
  resize: vertical;
  min-height: 60px;
  max-height: 150px;
  background: #ffffff;
}

#message-input:focus {
  outline: none;
  border-color: #0969da;
  box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.1);
}

#message-input:disabled {
  background: #f6f8fa;
  color: #6e7781;
  cursor: not-allowed;
}

button[type="submit"] {
  padding: 0.75rem 1.5rem;
  background: #2da44e;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  align-self: flex-end;
}

button[type="submit"]:hover:not(:disabled) {
  background: #2c974b;
}

button[type="submit"]:disabled {
  background: #afb8c1;
  cursor: not-allowed;
}
</style>
