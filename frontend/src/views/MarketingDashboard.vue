<template>
  <div :class="['marketing-dashboard', { 'sidebar-collapsed': sidebarCollapsed }]">
    <div class="dashboard-header">
      <div class="header-content">
        <h2>Campaign Workflow</h2>
        <p class="subtitle">AI-powered campaign planning and content creation</p>
      </div>
      <div class="workflow-status">
        <span :class="['status-badge', workflowStatus]">
          <span class="status-dot"></span>
          {{ workflowStatus === 'online' ? 'Workflow Online' : 'Checking...' }}
        </span>
      </div>
    </div>

    <div class="dashboard-body">
      <div class="chat-sidebar">
        <button
          class="sidebar-toggle"
          @click="sidebarCollapsed = !sidebarCollapsed"
          :title="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        >
          {{ sidebarCollapsed ? '►' : '◄' }}
        </button>
        <ChatBox
          v-if="!sidebarCollapsed"
          :messages="messages"
          :is-connected="isConnected"
          :workflow-status="workflowStatus"
          @send-message="handleSendMessage"
        />
      </div>
      <CampaignDetails
        :campaign-data="campaignData"
        :loading-states="loadingStates"
        @send-message="handleSendMessage"
      />
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useWebSocket } from '../../composables/useWebSocket';
import ChatBox from '../../components/marketing/ChatBox.vue';
import CampaignDetails from '../../components/marketing/CampaignDetails.vue';

export default {
  name: 'MarketingDashboard',
  components: {
    ChatBox,
    CampaignDetails
  },
  setup() {
    const sidebarCollapsed = ref(false);
    const workflowStatus = ref('checking');
    const campaignData = ref({
      brief: '',
      media: [],
      schedule: [],
      localizations: []
    });
    const loadingStates = ref({
      campaignBrief: false,
      socialMedia: false,
      localization: false
    });

    const { messages, sendMessage, isConnected } = useWebSocket();

    let statusCheckInterval = null;

    const checkWorkflowStatus = async () => {
      try {
        const response = await fetch('/api/status');
        const data = await response.json();
        workflowStatus.value = data.status === 'online' ? 'online' : 'offline';
      } catch (error) {
        workflowStatus.value = 'offline';
      }
    };

    const handleSendMessage = (message) => {
      // Check if this is an approval/reject decision
      const lowerMessage = message.toLowerCase().trim();
      if (lowerMessage === 'approve' || lowerMessage.startsWith('reject')) {
        // Clear ALL approval states immediately
        campaignData.value = {
          ...campaignData.value,
          needsApproval: false,
          needsCreativeApproval: false,
          needsPublishingApproval: false,
          needsLocalizationApproval: false
        };
      } else {
        // For new campaign requests, show loading
        loadingStates.value = { campaignBrief: true, socialMedia: false };
      }

      sendMessage(message);
    };

    const extractCampaignData = (messagesList) => {
      if (messagesList.length === 0) return;

      console.log('extractCampaignData called with', messagesList.length, 'messages');

      // Check executor status to show loading animations
      let currentlyRunningExecutor = null;

      for (let i = messagesList.length - 1; i >= Math.max(0, messagesList.length - 10); i--) {
        const msg = messagesList[i];

        if (msg.type === 'system' && msg.content) {
          const content = msg.content.toLowerCase();

          if (content.includes('running')) {
            if (content.includes('campaign kickoff') || content.includes('campaign_kickoff')) {
              currentlyRunningExecutor = 'campaign_kickoff';
              break;
            } else if (content.includes('creative agent') || content.includes('creative_agent')) {
              currentlyRunningExecutor = 'creative_agent';
              break;
            } else if (content.includes('critique agent') || content.includes('critique_agent')) {
              currentlyRunningExecutor = 'critique_agent';
              break;
            }
          }
        }
      }

      // Check for messages with embedded campaign_data
      let hasReceivedBrief = false;
      let hasReceivedMedia = false;
      let accumulatedCampaignData = {};

      for (let i = messagesList.length - 1; i >= 0; i--) {
        const msg = messagesList[i];

        if (msg.campaign_data) {
          console.log(`📨 Found campaign_data in message ${i}:`, msg.campaign_data);

          Object.keys(msg.campaign_data).forEach((key) => {
            const value = msg.campaign_data[key];

            // For approval flags, only set if true
            if (key.startsWith('needs') && key.includes('Approval')) {
              if (value === true) {
                accumulatedCampaignData[key] = true;
              }
            } else {
              // For non-approval fields, use newer values
              if (accumulatedCampaignData[key] === undefined) {
                accumulatedCampaignData[key] = value;
              }
            }
          });

          if (msg.campaign_data.brief) {
            hasReceivedBrief = true;
          }
          if (msg.campaign_data.media && msg.campaign_data.media.length > 0) {
            hasReceivedMedia = true;
          }
        }
      }

      // Apply accumulated campaign data
      if (Object.keys(accumulatedCampaignData).length > 0) {
        console.log('📦 Applying accumulated campaign_data');
        campaignData.value = {
          ...campaignData.value,
          ...accumulatedCampaignData
        };
      }

      // Set loading states
      const shouldShowBriefLoading =
        (currentlyRunningExecutor !== null && !hasReceivedBrief) ||
        (!hasReceivedBrief && loadingStates.value.campaignBrief);
      const shouldShowMediaLoading =
        (currentlyRunningExecutor === 'creative_agent' ||
          currentlyRunningExecutor === 'critique_agent') &&
        !hasReceivedMedia;

      if (shouldShowBriefLoading && !shouldShowMediaLoading) {
        loadingStates.value = { campaignBrief: true, socialMedia: false };
      } else if (shouldShowMediaLoading) {
        loadingStates.value = { campaignBrief: false, socialMedia: true };
      } else if (hasReceivedBrief || hasReceivedMedia) {
        loadingStates.value = {
          campaignBrief: false,
          socialMedia: false,
          localization: false
        };
      }
    };

    // Watch for message changes
    watch(messages, (newMessages) => {
      extractCampaignData(newMessages);
    }, { deep: true });

    onMounted(() => {
      checkWorkflowStatus();
      statusCheckInterval = setInterval(checkWorkflowStatus, 10000);
    });

    onUnmounted(() => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    });

    return {
      sidebarCollapsed,
      workflowStatus,
      campaignData,
      loadingStates,
      messages,
      isConnected,
      handleSendMessage
    };
  }
};
</script>

