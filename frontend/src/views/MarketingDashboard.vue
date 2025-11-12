<template>
  <div :class="['marketing-dashboard', { 'sidebar-collapsed': sidebarCollapsed }]">


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
        :active-agent="activeAgent"
        @send-message="handleSendMessage"
      />
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useWebSocket } from '../composables/useWebSocket';
import ChatBox from '../components/marketing/ChatBox.vue';
import CampaignDetails from '../components/marketing/CampaignDetails.vue';

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
    
    // Simplified loading state: single "active agent" variable
    const activeAgent = ref('');  // '', 'campaign_planner', 'creative', 'localization', 'publishing', 'instagram'

    const { messages, sendMessage, isConnected } = useWebSocket();


    let statusCheckInterval = null;
    const checkWorkflowStatus = async () => {
      try {
        const response = await fetch('/api/marketing/status');
        const data = await response.json();
        workflowStatus.value = data.status === 'online' ? 'online' : 'offline';
      } catch (error) {
        workflowStatus.value = 'offline';
      }
    };

    const handleSendMessage = (message) => {
      console.log(`📤 Sending message: "${message}"`);
      
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
        console.log('🎯 Approval message - not setting activeAgent');
      } else if (lowerMessage === 'approve_schedule') {
        // Clear schedule approval state and set Instagram loading
        campaignData.value = {
          ...campaignData.value,
          needsScheduleApproval: false
        };
        activeAgent.value = 'instagram';
        console.log(`🎯 Schedule approved - activeAgent set to: ${activeAgent.value}`);
      } else if (lowerMessage.includes('campaign approved! scheduling')) {
        // This is the confirmation message, don't trigger loading
        // Just send it to chat
        console.log('🎯 Confirmation message - not setting activeAgent');
      } else {
        // For new campaign requests, show loading for campaign planner
        activeAgent.value = 'campaign_planner';
        console.log(`🎯 New campaign request - activeAgent set to: ${activeAgent.value}`);
      }

      sendMessage(message);
    };

    // Enhanced campaign data extraction with better data preservation
    const extractCampaignData = (newMessages) => {
      if (!newMessages || newMessages.length === 0) return;

      // Get current values to avoid overwriting with empty data
      const currentBrief = campaignData.value.brief;
      const currentMedia = campaignData.value.media;
      const currentLocalizations = campaignData.value.localizations;
      const currentSchedule = campaignData.value.schedule;

      // Find the latest accumulated campaign data
      const accumulatedCampaignData = newMessages.reduce((acc, message) => {
        if (message.campaign_data) {
          return { ...acc, ...message.campaign_data };
        }
        return acc;
      }, {});

      // More programmatic ways to detect running agents:
      
      // 1. Look for ExecutorInvokedEvent or similar system messages with executor info
      // Include both debug and non-debug messages
      const executorMessages = newMessages.filter(msg => 
        msg.type === 'system' && 
        msg.content && 
        msg.content.includes('is running...')
      );
      
      // 2. Check for debug messages from backend about executor status  
      const debugMessages = newMessages.filter(msg => msg.debug === true);
      
      // 3. Look for workflow status indicators
      const statusMessages = newMessages.filter(msg => 
        msg.type === 'system' && 
        (msg.content?.includes('running') || msg.content?.includes('executing'))
      );

      // Enhanced executor detection - check both regular and debug messages
      const currentlyRunningExecutor = executorMessages
        .slice()
        .reverse()
        .find(msg => msg.content)
        ?.content?.match(/^(.+?)\s+is running\.\.\.$/)?.[1]?.toLowerCase();

      // Alternative detection specifically for creative agent
      const creativeAgentMessages = newMessages.filter(msg => 
        msg.content && msg.content.toLowerCase().includes('creative agent is running')
      );

      // Check for streaming creative content updates
      const creativeUpdateMessages = newMessages.filter(msg =>
        msg.content && (
          msg.content.includes('Creative Agent Update') ||
          msg.content.includes('**Creative Agent Update:**')
        )
      );

      // Check recent messages (last 10) for any creative activity
      const recentMessages = newMessages.slice(-10);
      const hasRecentCreativeActivity = recentMessages.some(msg =>
        msg.content && (
          msg.content.toLowerCase().includes('creative') ||
          msg.content.toLowerCase().includes('generating') ||
          msg.content.toLowerCase().includes('image') ||
          msg.content.toLowerCase().includes('assets')
        )
      );

      console.log('🔍 Executor Detection Debug:', {
        totalMessages: newMessages.length,
        executorMessages: executorMessages.map(m => ({ 
          content: m.content, 
          debug: m.debug,
          type: m.type 
        })),
        creativeAgentMessages: creativeAgentMessages.map(m => ({ 
          content: m.content, 
          debug: m.debug,
          type: m.type 
        })),
        debugMessages: debugMessages.map(m => ({ 
          content: m.content?.substring(0, 50),
          hasCreative: m.content?.toLowerCase().includes('creative')
        })),
        statusMessages: statusMessages.map(m => ({ content: m.content?.substring(0, 50) })),
        extractedExecutor: currentlyRunningExecutor
      });

      // Use accumulated data but preserve existing content if new data is empty
      // IMPORTANT: Preserve the original campaign brief once it's formatted to prevent
      // subsequent agent messages from overwriting it
      const currentBriefIsFormatted = campaignData.value.isFormattedBrief;
      const newBrief = currentBriefIsFormatted 
        ? currentBrief  // Keep existing brief if it's already formatted
        : (accumulatedCampaignData.brief || currentBrief);  // Otherwise, update as normal
      
      const newMedia = Array.isArray(accumulatedCampaignData.media) && accumulatedCampaignData.media.length > 0
        ? accumulatedCampaignData.media
        : currentMedia;
      const newLocalizations = Array.isArray(accumulatedCampaignData.localizations) && accumulatedCampaignData.localizations.length > 0
        ? accumulatedCampaignData.localizations
        : currentLocalizations;
      const newSchedule = Array.isArray(accumulatedCampaignData.schedule) && accumulatedCampaignData.schedule.length > 0
        ? accumulatedCampaignData.schedule
        : currentSchedule;

      // Update campaign data with preserved values
      campaignData.value = {
        ...campaignData.value,
        ...accumulatedCampaignData,
        brief: newBrief,
        media: newMedia,
        localizations: newLocalizations,
        schedule: newSchedule
      };
    };

    // Watch for message changes
    watch(messages, (newMessages) => {
      extractCampaignData(newMessages);
    }, { deep: true });

    // Separate watcher for agent status detection
    watch(messages, (newMessages) => {
      // Check the last 5 messages for any agent status
      const recentMessages = newMessages.slice(-5);
      
      for (const message of recentMessages) {
        if (message && message.content) {
          const content = message.content.toLowerCase();
          
          if (content.includes('coordinator is running')) {
            console.log('🎯 Found "coordinator is running" - setting activeAgent to campaign_planner');
            activeAgent.value = 'campaign_planner';
            return; // Exit early once we find an agent
          } else if (content.includes('creative agent is running')) {
            console.log('🎯 Found "creative agent is running" - setting activeAgent to creative');
            activeAgent.value = 'creative';
            return;
          } else if (content.includes('localization agent is running')) {
            console.log('🎯 Found "localization agent is running" - setting activeAgent to localization');
            activeAgent.value = 'localization';
            return;
          } else if (content.includes('publishing agent is running')) {
            console.log('🎯 Found "publishing agent is running" - setting activeAgent to publishing');
            activeAgent.value = 'publishing';
            return;
          } else if (content.includes('instagram agent is running')) {
            console.log('🎯 Found "instagram agent is running" - setting activeAgent to instagram');
            activeAgent.value = 'instagram';
            return;
          }
        }
      }
    }, { immediate: true });

    onMounted(() => {
      checkWorkflowStatus();
      statusCheckInterval = setInterval(checkWorkflowStatus, 10000);
      
      // Expose setActiveAgent to window for WebSocket to call
      window.setActiveAgent = (agent) => {
        activeAgent.value = agent;
      };
    });
    onUnmounted(() => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
      
      // Clean up global function
      if (window.setActiveAgent) {
        delete window.setActiveAgent;
      }
    });

    return {
      sidebarCollapsed,
      workflowStatus,
      campaignData,
      activeAgent,
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
  overflow: hidden;
}



.dashboard-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  background: white;
  min-height: 0;
}

.chat-sidebar {
  width: 400px;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  position: relative;
  flex-shrink: 0;
  border-right: 1px solid #d0d7de;
  min-height: 0;
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
}
</style>
