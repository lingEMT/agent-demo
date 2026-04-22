<template>
  <div id="app">
    <a-layout style="min-height: 100vh">
      <a-layout-header style="background: #001529; padding: 0 50px; display: flex; align-items: center; justify-content: space-between;">
        <div style="color: white; font-size: 24px; font-weight: bold">
          🌍 HelloAgents智能旅行助手
        </div>
        <a-menu
          v-model:selectedKeys="['1']"
          theme="dark"
          mode="horizontal"
          style="flex: 1; margin-left: 50px; min-width: 300px"
        >
          <a-menu-item key="1">
            <router-link to="/" style="color: white; text-decoration: none;">
              首页
            </router-link>
          </a-menu-item>
          <a-menu-item key="2">
            <router-link to="/result" style="color: white; text-decoration: none;">
              结果页
            </router-link>
          </a-menu-item>
          <a-menu-item key="3">
            <router-link to="/token-monitor" style="color: white; text-decoration: none;">
              Token监控
            </router-link>
          </a-menu-item>
        </a-menu>
      </a-layout-header>
      <a-layout-content style="padding: 24px">
        <router-view />
      </a-layout-content>
      <a-layout-footer style="text-align: center">
        HelloAgents智能旅行助手 ©2025 基于HelloAgents框架
      </a-layout-footer>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
}
</style>

