<template>
  <div id="app">
    <AppHeader v-if="!isMarketingPage && !isManagementPage" />
    <main class="main-content">
      <router-view />
    </main>
    <AppFooter v-if="!isMarketingPage && !isManagementPage" />
  </div>
</template>

<script>
import AppHeader from './components/AppHeader.vue';
import AppFooter from './components/AppFooter.vue';

export default {
  name: 'App',
  components: {
    AppHeader,
    AppFooter
  },
  computed: {
    isMarketingPage() {
      return this.$route && this.$route.path && this.$route.path.startsWith('/marketing');
    },
    isManagementPage() {
      return this.$route && this.$route.path && this.$route.path.startsWith('/management');
    }
  },
  watch: {
    '$route'(to, from) {
      // Force reactivity for route changes
      this.$forceUpdate();
    }
  }
};
</script>

<style>
.main-content {
  flex: 1;
}
</style>
