<template>
  <div :class="['message', message.type]">
    <div :class="['message-content', { 'markdown-content': hasMarkdown }]">
      <div v-if="hasMarkdown" v-html="renderMarkdown(cleanContent)"></div>
      <div v-else>{{ cleanContent }}</div>
    </div>
    <div class="message-time">{{ formatTime(message.timestamp) }}</div>

    <div v-if="isApprovalRequest" class="approval-buttons">
      <button class="approval-btn approve-btn" @click="handleApprove">
        ✓ Approve
      </button>
      <button class="approval-btn reject-btn" @click="handleReject">
        ✗ Reject
      </button>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';
import { marked } from 'marked';

export default {
  name: 'CampaignMessage',
  props: {
    message: {
      type: Object,
      required: true
    }
  },
  emits: ['approval-response'],
  setup(props, { emit }) {
    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString();
    };

    // Check for approval request
    const hasApprovalMarker = computed(() => 
      props.message.content?.includes('[APPROVAL_REQUIRED]')
    );
    
    const hasRequestId = computed(() => 
      props.message.request_id && props.message.awaiting_input
    );
    
    const isApprovalRequest = computed(() => 
      hasApprovalMarker.value || hasRequestId.value
    );

    const cleanContent = computed(() => {
      if (hasApprovalMarker.value) {
        return props.message.content.replace('[APPROVAL_REQUIRED]', '').trim();
      }
      return props.message.content || '';
    });

    // Check if content should be rendered as markdown
    const hasMarkdown = computed(() => {
      const content = cleanContent.value;
      return content && (
        content.includes('##') ||
        content.includes('**') ||
        /^\s*[-*]\s+/m.test(content) ||
        /^\s*\d+\.\s+/m.test(content)
      );
    });

    const renderMarkdown = (content) => {
      try {
        return marked.parse(content);
      } catch (error) {
        console.error('Error rendering markdown:', error);
        return content;
      }
    };

    const handleApprove = () => {
      emit('approval-response', 'approve');
    };

    const handleReject = () => {
      const feedback = window.prompt('Please provide feedback for rejection:');
      if (feedback !== null && feedback.trim()) {
        emit('approval-response', 'reject: ' + feedback);
      }
    };

    return {
      formatTime,
      isApprovalRequest,
      cleanContent,
      hasMarkdown,
      renderMarkdown,
      handleApprove,
      handleReject
    };
  }
};
</script>

<style scoped>
.message {
  margin: 1rem 0;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  animation: slideIn 0.3s ease-out;
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
  background: #ddf4ff;
  border-left: 3px solid #0969da;
  margin-left: 2rem;
}

.message.system,
.message.workflow {
  background: #f6f8fa;
  border-left: 3px solid #6e7781;
}

.message-content {
  color: #24292f;
  line-height: 1.6;
  word-wrap: break-word;
}

.message-content.markdown-content {
  font-size: 0.95rem;
}

.message-content :deep(h1),
.message-content :deep(h2),
.message-content :deep(h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

.message-content :deep(p) {
  margin: 0.5rem 0;
}

.message-content :deep(strong) {
  font-weight: 600;
  color: #1f2328;
}

.message-time {
  font-size: 0.75rem;
  color: #6e7781;
  margin-top: 0.5rem;
}

.approval-buttons {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.approval-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.approve-btn {
  background: #2da44e;
  color: white;
}

.approve-btn:hover {
  background: #2c974b;
}

.reject-btn {
  background: #cf222e;
  color: white;
}

.reject-btn:hover {
  background: #a40e26;
}
</style>
