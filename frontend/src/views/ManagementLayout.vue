<template>
  <div id="management-app">
    <ManagementHeader />
    <main class="management-content">
      <router-view />
    </main>
  </div>
</template>

<script>
import ManagementHeader from '../components/ManagementHeader.vue';

export default {
  name: 'ManagementLayout',
  components: {
    ManagementHeader
  }
};
</script>

<style scoped>
#management-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.management-content {
  flex: 1;
  padding: 1.5rem 0;
}
</style>
