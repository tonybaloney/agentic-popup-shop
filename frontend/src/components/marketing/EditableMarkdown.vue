<template>
  <div class="editable-markdown">
    <div
      v-if="!isEditing"
      ref="previewRef"
      class="markdown-preview"
      @click="handlePreviewClick"
      v-html="renderMarkdown(modelValue)"
    ></div>
    <textarea
      v-else
      ref="textareaRef"
      :value="modelValue"
      @input="handleTextChange"
      @blur="handleBlur"
      class="markdown-textarea"
      spellcheck="true"
    ></textarea>
  </div>
</template>

<script>
import { ref, nextTick } from 'vue';
import { marked } from 'marked';

export default {
  name: 'EditableMarkdown',
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const isEditing = ref(false);
    const textareaRef = ref(null);
    const previewRef = ref(null);

    const handlePreviewClick = () => {
      isEditing.value = true;
      nextTick(() => {
        if (textareaRef.value) {
          textareaRef.value.focus();
          // Set cursor to end
          const len = textareaRef.value.value.length;
          textareaRef.value.selectionStart = len;
          textareaRef.value.selectionEnd = len;
        }
      });
    };

    const handleTextChange = (e) => {
      emit('update:modelValue', e.target.value);
    };

    const handleBlur = () => {
      isEditing.value = false;
    };

    const renderMarkdown = (content) => {
      try {
        return marked.parse(content || '');
      } catch (error) {
        console.error('Error rendering markdown:', error);
        return content || '';
      }
    };

    return {
      isEditing,
      textareaRef,
      previewRef,
      handlePreviewClick,
      handleTextChange,
      handleBlur,
      renderMarkdown
    };
  }
};
</script>

<style scoped>
.editable-markdown {
  position: relative;
  width: 100%;
}

.markdown-preview {
  padding: 1rem;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: text;
  min-height: 100px;
  transition: all 0.2s;
  background: #f6f8fa;
}

.markdown-preview:hover {
  border-color: #0969da;
  background: #ffffff;
}

.markdown-preview::after {
  content: '✏️ Click to edit';
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  font-size: 0.75rem;
  color: #6e7781;
  opacity: 0;
  transition: opacity 0.2s;
}

.markdown-preview:hover::after {
  opacity: 1;
}

.markdown-textarea {
  width: 100%;
  min-height: 200px;
  padding: 1rem;
  border: 2px solid #0969da;
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.6;
  resize: vertical;
  background: #ffffff;
}

.markdown-textarea:focus {
  outline: none;
  border-color: #0550ae;
  box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.1);
}

/* Markdown styling in preview */
.markdown-preview :deep(h1),
.markdown-preview :deep(h2),
.markdown-preview :deep(h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #1f2328;
}

.markdown-preview :deep(h1) {
  font-size: 1.5rem;
  border-bottom: 2px solid #d0d7de;
  padding-bottom: 0.5rem;
}

.markdown-preview :deep(h2) {
  font-size: 1.25rem;
  border-bottom: 1px solid #d0d7de;
  padding-bottom: 0.3rem;
}

.markdown-preview :deep(h3) {
  font-size: 1.1rem;
}

.markdown-preview :deep(p) {
  margin: 0.75rem 0;
  line-height: 1.6;
}

.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  padding-left: 1.5rem;
  margin: 0.75rem 0;
}

.markdown-preview :deep(li) {
  margin: 0.25rem 0;
}

.markdown-preview :deep(strong) {
  font-weight: 600;
  color: #1f2328;
}

.markdown-preview :deep(code) {
  background: #f6f8fa;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: ui-monospace, monospace;
}
</style>
