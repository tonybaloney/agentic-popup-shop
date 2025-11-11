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
      localization: false,
      publishing: false,
      instagram: false
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
        loadingStates.value = { campaignBrief: true, socialMedia: false, localization: false, publishing: false, instagram: false };
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

      // Enhanced loading state detection
      const hasReceivedBrief = newBrief && accumulatedCampaignData.isFormattedBrief;
      const hasReceivedMedia = Array.isArray(newMedia) && newMedia.length > 0;
      const needsCreativeApproval = accumulatedCampaignData.needsCreativeApproval;

      // More precise loading state logic using multiple detection methods
      const shouldShowBriefLoading = !hasReceivedBrief && (
        currentlyRunningExecutor === 'campaign planner' ||
        currentlyRunningExecutor === 'campaign_planner_agent' ||
        accumulatedCampaignData.needsCampaignFollowup ||
        accumulatedCampaignData.needsMarketSelection
      );

      // Enhanced detection for creative agent running
      const isCreativeAgentActive = currentlyRunningExecutor === 'creative agent' ||
        currentlyRunningExecutor === 'creative' ||
        currentlyRunningExecutor === 'creative_agent' ||
        creativeAgentMessages.length > 0 ||
        creativeUpdateMessages.length > 0 ||
        hasRecentCreativeActivity ||
        debugMessages.some(msg => 
          msg.content && (
            msg.content.toLowerCase().includes('creative agent') ||
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

      console.log('🔍 Creative Agent Detection Debug:', {
        currentlyRunningExecutor,
        creativeAgentMessagesCount: creativeAgentMessages.length,
        creativeUpdateMessagesCount: creativeUpdateMessages.length,
        hasRecentCreativeActivity,
        recentMessagesContent: recentMessages.map(m => m.content?.substring(0, 30)),
        executorMessages: executorMessages.map(m => ({ 
          content: m.content?.substring(0, 100),
          debug: m.debug,
          type: m.type,
          matchesPattern: /^(.+?)\s+is running\.\.\.$/i.test(m.content || '')
        })),
        debugMessages: debugMessages.map(m => ({ 
          content: m.content?.substring(0, 50),
          hasCreative: m.content?.toLowerCase().includes('creative'),
          hasGenerating: m.content?.toLowerCase().includes('generating')
        })),
        statusMessages: statusMessages.map(m => ({ 
          content: m.content?.substring(0, 50),
          hasCreative: m.content?.toLowerCase().includes('creative'),
          hasMedia: m.content?.toLowerCase().includes('media')
        })),
        isCreativeAgentActive
      });

      const shouldShowMediaLoading = (
        hasReceivedBrief && 
        !hasReceivedMedia && 
        !needsCreativeApproval && 
        isCreativeAgentActive
      ) || (
        // Also show loading if we detect creative agent running regardless of brief status
        isCreativeAgentActive && 
        !hasReceivedMedia && 
        !needsCreativeApproval
      );

      console.log('🎨 Media Loading Debug:', {
        hasReceivedBrief,
        hasReceivedMedia,
        needsCreativeApproval,
        isCreativeAgentActive,
        shouldShowMediaLoading,
        'newMedia.length': newMedia ? newMedia.length : 'null',
        'brief exists': !!newBrief,
        'isFormattedBrief': accumulatedCampaignData.isFormattedBrief
      });

      // Detection for localization agent running
      const isLocalizationAgentActive = currentlyRunningExecutor === 'localization_agent' ||
        currentlyRunningExecutor === 'localization agent' ||
        debugMessages.some(msg => 
          msg.content && (
            msg.content.toLowerCase().includes('localization agent') ||
            msg.content.toLowerCase().includes('translating') ||
            msg.content.toLowerCase().includes('localization')
          )
        );

      const hasReceivedLocalizations = Array.isArray(newLocalizations) && newLocalizations.length > 0;
      const shouldShowLocalizationLoading = (
        hasReceivedMedia && 
        !hasReceivedLocalizations && 
        isLocalizationAgentActive
      ) || (
        // Also show if localization agent is detected running regardless
        isLocalizationAgentActive && 
        !hasReceivedLocalizations
      );

      // Detection for publishing agent running
      const isPublishingAgentActive = currentlyRunningExecutor === 'publishing_agent' ||
        currentlyRunningExecutor === 'publishing agent' ||
        debugMessages.some(msg => 
          msg.content && (
            msg.content.toLowerCase().includes('publishing agent') ||
            msg.content.toLowerCase().includes('publishing') ||
            msg.content.toLowerCase().includes('scheduling')
          )
        );

      const hasReceivedSchedule = Array.isArray(newSchedule) && newSchedule.length > 0;
      const shouldShowPublishingLoading = (
        hasReceivedLocalizations && 
        !hasReceivedSchedule && 
        isPublishingAgentActive
      ) || (
        // Also show if publishing agent is detected running regardless
        isPublishingAgentActive && 
        !hasReceivedSchedule
      );

      // Detection for Instagram agent running
      const isInstagramAgentActive = currentlyRunningExecutor === 'instagram_agent' ||
        currentlyRunningExecutor === 'instagram agent' ||
        debugMessages.some(msg => 
          msg.content && (
            msg.content.toLowerCase().includes('instagram agent') ||
            msg.content.toLowerCase().includes('instagram post') ||
            msg.content.toLowerCase().includes('preparing instagram')
          )
        );

      const hasReceivedInstagramPost = campaignData.value?.instagram_post != null;
      const shouldShowInstagramLoading = (
        hasReceivedSchedule && 
        !hasReceivedInstagramPost && 
        isInstagramAgentActive
      ) || (
        // Also show if Instagram agent is detected running regardless
        isInstagramAgentActive && 
        !hasReceivedInstagramPost
      );

      console.log('🎬 Enhanced loading state calculation:', {
        currentlyRunningExecutor,
        isCreativeAgentActive,
        isLocalizationAgentActive,
        isPublishingAgentActive,
        isInstagramAgentActive,
        hasReceivedBrief,
        hasReceivedMedia,
        hasReceivedLocalizations,
        hasReceivedSchedule,
        hasReceivedInstagramPost,
        needsCreativeApproval,
        shouldShowBriefLoading,
        shouldShowMediaLoading,
        shouldShowLocalizationLoading,
        shouldShowPublishingLoading,
        shouldShowInstagramLoading,
        shouldShowPublishingLoading,
        executorMessages: executorMessages.length,
        debugMessages: debugMessages.length,
        statusMessages: statusMessages.length
      });

      if (shouldShowBriefLoading && !shouldShowMediaLoading && !shouldShowLocalizationLoading && !shouldShowPublishingLoading && !shouldShowInstagramLoading) {
        console.log('📋 Setting brief loading to true');
        loadingStates.value = { campaignBrief: true, socialMedia: false, localization: false, publishing: false, instagram: false };
      } else if (shouldShowMediaLoading && !shouldShowLocalizationLoading && !shouldShowPublishingLoading && !shouldShowInstagramLoading) {
        console.log('🎨 Setting media loading to true');
        loadingStates.value = { campaignBrief: false, socialMedia: true, localization: false, publishing: false, instagram: false };
      } else if (shouldShowLocalizationLoading && !shouldShowPublishingLoading && !shouldShowInstagramLoading) {
        console.log('🌍 Setting localization loading to true');
        loadingStates.value = { campaignBrief: false, socialMedia: false, localization: true, publishing: false, instagram: false };
      } else if (shouldShowPublishingLoading && !shouldShowInstagramLoading) {
        console.log('📅 Setting publishing loading to true');
        loadingStates.value = { campaignBrief: false, socialMedia: false, localization: false, publishing: true, instagram: false };
      } else if (shouldShowInstagramLoading) {
        console.log('📱 Setting Instagram loading to true');
        loadingStates.value = { campaignBrief: false, socialMedia: false, localization: false, publishing: false, instagram: true };
      } else if (hasReceivedBrief || hasReceivedMedia || hasReceivedLocalizations || hasReceivedSchedule || hasReceivedInstagramPost) {
        console.log('✅ Setting all loading to false');
        loadingStates.value = {
          campaignBrief: false,
          socialMedia: false,
          localization: false,
          publishing: false,
          instagram: false
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
