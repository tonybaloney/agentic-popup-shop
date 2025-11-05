<template>
  <div id="marketing-app">
    <MarketingHeader />
    <main class="marketing-content">
      <router-view />
    </main>
  </div>
</template>

<script>
import MarketingHeader from '../components/MarketingHeader.vue';

export default {
  name: 'MarketingLayout',
  components: {
    MarketingHeader
  }
};
</script>

<style scoped>
#marketing-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.marketing-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