<style scoped>
.marketing-dashboard {
  display: flex;
  flex-direction: column;
  background: #f6f8fa;
  height: 100%;
}

.dashboard-header {
  background: #ffffff;
  border-bottom: 1px solid #d0d7de;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2328;
}

.subtitle {
  margin: 0.25rem 0 0;
  color: #6e7781;
  font-size: 0.9rem;
}

.workflow-status {
  display: flex;
  align-items: center;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #f6f8fa;
  border: 1px solid #d0d7de;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
  color: #1f2328;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2da44e;
  animation: pulse 2s ease-in-out infinite;
}

.status-badge.offline .status-dot {
  background: #cf222e;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.dashboard-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  margin: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  background: white;
}

.chat-sidebar {
  width: 400px;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  position: relative;
  flex-shrink: 0;
  border-right: 1px solid #d0d7de;
}

.marketing-dashboard.sidebar-collapsed .chat-sidebar {
  width: 60px;
}

.sidebar-toggle {
  position: absolute;
  top: 1rem;
  right: -15px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #667eea;
  color: white;
  border: 2px solid white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  z-index: 100;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.sidebar-toggle:hover {
  transform: scale(1.1);
  background: #764ba2;
}

@media (max-width: 1024px) {
  .dashboard-body {
    flex-direction: column;
    margin: 1rem;
  }

  .chat-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #d0d7de;
    max-height: 400px;
  }

  .marketing-dashboard.sidebar-collapsed .chat-sidebar {
    max-height: 60px;
  }

  .sidebar-toggle {
    top: auto;
    bottom: -15px;
    right: 50%;
    transform: translateX(50%) rotate(90deg);
  }

  .sidebar-toggle:hover {
    transform: translateX(50%) rotate(90deg) scale(1.1);
  }
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    padding: 1.5rem;
  }

  .header-content h1 {
    font-size: 1.5rem;
  }
}
</style>
