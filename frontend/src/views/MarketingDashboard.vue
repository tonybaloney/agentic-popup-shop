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
        :loading-states="loadingStates"
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
    const loadingStates = ref({
      campaignBrief: false,
      socialMedia: false,
      localization: false
    });

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

      console.log('🔍 Executor Detection Debug:', {
        totalMessages: newMessages.length,
        executorMessages: executorMessages.map(m => ({ content: m.content, debug: m.debug })),
        debugMessages: debugMessages.map(m => ({ content: m.content?.substring(0, 50) })),
        statusMessages: statusMessages.map(m => ({ content: m.content?.substring(0, 50) })),
        extractedExecutor: currentlyRunningExecutor
      });

      // Use accumulated data but preserve existing content if new data is empty
      const newBrief = accumulatedCampaignData.brief || currentBrief;
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

      // Enhanced loading state detection
      const hasReceivedBrief = newBrief && accumulatedCampaignData.isFormattedBrief;
      const hasReceivedMedia = Array.isArray(newMedia) && newMedia.length > 0;
      const needsCreativeApproval = accumulatedCampaignData.needsCreativeApproval;

      // More precise loading state logic using multiple detection methods
      const shouldShowBriefLoading = !hasReceivedBrief && (
        currentlyRunningExecutor === 'campaign planner' ||
        accumulatedCampaignData.needsCampaignFollowup ||
        accumulatedCampaignData.needsMarketSelection
      );

      // Enhanced detection for creative agent running
      const isCreativeAgentActive = currentlyRunningExecutor === 'creative agent' ||
        currentlyRunningExecutor === 'creative' ||
        debugMessages.some(msg => 
          msg.content && (
            msg.content.toLowerCase().includes('creative') ||
            msg.content.toLowerCase().includes('generating')
          )
        ) ||
        // Look for workflow state indicating creative work
        statusMessages.some(msg => 
          msg.content && (
            msg.content.toLowerCase().includes('creative') ||
            msg.content.toLowerCase().includes('media') ||
            msg.content.toLowerCase().includes('assets')
          )
        );

      const shouldShowMediaLoading = hasReceivedBrief && 
        !hasReceivedMedia && 
        !needsCreativeApproval && 
        isCreativeAgentActive;

      console.log('🎬 Enhanced loading state calculation:', {
        currentlyRunningExecutor,
        isCreativeAgentActive,
        hasReceivedBrief,
        hasReceivedMedia,
        needsCreativeApproval,
        shouldShowBriefLoading,
        shouldShowMediaLoading,
        executorMessages: executorMessages.length,
        debugMessages: debugMessages.length,
        statusMessages: statusMessages.length
      });

      if (shouldShowBriefLoading && !shouldShowMediaLoading) {
        console.log('📋 Setting brief loading to true');
        loadingStates.value = { campaignBrief: true, socialMedia: false };
      } else if (shouldShowMediaLoading) {
        console.log('🎨 Setting media loading to true');
        loadingStates.value = { campaignBrief: false, socialMedia: true };
      } else if (hasReceivedBrief || hasReceivedMedia) {
        console.log('✅ Setting all loading to false');
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
  overflow: hidden;
}



.dashboard-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  margin: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
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
