import { ref, onUnmounted } from 'vue';

export function useWebSocket() {
  const messages = ref([]);
  const isConnected = ref(false);
  const wsRef = ref(null);
  const reconnectTimeoutRef = ref(null);
  const isConnectingRef = ref(false);

  // Helper function to create approval messages
  const createApprovalMessage = (messageType, data, requestId) => {
    const approvalConfig = {
      approval_required: {
        dataKey: 'brief',
        dataValue: data.campaign_plan,
        approvalFlag: 'needsApproval',
        extraData: { isFormattedBrief: true }
      },
      creative_approval_required: {
        dataKey: 'media',
        dataValue: data.media || [],
        approvalFlag: 'needsCreativeApproval',
        extraData: {
          creativePrompt: data.prompt || ''
        }
      },
      publishing_approval_required: {
        dataKey: 'schedule',
        dataValue: data.schedule || [],
        approvalFlag: 'needsPublishingApproval',
        extraData: {}
      },
      localization_approval_required: {
        dataKey: 'localizations',
        dataValue: data.localizations || [],
        approvalFlag: 'needsLocalizationApproval',
        extraData: {}
      }
    };

    const config = approvalConfig[messageType];
    if (!config) return null;

    return {
      type: 'campaign_data',
      sender: 'silent',
      silent: true,
      campaign_data: {
        [config.dataKey]: config.dataValue,
        [config.approvalFlag]: true,
        ...config.extraData
      },
      request_id: requestId
    };
  };

  const connect = () => {
    // Prevent multiple simultaneous connection attempts
    if (
      isConnectingRef.value ||
      (wsRef.value && wsRef.value.readyState === WebSocket.OPEN)
    ) {
      console.log('Already connected or connecting, skipping...');
      return;
    }

    isConnectingRef.value = true;
    const wsUrl = `/api/marketing/ws`;

    console.log('Connecting to WebSocket:', wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      isConnected.value = true;
      isConnectingRef.value = false;
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('Received message:', message);

        // If this is campaign_data type, don't add to chat messages - just update state
        if (message.type === 'campaign_data') {
          console.log(
            'Received campaign data (not adding to chat):',
            message.campaign_data
          );
          // Still add to messages so we can extract campaign_data, but mark it as silent
          const silentMessage = {
            ...message,
            sender: 'silent',
            silent: true
          };
          messages.value = [...messages.value, silentMessage];
          return;
        }

        // Handle all approval-required message types with unified logic
        const approvalTypes = [
          'approval_required',
          'creative_approval_required',
          'publishing_approval_required',
          'localization_approval_required'
        ];

        if (approvalTypes.includes(message.type)) {
          console.log('📋 Creating approval message for type:', message.type);
          console.log('📋 Message data:', message);
          const approvalMessage = createApprovalMessage(
            message.type,
            message,
            message.request_id
          );
          console.log('📋 Created approval message:', approvalMessage);
          if (approvalMessage) {
            messages.value = [...messages.value, approvalMessage];
            return;
          }
        }

        // Transform message type to sender for backwards compatibility
        const transformedMessage = {
          ...message,
          sender: message.type === 'user' ? 'user' : 'workflow',
          // Preserve request_id and awaiting_input if present
          request_id: message.request_id,
          awaiting_input: message.awaiting_input
        };

        messages.value = [...messages.value, transformedMessage];
      } catch (error) {
        console.error('Error parsing message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      isConnectingRef.value = false;
    };

    ws.onclose = () => {
      console.log('WebSocket closed, reconnecting...');
      isConnected.value = false;
      isConnectingRef.value = false;

      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.value = setTimeout(() => {
        connect();
      }, 3000);
    };

    wsRef.value = ws;
  };

  const sendMessage = async (content) => {
    if (wsRef.value && wsRef.value.readyState === WebSocket.OPEN) {
      wsRef.value.send(JSON.stringify({ content }));
    } else {
      // Fallback to HTTP POST if WebSocket is not connected
      try {
        await fetch('/api/marketing/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content })
        });
      } catch (error) {
        console.error('Error sending message via HTTP:', error);
      }
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.value) {
      clearTimeout(reconnectTimeoutRef.value);
    }
    if (wsRef.value) {
      wsRef.value.close();
      wsRef.value = null;
    }
    isConnectingRef.value = false;
  };

  // Initialize connection
  connect();

  // Clean up on unmount
  onUnmounted(() => {
    disconnect();
  });

  return {
    messages,
    sendMessage,
    isConnected,
    connect,
    disconnect
  };
}
