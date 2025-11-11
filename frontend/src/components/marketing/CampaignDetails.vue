<template>
  <div class="campaign-details">
    <div class="details-content">
      <!-- Campaign Brief Accordion -->
      <div
        :class="['accordion-section', { 'needs-approval': needsApproval }]"
      >
        <div class="accordion-header" @click="toggleSection('brief')">
          <h3>Campaign Brief</h3>
          <div class="accordion-controls">
            <span v-if="needsApproval" class="approval-indicator">⚠</span>
            <span v-else-if="hasBriefContent" class="content-indicator">✓</span>
            <span class="accordion-icon">
              {{ expandedSections.brief ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSections.brief" class="accordion-content">
          <div v-if="isBriefLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Generating campaign strategy...</p>
          </div>
          <template v-else-if="brief">
            <div
              :class="['brief-content', { 'markdown-content': isFormattedBrief }]"
            >
              <div v-if="isFormattedBrief" v-html="renderMarkdown(brief)"></div>
              <div v-else class="user-input">{{ brief }}</div>
            </div>
          </template>
          <span v-else class="placeholder">
            Campaign brief will appear here...
          </span>
          <div
            v-if="needsApproval && brief && !isBriefLoading"
            class="approval-actions"
          >
            <button class="approve-btn" @click="handleApproval(true)">
              ✓ Approve
            </button>
            <button class="reject-btn" @click="handleApproval(false)">
              ✗ Reject
            </button>
          </div>
        </div>
      </div>

      <!-- Media Carousel Accordion -->
      <div
        :class="['accordion-section', { 'needs-approval': needsCreativeApproval }]"
      >
        <div class="accordion-header" @click="toggleSection('media')">
          <h3>Social Media Assets</h3>
          <div class="accordion-controls">
            <span v-if="needsCreativeApproval" class="approval-indicator">⚠</span>
            <span v-else-if="media.length > 0" class="content-indicator">✓</span>
            <span class="accordion-icon">
              {{ expandedSections.media ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSections.media" class="accordion-content">
          <div v-if="isMediaLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Creating marketing visuals...</p>
          </div>
          <template v-else-if="media.length > 0">
            <div
              :class="['media-grid', { 'pending-approval': needsCreativeApproval }]"
            >
              <div
                v-for="(item, index) in media"
                :key="index"
                class="media-item"
              >
                <img
                  v-if="item.type === 'image'"
                  :src="item.url"
                  :alt="item.caption || `Campaign media ${index + 1}`"
                  class="media-image"
                />
                <video
                  v-if="item.type === 'video'"
                  :src="item.url"
                  :poster="item.thumbnail"
                  controls
                  class="media-video"
                />
                <div
                  v-if="item.caption || item.hashtags"
                  :contenteditable="needsCreativeApproval"
                  :class="needsCreativeApproval ? 'editable-caption' : 'media-caption'"
                  @input="(e) => handleCaptionEdit(index, e)"
                  @blur="(e) => handleCaptionEdit(index, e)"
                >
                  <span v-if="item.caption">{{ editedCaptions[index] || item.caption }}</span>
                  <span v-if="item.caption && item.hashtags"> </span>
                  <span v-if="item.hashtags">{{ Array.isArray(item.hashtags) ? item.hashtags.join(' ') : item.hashtags }}</span>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="media-placeholder">
            <span>Media assets will appear here...</span>
          </div>
          <div
            v-if="needsCreativeApproval && media.length > 0 && !isMediaLoading"
            class="approval-actions"
          >
            <button class="approve-btn" @click="handleApproval(true)">
              ✓ Approve
            </button>
            <button class="reject-btn" @click="handleApproval(false)">
              ✗ Reject
            </button>
          </div>
        </div>
      </div>

      <!-- Localization Accordion -->
      <div
        :class="['accordion-section', { 'needs-approval': needsMarketSelection }]"
      >
        <div class="accordion-header" @click="toggleSection('localization')">
          <h3>Localized Content</h3>
          <div class="accordion-controls">
            <span v-if="needsMarketSelection" class="approval-indicator">⚠</span>
            <span v-else-if="localizations.length > 0" class="content-indicator">✓</span>
            <span class="accordion-icon">
              {{ expandedSections.localization ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSections.localization" class="accordion-content">
          <div v-if="isLocalizationLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Generating localized content...</p>
          </div>
          <template v-else-if="localizations.length > 0">
            <div class="media-grid">
              <div
                v-for="(item, index) in localizations"
                :key="index"
                class="media-item"
              >
                <div class="media-container">
                  <img
                    v-if="item.type === 'image'"
                    :src="item.image"
                    :alt="`Localized media ${index + 1}`"
                    class="media-image"
                  />
                  <video
                    v-if="item.type === 'video'"
                    :src="item.image"
                    :poster="item.thumbnail"
                    controls
                    class="media-video"
                  />
                  <!-- Language pill as overlay on the media -->
                  <div class="language-pills">
                    <span class="language-pill">
                      {{ item.locale ? item.locale.toUpperCase() : item.language }}
                    </span>
                  </div>
                </div>
                
                <!-- Show translated caption (includes hashtags) -->
                <div class="localized-caption">
                  <div class="media-caption">
                    {{ item.caption }}
                  </div>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="media-placeholder">
            <span v-if="needsMarketSelection">Waiting for response...</span>
            <span v-else>Localized content will appear here...</span>
          </div>
        </div>
      </div>

      <!-- Schedule Accordion -->
      <div
        :class="['accordion-section', { 'needs-approval': needsScheduleApproval }]"
      >
        <div class="accordion-header" @click="toggleSection('schedule')">
          <h3>Publish Schedule</h3>
          <div class="accordion-controls">
            <span v-if="needsScheduleApproval" class="approval-indicator">⚠</span>
            <span v-else-if="hasScheduleContent" class="content-indicator">✓</span>
            <span class="accordion-icon">
              {{ expandedSections.schedule ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSections.schedule" class="accordion-content">
          <div v-if="isPublishingLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Generating publishing schedule...</p>
          </div>
          <template v-else-if="schedule.length > 0">
            <!-- Publishing Schedule Table -->
            <div 
              :class="['schedule-table-container', { 'pending-approval': needsScheduleApproval }]"
            >
              <table class="schedule-table">
                <thead>
                  <tr>
                    <th>Platform</th>
                    <th>Language</th>
                    <th>Media</th>
                    <th>Post Time</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(item, index) in schedule"
                    :key="index"
                    class="schedule-row"
                  >
                    <td class="platform-cell">
                      <div class="platform-info">
                        <span class="platform-icon">{{ item.icon || item.platform_icon || "" }}</span>
                        <span class="platform-name">{{ item.platform || item.channel || 'Social Media' }}</span>
                      </div>
                    </td>
                    <td class="language-cell">
                      <span 
                        :class="['language-badge', getLanguageClass(item.language || item.locale || 'EN')]"
                      >
                        {{ getLanguageFlag(item.language || item.locale || 'EN') }} 
                        {{ (item.language || item.locale || 'EN').toUpperCase() }}
                      </span>
                    </td>
                    <td class="media-cell">
                      <div class="media-preview">
                        <img 
                          v-if="(item.media_type || item.type || 'image') === 'image' && (item.media_url || item.image)"
                          :src="item.media_url || item.image"
                          :alt="'Media preview'"
                          class="media-thumbnail"
                        />
                        <video 
                          v-else-if="(item.media_type || item.type) === 'video' && (item.media_url || item.image)"
                          :src="item.media_url || item.image"
                          class="media-thumbnail video-thumbnail"
                          muted
                        >
                        </video>
                        <span v-else class="media-type">
                          {{ (item.media_type || item.type || 'Image').charAt(0).toUpperCase() + (item.media_type || item.type || 'Image').slice(1) }}
                        </span>
                      </div>
                    </td>
                    <td class="time-cell">
                      <div class="schedule-time">
                        <div class="date">{{ formatDate(item.datetime || item.post_time || item.time) }}</div>
                        <div class="time">{{ formatTime(item.datetime || item.post_time || item.time) }}</div>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <div v-if="needsScheduleApproval" class="approval-actions">
              <button class="approve-btn" @click="handleScheduleApproval(true)">
                ✓ Approve & Publish to Instagram
              </button>
              <button class="reject-btn" @click="handleScheduleApproval(false)">
                ✗ Reject Schedule
              </button>
            </div>
          </template>
          <div v-else class="schedule-placeholder">
            <span>Publish schedule will appear here...</span>
          </div>
        </div>
      </div>

      <!-- Instagram Publish Accordion -->
      <div class="accordion-section">
        <div class="accordion-header" @click="toggleSection('instagram')">
          <h3>Instagram Publish</h3>
          <div class="accordion-controls">
            <span v-if="hasInstagramContent" class="content-indicator">✓</span>
            <span class="accordion-icon">
              {{ expandedSections.instagram ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSections.instagram" class="accordion-content">
          <div v-if="isInstagramLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">🚀 Publishing to Instagram via Ayrshare...</p>
          </div>
          <template v-else-if="instagramPost">
            <!-- Instagram Post Preview -->
            <div class="instagram-post-container">
              <div class="instagram-post-header">
                <div class="platform-badge">
                  <span class="platform-name">{{ instagramPost.platform || 'Instagram' }}</span>
                  <span class="content-type">{{ instagramPost.content_type || 'Post' }}</span>
                </div>
                <div class="post-status">
                  <span v-if="campaignData?.published === true" class="status-badge status-published">
                    ✅ Published
                  </span>
                  <span v-else-if="campaignData?.published === false" class="status-badge status-failed">
                    ❌ Failed
                  </span>
                  <span v-else :class="['status-badge', getStatusClass(instagramPost.status)]">
                    {{ formatStatus(instagramPost.status) }}
                  </span>
                </div>
              </div>
              
              <div class="instagram-post-content">
                <!-- Media Preview -->
                <div v-if="instagramPost.media_url" class="media-preview-large">
                  <img 
                    v-if="instagramPost.media_type === 'image'"
                    :src="instagramPost.media_url"
                    :alt="instagramPost.caption"
                    class="instagram-media"
                  />
                  <video 
                    v-else-if="instagramPost.media_type === 'video'"
                    :src="instagramPost.media_url"
                    controls
                    class="instagram-media"
                  >
                  </video>
                </div>

                <!-- Post Details -->
                <div class="post-details">
                  <div class="detail-row">
                    <span class="detail-label">Post ID:</span>
                    <span class="detail-value">{{ instagramPost.post_id || 'N/A' }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">Language:</span>
                    <span 
                      :class="['language-badge', getLanguageClass(instagramPost.language)]"
                    >
                      {{ getLanguageFlag(instagramPost.language) }} 
                      {{ instagramPost.language || 'N/A' }}
                    </span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">Scheduled:</span>
                    <span class="detail-value">{{ formatDateTime(instagramPost.scheduled_time) }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">Target Audience:</span>
                    <span class="detail-value">{{ instagramPost.target_audience || 'N/A' }}</span>
                  </div>
                  
                  <!-- Publishing Status Messages -->
                  <div v-if="campaignData?.published === true" class="success-message">
                    <div class="detail-label">✅ Publishing Status:</div>
                    <div class="success-text">Successfully posted to Instagram!</div>
                    <div v-if="instagramPost.ayrshare_response?.id" class="post-link">
                      Post ID: {{ instagramPost.ayrshare_response.id }}
                    </div>
                  </div>
                  
                  <div v-else-if="campaignData?.published === false && campaignData?.error" class="error-message">
                    <div class="detail-label">❌ Publishing Error:</div>
                    <div class="error-text">{{ campaignData.error }}</div>
                    <div v-if="instagramPost.message" class="error-details">
                      Details: {{ instagramPost.message }}
                    </div>
                  </div>
                  
                  <!-- Caption and Hashtags -->
                  <div class="caption-section">
                    <div class="detail-label">Caption:</div>
                    <div class="instagram-caption">
                      <span v-if="instagramPost.caption">{{ instagramPost.caption || 'No caption' }}</span>
                      <span v-if="instagramPost.caption && instagramPost.hashtags"> </span>
                      <span v-if="instagramPost.hashtags">{{ Array.isArray(instagramPost.hashtags) ? instagramPost.hashtags.join(' ') : instagramPost.hashtags }}</span>
                    </div>
                  </div>

                  <!-- Raw Data (for debugging) -->
                  <details class="raw-data-section">
                    <summary>View Raw Data</summary>
                    <pre class="raw-data">{{ JSON.stringify(instagramPost, null, 2) }}</pre>
                  </details>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="instagram-placeholder">
            <span>Instagram post preparation will appear here...</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import { marked } from 'marked';

export default {
  name: 'CampaignDetails',
  components: {},
  props: {
    campaignData: {
      type: Object,
      default: () => ({})
    },
    activeAgent: {
      type: String,
      default: ''
    }
  },
  emits: ['send-message'],
  setup(props, { emit }) {
    // Track which sections are expanded (multiple can be open)
    const expandedSections = ref({
      brief: true,
      media: false,
      localization: false,
      schedule: false,
      instagram: false
    });
    const editedCaptions = ref({});
    const editedLocalizations = ref({});

    // Computed properties from campaignData
    const brief = computed(() => props.campaignData?.brief || '');
    const isFormattedBrief = computed(() => props.campaignData?.isFormattedBrief || false);
    const needsApproval = computed(() => props.campaignData?.needsApproval || false);
    const needsCreativeApproval = computed(() => props.campaignData?.needsCreativeApproval || false);
    const needsPublishingApproval = computed(() => props.campaignData?.needsPublishingApproval || false);
    const needsLocalizationApproval = computed(() => props.campaignData?.needsLocalizationApproval || false);
    const needsMarketSelection = computed(() => props.campaignData?.needsMarketSelection || false);
    // NEW: Separate variable for publishing schedule approval to avoid conflicts
    const needsScheduleApproval = computed(() => props.campaignData?.needsScheduleApproval || false);
    const media = computed(() => props.campaignData?.media || []);
    const schedule = computed(() => props.campaignData?.schedule || []);
    const localizations = computed(() => props.campaignData?.localizations || []);
    const instagramPost = computed(() => props.campaignData?.instagram_post || null);

    // Smart loading states - show loading only when agent is active AND we don't have content yet
    const isBriefLoading = computed(() => {
      return props.activeAgent === 'campaign_planner' && !brief.value;
    });
    const isMediaLoading = computed(() => {
      return props.activeAgent === 'creative' && media.value.length === 0;
    });
    const isLocalizationLoading = computed(() => {
      return props.activeAgent === 'localization' && localizations.value.length === 0;
    });
    const isPublishingLoading = computed(() => {
      return props.activeAgent === 'publishing' && schedule.value.length === 0;
    });
    const isInstagramLoading = computed(() => {
      return props.activeAgent === 'instagram' && !instagramPost.value;
    });

    // Debug: Watch activeAgent changes
    watch(() => props.activeAgent, (newActiveAgent, oldActiveAgent) => {
      console.log('🎯 ActiveAgent changed:', { 
        old: oldActiveAgent, 
        new: newActiveAgent,
        isBriefLoading: isBriefLoading.value,
        isMediaLoading: isMediaLoading.value,
        isLocalizationLoading: isLocalizationLoading.value,
        isPublishingLoading: isPublishingLoading.value,
        isInstagramLoading: isInstagramLoading.value
      });
    }, { immediate: true });

    // Content flags
    const hasBriefContent = computed(() => brief.value && isFormattedBrief.value && !isBriefLoading.value);
    const hasScheduleContent = computed(() => schedule.value.length > 0);
    const hasInstagramContent = computed(() => instagramPost.value && !isInstagramLoading.value);

    // Watch for media changes
    watch(media, (newMedia) => {
      if (newMedia.length > 0) {
        newMedia.forEach((item, index) => {
          if (item.caption && !editedCaptions.value[index]) {
            editedCaptions.value[index] = item.caption;
          }
        });
      }
    }, { deep: true });

    // Watch for localizations changes
    watch(localizations, (newLocalizations) => {
      if (newLocalizations.length > 0) {
        newLocalizations.forEach((item, index) => {
          if (!editedLocalizations.value[index]) {
            editedLocalizations.value[index] = item;
          }
        });
      }
    }, { deep: true });

    // Auto-expand sections when their workflow stage starts or needs approval
    watch(
      () => [
        props.activeAgent,
        needsApproval.value,
        needsCreativeApproval.value,
        needsPublishingApproval.value,
        needsLocalizationApproval.value,
        hasInstagramContent.value
      ],
      () => {
        // Open sections based on active agent or approval needs
        if (needsApproval.value || props.activeAgent === 'campaign_planner') {
          expandedSections.value.brief = true;
        }
        if (needsCreativeApproval.value || props.activeAgent === 'creative') {
          expandedSections.value.media = true;
        }
        if (needsLocalizationApproval.value || props.activeAgent === 'localization') {
          expandedSections.value.localization = true;
        }
        if (needsPublishingApproval.value || props.activeAgent === 'publishing') {
          expandedSections.value.schedule = true;
        }
        if (props.activeAgent === 'instagram' || hasInstagramContent.value) {
          expandedSections.value.instagram = true;
        }
      },
      { immediate: true }
    );

    const renderMarkdown = (content) => {
      try {
        return marked.parse(content);
      } catch (error) {
        console.error('Error rendering markdown:', error);
        return content;
      }
    };

    const toggleSection = (section) => {
      expandedSections.value[section] = !expandedSections.value[section];
    };

    const handleCaptionEdit = (index, e) => {
      const text = e.target.innerText;
      editedCaptions.value[index] = text;
    };

    const handleLocalizationEdit = (index, e) => {
      const text = e.target.innerText;
      if (!editedLocalizations.value[index]) {
        editedLocalizations.value[index] = { ...localizations.value[index] };
      }
      editedLocalizations.value[index].caption = text;
    };

    const handleApproval = (approved) => {
      console.log('handleApproval called with approved:', approved);

      if (approved) {
        if (needsApproval.value) {
          emit('send-message', 'approve');
        } else if (needsCreativeApproval.value) {
          const hasEdits = media.value.some((item, index) => {
            return editedCaptions.value[index] && editedCaptions.value[index] !== item.caption;
          });

          if (hasEdits) {
            const editedMediaData = media.value.map((item, index) => {
              if (editedCaptions.value[index] && editedCaptions.value[index] !== item.caption) {
                return { ...item, caption: editedCaptions.value[index] };
              }
              return item;
            });
            emit('send-message', `approve: ${JSON.stringify({ media: editedMediaData })}`);
          } else {
            emit('send-message', 'approve');
          }
        } else if (needsLocalizationApproval.value) {
          const hasEdits = Object.keys(editedLocalizations.value).some(
            (index) =>
              JSON.stringify(editedLocalizations.value[index]) !==
              JSON.stringify(localizations.value[index])
          );

          if (hasEdits) {
            emit('send-message', `approve: ${JSON.stringify({
              localizations: Object.values(editedLocalizations.value)
            })}`);
          } else {
            emit('send-message', 'approve');
          }
        } else {
          emit('send-message', 'approve');
        }
      } else {
        emit('send-message', 'reject');
      }
    };

    // NEW: Separate approval handler for publishing schedule to avoid conflicts
    const handleScheduleApproval = (approved) => {
      if (approved) {
        // Send confirmation message to chat
        emit('send-message', 'Campaign approved! Scheduling first Instagram post...');
        
        // Auto-expand Instagram section
        expandedSections.value.instagram = true;
        
        // Send the actual approval command
        emit('send-message', 'approve_schedule');
      } else {
        emit('send-message', 'reject_schedule');
      }
    };

    // Helper methods for schedule table
    const getLanguageFlag = (language) => {
      const langCode = (language || '').toLowerCase();
      const flagMap = {
        'en': '🇺🇸',
        'es': '🇪🇸', 
        'es-es': '🇪🇸',
        'es-mx': '🇲🇽',
        'es-la': '🇲🇽',
        'fr': '🇫🇷',
        'fr-fr': '🇫🇷',
        'de': '🇩🇪',
        'de-de': '🇩🇪',
        'pt': '🇧🇷',
        'pt-br': '🇧🇷',
        'it': '🇮🇹',
        'zh': '🇨🇳',
        'ja': '🇯🇵',
        'ko': '🇰🇷'
      };
      return flagMap[langCode] || '🌐';
    };

    const getLanguageClass = (language) => {
      const langCode = (language || '').toLowerCase();
      if (langCode.includes('en')) return 'lang-english';
      if (langCode.includes('es')) return 'lang-spanish';
      if (langCode.includes('fr')) return 'lang-french';
      if (langCode.includes('de')) return 'lang-german';
      if (langCode.includes('pt')) return 'lang-portuguese';
      if (langCode.includes('it')) return 'lang-italian';
      if (langCode.includes('zh')) return 'lang-chinese';
      if (langCode.includes('ja')) return 'lang-japanese';
      if (langCode.includes('ko')) return 'lang-korean';
      return 'lang-default';
    };

    const formatDate = (dateString) => {
      if (!dateString) return 'TBD';
      try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric',
          year: 'numeric'
        });
      } catch {
        return dateString.split(' ')[0] || 'TBD';
      }
    };

    const formatTime = (dateString) => {
      if (!dateString) return '';
      try {
        const date = new Date(dateString);
        return date.toLocaleTimeString('en-US', { 
          hour: 'numeric', 
          minute: '2-digit',
          hour12: true
        });
      } catch {
        return dateString.split(' ')[1] || '';
      }
    };

    // Instagram helper methods
    const getStatusClass = (status) => {
      switch (status) {
        case 'ready_to_publish': return 'status-ready';
        case 'scheduled': return 'status-scheduled';
        case 'draft': return 'status-draft';
        case 'published': return 'status-published';
        default: return 'status-unknown';
      }
    };

    const formatStatus = (status) => {
      switch (status) {
        case 'ready_to_publish': return 'Ready to Publish';
        case 'scheduled': return 'Scheduled';
        case 'draft': return 'Draft';
        case 'published': return 'Published';
        default: return status || 'Unknown';
      }
    };

    const formatDateTime = (dateString) => {
      if (!dateString) return 'Not scheduled';
      try {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
          hour12: true
        });
      } catch {
        return dateString;
      }
    };

    return {
      expandedSections,
      editedCaptions,
      editedLocalizations,
      brief,
      isFormattedBrief,
      needsApproval,
      needsCreativeApproval,
      needsPublishingApproval,
      needsLocalizationApproval,
      needsMarketSelection,
      needsScheduleApproval,
      media,
      schedule,
      localizations,
      instagramPost,
      isBriefLoading,
      isMediaLoading,
      isLocalizationLoading,
      isPublishingLoading,
      isInstagramLoading,
      hasBriefContent,
      hasScheduleContent,
      hasInstagramContent,
      renderMarkdown,
      toggleSection,
      handleCaptionEdit,
      handleLocalizationEdit,
      handleApproval,
      handleScheduleApproval,
      getLanguageFlag,
      getLanguageClass,
      formatDate,
      formatTime,
      getStatusClass,
      formatStatus,
      formatDateTime
    };
  }
};
</script>

<style scoped>
.campaign-details {
  flex: 1;
  overflow-y: auto;
  background: #ffffff;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.details-content {
  padding: 1.5rem;
  flex: 1;
}

.accordion-section {
  margin-bottom: 1rem;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  background: #ffffff;
  transition: all 0.2s;
}

/* .accordion-section.needs-approval {
  border-color: #fb8500;
  box-shadow: 0 0 0 3px rgba(251, 133, 0, 0.1);
} */

.accordion-header {
  padding: 1rem 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  background: #f6f8fa;
  border-radius: 8px 8px 0 0;
  transition: background 0.2s;
}

.accordion-header:hover {
  background: #eaeef2;
}

.accordion-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1f2328;
}

.accordion-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.approval-indicator {
  color: #fb8500;
  font-size: 1.25rem;
}

.content-indicator {
  color: #2da44e;
  font-size: 1.25rem;
}

.accordion-icon {
  color: #6e7781;
  font-size: 0.875rem;
}

.accordion-content {
  padding: 1.25rem;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #0969da;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 1rem;
  color: #6e7781;
  font-size: 0.95rem;
}

.placeholder,
.media-placeholder,
.schedule-placeholder {
  color: #6e7781;
  font-style: italic;
  text-align: center;
  padding: 2rem;
}

.brief-content {
  line-height: 1.6;
  color: #1f2328;
}

.brief-content.markdown-content :deep(h1),
.brief-content.markdown-content :deep(h2),
.brief-content.markdown-content :deep(h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.brief-content.markdown-content :deep(ul),
.brief-content.markdown-content :deep(ol) {
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

.brief-content.markdown-content :deep(p) {
  margin: 0.5rem 0;
}

.user-input {
  background: #f6f8fa;
  padding: 1rem;
  border-radius: 6px;
  border-left: 3px solid #0969da;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.media-item {
  border: 1px solid #d0d7de;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
  transition: all 0.2s;
}

.media-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.media-image,
.media-video {
  width: 100%;
  height: auto;
  display: block;
}

.media-caption,
.editable-caption {
  padding: 0.75rem;
  font-size: 0.9rem;
  color: #1f2328;
  line-height: 1.5;
}

.editable-caption {
  /* background: #fff8dc;
  border-top: 2px solid #fb8500; */
  cursor: text;
  min-height: 50px;
}

.editable-caption:focus {
  outline: none;
  background: #ffffff;
}

.localization-meta {
  padding: 0.5rem 0.75rem;
  background: #f6f8fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.localization-language {
  font-weight: 600;
  color: #0969da;
}

.localization-hashtags {
  color: #6e7781;
}

.schedule-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.schedule-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #f6f8fa;
}

.schedule-channel {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.channel-icon {
  font-size: 1.25rem;
}

.schedule-time {
  color: #6e7781;
  font-size: 0.9rem;
}

.schedule-status {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.schedule-status.scheduled {
  background: #ddf4ff;
  color: #0969da;
}

.schedule-status.published {
  background: #dafbe1;
  color: #1a7f37;
}

.approval-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #d0d7de;
}

.approve-btn,
.reject-btn {
  flex: 1;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.95rem;
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

/* Localized content styling */
.media-container {
  position: relative;
}

.language-pills {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  max-width: calc(100% - 16px);
}

.language-pill {
  background: rgba(0, 0, 0, 0.75);
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.original-caption {
  background: #f6f8fa;
  border-left: 3px solid #0969da;
  margin-bottom: 0.5rem;
}

.localized-caption {
  margin-bottom: 0.75rem;
  padding: 0.5rem;
  border: 1px solid #d0d7de;
  border-radius: 4px;
  background: #ffffff;
}

.localized-caption:last-child {
  margin-bottom: 0;
}

.localized-caption .localization-meta {
  margin-bottom: 0.25rem;
}

.localized-caption .media-caption {
  margin: 0;
  padding: 0;
  background: transparent;
  border: none;
}

/* .media-hashtags {
  margin-top: 0.5rem;
  color: #0969da;
  font-weight: 500;
  font-size: 0.9rem;
} */

/* Publishing Schedule Table */
.schedule-table-container {
  margin: 1rem 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #d0d7de;
  background: white;
}

.schedule-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.schedule-table th {
  background: #f6f8fa;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #24292f;
  border-bottom: 2px solid #d0d7de;
}

.schedule-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #d0d7de;
  vertical-align: middle;
}

.schedule-row:hover {
  background: #f6f8fa;
}

.platform-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.platform-icon {
  font-size: 1.1rem;
}

.platform-name {
  font-weight: 500;
}

.language-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

/* Language-specific colors */
.language-badge.lang-english {
  background: #dbeafe;
  color: #1e40af;
}

.language-badge.lang-spanish {
  background: #fef3c7;
  color: #d97706;
}

.language-badge.lang-french {
  background: #e0e7ff;
  color: #5b21b6;
}

.language-badge.lang-german {
  background: #dcfce7;
  color: #166534;
}

.language-badge.lang-portuguese {
  background: #fecaca;
  color: #dc2626;
}

.language-badge.lang-italian {
  background: #fed7d7;
  color: #c53030;
}

.language-badge.lang-chinese {
  background: #fce7f3;
  color: #be185d;
}

.language-badge.lang-japanese {
  background: #f3e8ff;
  color: #7c3aed;
}

.language-badge.lang-korean {
  background: #ecfdf5;
  color: #065f46;
}

.language-badge.lang-default {
  background: #f3f4f6;
  color: #374151;
}

.media-preview {
  display: flex;
  align-items: center;
}

.media-thumbnail {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #d0d7de;
}

.video-thumbnail {
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.video-thumbnail::after {
  content: '▶️';
  position: absolute;
  font-size: 0.8rem;
  color: white;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
}

.media-type {
  padding: 0.5rem;
  background: #f6f8fa;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #656d76;
}

.schedule-time {
  text-align: left;
}

.schedule-time .date {
  font-weight: 500;
  color: #24292f;
}

.schedule-time .time {
  font-size: 0.8rem;
  color: #656d76;
  margin-top: 0.1rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.status-badge.ready {
  background: #ddf4ff;
  color: #0969da;
}

.status-badge.published {
  background: #dcfce7;
  color: #166534;
}

.status-badge.failed {
  background: #ffe4e6;
  color: #dc2626;
}

/* Instagram Post Styles */
.instagram-post-container {
  border: 1px solid #d0d7de;
  border-radius: 8px;
  padding: 1rem;
  background: #ffffff;
}

.instagram-post-header {
  display: flex;
  justify-content: between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #eaeef2;
}

.platform-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.platform-icon {
  font-size: 1.2rem;
}

.platform-name {
  font-weight: 600;
  color: #1f2328;
}

.content-type {
  background: #f6f8fa;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  color: #656d76;
}

.post-status {
  margin-left: auto;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.status-ready {
  background: #ddf4ff;
  color: #0969da;
}

.status-scheduled {
  background: #fff8c5;
  color: #b58900;
}

.status-draft {
  background: #f6f8fa;
  color: #656d76;
}

.status-published {
  background: #dcfce7;
  color: #166534;
}

.status-unknown {
  background: #ffe4e6;
  color: #dc2626;
}

.instagram-post-content {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.media-preview-large {
  flex-shrink: 0;
  width: 200px;
}

.instagram-media {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #d0d7de;
}

.post-details {
  flex: 1;
}

.detail-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  align-items: center;
}

.detail-label {
  font-weight: 600;
  color: #656d76;
  min-width: 100px;
}

.detail-value {
  color: #1f2328;
  flex: 1;
}

.caption-section, .hashtags-section {
  margin-top: 1rem;
}

.instagram-caption {
  background: #f6f8fa;
  padding: 0.75rem;
  border-radius: 6px;
  margin-top: 0.5rem;
  color: #1f2328;
  line-height: 1.5;
}

/* .instagram-hashtags {
  background: #ddf4ff;
  padding: 0.5rem;
  border-radius: 6px;
  margin-top: 0.5rem;
  color: #0969da;
  font-family: monospace;
  font-size: 0.9rem;
} */

.raw-data-section {
  margin-top: 1.5rem;
  border-top: 1px solid #eaeef2;
  padding-top: 1rem;
}

.raw-data-section summary {
  cursor: pointer;
  color: #656d76;
  font-size: 0.9rem;
}

.raw-data {
  background: #f6f8fa;
  padding: 0.75rem;
  border-radius: 6px;
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: #1f2328;
  overflow-x: auto;
}

.success-message {
  background: #dcfce7;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  padding: 0.75rem;
  margin-top: 1rem;
}

.success-text {
  color: #166534;
  font-weight: 600;
  margin-top: 0.25rem;
}

.post-link {
  color: #059669;
  font-size: 0.9rem;
  margin-top: 0.25rem;
  font-family: monospace;
}

.error-message {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 0.75rem;
  margin-top: 1rem;
}

.error-text {
  color: #dc2626;
  font-weight: 600;
  margin-top: 0.25rem;
}

.error-details {
  color: #991b1b;
  font-size: 0.9rem;
  margin-top: 0.25rem;
}

.instagram-placeholder {
  text-align: center;
  padding: 2rem;
  color: #656d76;
  font-style: italic;
}
</style>
