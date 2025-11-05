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
              {{ expandedSection === 'brief' ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSection === 'brief'" class="accordion-content">
          <div v-if="isBriefLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Generating campaign strategy...</p>
          </div>
          <template v-else-if="brief">
            <EditableMarkdown
              v-if="needsApproval"
              v-model="editedBrief"
              class="editable-brief-markdown"
            />
            <div
              v-else
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
            <span class="accordion-icon">
              {{ expandedSection === 'media' ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSection === 'media'" class="accordion-content">
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
                  v-if="item.caption"
                  :contenteditable="needsCreativeApproval"
                  :class="needsCreativeApproval ? 'editable-caption' : 'media-caption'"
                  @input="(e) => handleCaptionEdit(index, e)"
                  @blur="(e) => handleCaptionEdit(index, e)"
                >
                  {{ editedCaptions[index] || item.caption }}
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
        :class="['accordion-section', { 'needs-approval': needsLocalizationApproval }]"
      >
        <div class="accordion-header" @click="toggleSection('localization')">
          <h3>Localized Content</h3>
          <div class="accordion-controls">
            <span v-if="needsLocalizationApproval" class="approval-indicator">⚠</span>
            <span v-else-if="localizations.length > 0" class="content-indicator">✓</span>
            <span class="accordion-icon">
              {{ expandedSection === 'localization' ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSection === 'localization'" class="accordion-content">
          <div v-if="isLocalizationLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Generating localized content...</p>
          </div>
          <template v-else-if="localizations.length > 0">
            <div
              :class="['media-grid', { 'pending-approval': needsLocalizationApproval }]"
            >
              <div
                v-for="(item, index) in localizations"
                :key="index"
                class="media-item"
              >
                <img
                  v-if="item.image"
                  :src="item.image"
                  :alt="`${item.language} localization`"
                  class="media-image"
                />
                <div
                  v-if="item.caption"
                  :contenteditable="needsLocalizationApproval"
                  :class="needsLocalizationApproval ? 'editable-caption' : 'media-caption'"
                  @input="(e) => handleLocalizationEdit(index, e)"
                  @blur="(e) => handleLocalizationEdit(index, e)"
                >
                  {{ editedLocalizations[index]?.caption || item.caption }}
                </div>
                <div class="localization-meta">
                  <span class="localization-language">
                    {{ item.language || 'Unknown' }}
                  </span>
                  <span v-if="item.hashtags" class="localization-hashtags">
                    {{ item.hashtags }}
                  </span>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="media-placeholder">
            <span>Localized content will appear here...</span>
          </div>
          <div
            v-if="needsLocalizationApproval && localizations.length > 0 && !isLocalizationLoading"
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

      <!-- Schedule Accordion -->
      <div
        :class="['accordion-section', { 'needs-approval': needsPublishingApproval }]"
      >
        <div class="accordion-header" @click="toggleSection('schedule')">
          <h3>Publish Schedule</h3>
          <div class="accordion-controls">
            <span v-if="needsPublishingApproval" class="approval-indicator">⚠</span>
            <span v-else-if="hasScheduleContent" class="content-indicator">✓</span>
            <span class="accordion-icon">
              {{ expandedSection === 'schedule' ? '▲' : '▼' }}
            </span>
          </div>
        </div>
        <div v-if="expandedSection === 'schedule'" class="accordion-content">
          <template v-if="schedule.length > 0">
            <div
              :class="['schedule-list', { 'pending-approval': needsPublishingApproval }]"
            >
              <div
                v-for="(item, index) in schedule.slice(0, 3)"
                :key="index"
                class="schedule-item"
              >
                <div class="schedule-channel">
                  <span class="channel-icon">{{ item.icon || '📱' }}</span>
                  <strong>{{ item.channel }}</strong>
                </div>
                <div class="schedule-time">{{ item.datetime }}</div>
                <div
                  v-if="item.status"
                  :class="['schedule-status', item.status]"
                >
                  {{ item.status }}
                </div>
              </div>
            </div>
            <div v-if="needsPublishingApproval" class="approval-actions">
              <button class="approve-btn" @click="handleApproval(true)">
                ✓ Approve
              </button>
              <button class="reject-btn" @click="handleApproval(false)">
                ✗ Reject
              </button>
            </div>
          </template>
          <div v-else class="schedule-placeholder">
            <span>Publish schedule will appear here...</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import { marked } from 'marked';
import EditableMarkdown from './EditableMarkdown.vue';

export default {
  name: 'CampaignDetails',
  components: {
    EditableMarkdown
  },
  props: {
    campaignData: {
      type: Object,
      default: () => ({})
    },
    loadingStates: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['send-message'],
  setup(props, { emit }) {
    const expandedSection = ref('brief');
    const editedBrief = ref('');
    const editedCaptions = ref({});
    const editedLocalizations = ref({});

    // Computed properties from campaignData
    const brief = computed(() => props.campaignData?.brief || '');
    const isFormattedBrief = computed(() => props.campaignData?.isFormattedBrief || false);
    const needsApproval = computed(() => props.campaignData?.needsApproval || false);
    const needsCreativeApproval = computed(() => props.campaignData?.needsCreativeApproval || false);
    const needsPublishingApproval = computed(() => props.campaignData?.needsPublishingApproval || false);
    const needsLocalizationApproval = computed(() => props.campaignData?.needsLocalizationApproval || false);
    const media = computed(() => props.campaignData?.media || []);
    const schedule = computed(() => props.campaignData?.schedule || []);
    const localizations = computed(() => props.campaignData?.localizations || []);

    // Loading states
    const isBriefLoading = computed(() => props.loadingStates.campaignBrief || false);
    const isMediaLoading = computed(() => props.loadingStates.socialMedia || false);
    const isLocalizationLoading = computed(() => props.loadingStates.localization || false);

    // Content flags
    const hasBriefContent = computed(() => isBriefLoading.value || brief.value);
    const hasScheduleContent = computed(() => schedule.value.length > 0);

    // Watch for brief changes
    watch(brief, (newBrief) => {
      if (newBrief && newBrief !== editedBrief.value) {
        editedBrief.value = newBrief;
      }
    });

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

    // Auto-expand the section that needs attention
    watch(
      () => [
        needsApproval.value,
        needsCreativeApproval.value,
        needsPublishingApproval.value,
        needsLocalizationApproval.value,
        brief.value,
        media.value.length,
        schedule.value.length,
        localizations.value.length
      ],
      () => {
        if (needsCreativeApproval.value || (media.value.length > 0 && !needsApproval.value)) {
          expandedSection.value = 'media';
        } else if (needsPublishingApproval.value || schedule.value.length > 0) {
          expandedSection.value = 'schedule';
        } else if (needsLocalizationApproval.value || localizations.value.length > 0) {
          expandedSection.value = 'localization';
        } else if (needsApproval.value || brief.value) {
          expandedSection.value = 'brief';
        }
      }
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
      expandedSection.value = expandedSection.value === section ? null : section;
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
        if (needsApproval.value && editedBrief.value !== brief.value) {
          emit('send-message', `approve: ${editedBrief.value}`);
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

    return {
      expandedSection,
      editedBrief,
      editedCaptions,
      editedLocalizations,
      brief,
      isFormattedBrief,
      needsApproval,
      needsCreativeApproval,
      needsPublishingApproval,
      needsLocalizationApproval,
      media,
      schedule,
      localizations,
      isBriefLoading,
      isMediaLoading,
      isLocalizationLoading,
      hasBriefContent,
      hasScheduleContent,
      renderMarkdown,
      toggleSection,
      handleCaptionEdit,
      handleLocalizationEdit,
      handleApproval
    };
  }
};
</script>

<style scoped>
.campaign-details {
  flex: 1;
  overflow-y: auto;
  background: #ffffff;
}

.details-content {
  padding: 1.5rem;
}

.accordion-section {
  margin-bottom: 1rem;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  background: #ffffff;
  transition: all 0.2s;
}

.accordion-section.needs-approval {
  border-color: #fb8500;
  box-shadow: 0 0 0 3px rgba(251, 133, 0, 0.1);
}

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
  background: #fff8dc;
  border-top: 2px solid #fb8500;
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
</style>
