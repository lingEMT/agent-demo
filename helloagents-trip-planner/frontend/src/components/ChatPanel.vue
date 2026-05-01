<template>
  <div class="chat-panel">
    <!-- 顶部：版本标签栏 -->
    <div class="chat-header">
      <div class="version-tabs">
        <a-tabs
          v-model:activeKey="currentVersionKey"
          size="small"
          type="card"
          @change="onVersionChange"
        >
          <a-tab-pane
            v-for="ver in versions"
            :key="String(ver.version_number)"
            :tab="`v${ver.version_number}`"
          />
          <!-- 超过30个版本时折叠 -->
          <template v-if="versions.length > 30" #addon>
            <a-dropdown>
              <template #overlay>
                <a-menu @click="onVersionDropdownChange">
                  <a-menu-item
                    v-for="ver in collapsedVersions"
                    :key="String(ver.version_number)"
                  >
                    v{{ ver.version_number }}
                    <span v-if="ver.modification_request">
                      - {{ truncateText(ver.modification_request, 20) }}
                    </span>
                  </a-menu-item>
                </a-menu>
              </template>
              <a-button size="small" type="link">更多...</a-button>
            </a-dropdown>
          </template>
        </a-tabs>
      </div>
    </div>

    <!-- 中间：消息列表 -->
    <div class="chat-messages" ref="messagesRef">
      <!-- 空状态 -->
      <div v-if="messages.length === 0 && !loading" class="empty-state">
        <div class="empty-icon">💬</div>
        <p class="empty-text">开始修改您的计划</p>
        <p class="empty-hint">输入修改请求，AI将为您调整行程</p>
      </div>

      <!-- 加载中 -->
      <div v-if="loadingVersions" class="loading-state">
        <a-spin size="small" />
        <span class="loading-text">加载版本历史...</span>
      </div>

      <!-- 消息列表 -->
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="message-item"
        :class="[`message-${msg.role}`]"
      >
        <div class="message-avatar">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </div>
        <div class="message-bubble">
          <div class="message-content">{{ msg.content }}</div>
          <div class="message-meta">
            <span v-if="msg.version_number" class="version-badge">
              v{{ msg.version_number }}
            </span>
            <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
        </div>
      </div>

      <!-- 流式加载指示器 -->
      <div v-if="streaming" class="message-item message-assistant">
        <div class="message-avatar">🤖</div>
        <div class="message-bubble streaming-bubble">
          <div class="streaming-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
          <div class="streaming-text">正在修改计划...</div>
        </div>
      </div>

      <!-- 错误消息 -->
      <div v-if="errorMsg" class="message-item message-system">
        <div class="message-avatar">⚠️</div>
        <div class="message-bubble error-bubble">
          <div class="message-content">{{ errorMsg }}</div>
        </div>
      </div>
    </div>

    <!-- 底部：输入框 -->
    <div class="chat-input-area">
      <div class="input-wrapper">
        <a-textarea
          v-model:value="inputText"
          placeholder="输入修改请求，例如：第二天轻松些..."
          :rows="2"
          :disabled="streaming || loadingVersions"
          @pressEnter="sendMessage"
          class="chat-textarea"
        />
        <a-button
          type="primary"
          :loading="streaming"
          :disabled="!inputText.trim() || loadingVersions"
          @click="sendMessage"
          class="send-button"
        >
          <template v-if="!streaming">发送</template>
          <template v-else>修改中</template>
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { modifyTripPlanStream, getConversation } from '@/services/api'
import type { PlanVersion, ChatMessage, TripPlan, TripPlanMeta } from '@/types'

const props = defineProps<{
  planId: string
  conversationId: string
  sessionId: string
  currentPlan: TripPlan | null
}>()

const emit = defineEmits<{
  (e: 'plan-changed', plan: TripPlan, planId: string, versionNumber: number): void
}>()

// 状态
const messages = ref<ChatMessage[]>([])
const versions = ref<PlanVersion[]>([])
const inputText = ref('')
const streaming = ref(false)
const loading = ref(false)
const loadingVersions = ref(false)
const errorMsg = ref('')
const currentVersionKey = ref('1')
const messagesRef = ref<HTMLElement | null>(null)

// 超过30个版本时折叠
const collapsedVersions = computed(() => {
  if (versions.value.length > 30) {
    return versions.value.slice(30)
  }
  return []
})

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

// 格式化时间
const formatTime = (timestamp: string): string => {
  try {
    const d = new Date(timestamp)
    return d.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

// 截断文本
const truncateText = (text: string, maxLen: number): string => {
  if (text.length <= maxLen) return text
  return text.slice(0, maxLen) + '...'
}

// 加载版本历史
const loadVersions = async () => {
  if (!props.conversationId) return

  loadingVersions.value = true
  errorMsg.value = ''

  try {
    const result = await getConversation(props.conversationId)
    if (result.success) {
      versions.value = result.versions || []

      // 生成消息列表
      const chatMessages: ChatMessage[] = []

      // 第一个版本 —— 系统消息
      const firstVer = versions.value[0]
      if (firstVer) {
        chatMessages.push({
          role: 'system',
          content: `已生成初始计划 (v${firstVer.version_number})`,
          timestamp: firstVer.created_at,
          plan_id: firstVer.id,
          version_number: firstVer.version_number,
        })
      }

      // 后续版本 —— 用户修改 + 系统回复
      for (let i = 1; i < versions.value.length; i++) {
        const ver = versions.value[i]
        if (ver.modification_request) {
          chatMessages.push({
            role: 'user',
            content: ver.modification_request,
            timestamp: ver.created_at,
            plan_id: ver.id,
            version_number: ver.version_number,
          })
          chatMessages.push({
            role: 'assistant',
            content: `已根据您的请求修改计划 (v${ver.version_number})`,
            timestamp: ver.created_at,
            plan_id: ver.id,
            version_number: ver.version_number,
          })
        }
      }

      messages.value = chatMessages

      // 设置当前版本为最新
      const latestVer = versions.value.find((v) => v.is_current)
      if (latestVer) {
        currentVersionKey.value = String(latestVer.version_number)
      }

      await scrollToBottom()
    }
  } catch (e: any) {
    console.error('加载版本历史失败:', e)
    errorMsg.value = '加载版本历史失败'
  } finally {
    loadingVersions.value = false
  }
}

// 发送消息
const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || streaming.value || loadingVersions.value) return

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: text,
    timestamp: new Date().toISOString(),
  })

  inputText.value = ''
  streaming.value = true
  errorMsg.value = ''

  await scrollToBottom()

  try {
    // 使用当前最新的 plan_id 作为修改基础
    const currentPlanId = versions.value.find((v) => v.is_current)?.id || props.planId

    await modifyTripPlanStream(
      currentPlanId,
      text,
      props.sessionId,
      {
        onProgress: () => {
          // 进度更新可忽略
        },
        onFinalResult: (data) => {
          if (data.success && data.data) {
            const planData = data.data as TripPlan & { _meta?: any }
            const meta = planData._meta || {}

            // 添加系统回复
            const newVersionNumber = meta.version_number || 1
            const newPlanId = meta.plan_id || currentPlanId
            messages.value.push({
              role: 'assistant',
              content: `已根据您的请求修改计划 (v${newVersionNumber})`,
              timestamp: new Date().toISOString(),
              plan_id: newPlanId,
              version_number: newVersionNumber,
            })

            // 更新版本列表
            const newVersion: PlanVersion = {
              id: newPlanId,
              version_number: newVersionNumber,
              is_current: true,
              modification_request: text,
              created_at: new Date().toISOString(),
              plan_data: planData,
            }

            // 标记旧版本为非当前
            versions.value = versions.value.map((v) => ({
              ...v,
              is_current: false,
            }))
            versions.value.push(newVersion)
            currentVersionKey.value = String(newVersionNumber)

            // 移除 _meta 后 emit 纯净的 plan 数据
            const { _meta, ...cleanPlan } = planData
            emit('plan-changed', cleanPlan as TripPlan, newPlanId, newVersionNumber)
          } else {
            errorMsg.value = data.message || '修改失败'
          }
        },
        onError: (data) => {
          errorMsg.value = data.error || '修改失败，请重试'
          message.error(data.error || '修改失败')
        },
      }
    )
  } catch (e: any) {
    errorMsg.value = e.message || '修改失败，请重试'
    message.error(e.message || '修改失败')
  } finally {
    streaming.value = false
    await scrollToBottom()
  }
}

// 切换版本
const onVersionChange = (versionKey: string | number) => {
  const ver = versions.value.find(
    (v) => v.version_number === Number(versionKey)
  )
  if (ver && ver.plan_data) {
    emit('plan-changed', ver.plan_data as TripPlan, ver.id, ver.version_number)
  }
}

// 下拉菜单切换版本
const onVersionDropdownChange = ({ key }: { key: string }) => {
  currentVersionKey.value = key
  onVersionChange(key)
}

// 监听 conversationId 变化，重新加载
watch(
  () => props.conversationId,
  (newVal) => {
    if (newVal) {
      loadVersions()
    }
  }
)

onMounted(() => {
  if (props.conversationId) {
    loadVersions()
  }
})
</script>

<style scoped>
.chat-panel {
  width: 350px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  height: fit-content;
  max-height: calc(100vh - 120px);
  position: sticky;
  top: 80px;
}

.chat-header {
  padding: 8px 12px 0;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.version-tabs :deep(.ant-tabs) {
  overflow: visible;
}

.version-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 0 !important;
}

.version-tabs :deep(.ant-tabs-tab) {
  font-size: 12px;
  padding: 4px 8px !important;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  min-height: 300px;
  max-height: 500px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 16px;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 13px;
  color: #999;
}

.loading-state {
  text-align: center;
  padding: 40px 0;
}

.loading-text {
  margin-left: 8px;
  color: #999;
}

.message-item {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  animation: fadeIn 0.3s ease;
}

.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  font-size: 24px;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  position: relative;
}

.message-user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-assistant .message-bubble {
  background: #f5f7fa;
  color: #333;
  border-bottom-left-radius: 4px;
}

.message-system .message-bubble {
  background: #fff7e6;
  color: #d46b08;
  border: 1px solid #ffd591;
}

.error-bubble {
  background: #fff2f0 !important;
  color: #cf1322 !important;
  border: 1px solid #ffccc7 !important;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  opacity: 0.7;
}

.message-user .message-meta {
  color: rgba(255, 255, 255, 0.8);
}

.message-assistant .message-meta {
  color: #999;
}

.version-badge {
  display: inline-block;
  padding: 0 6px;
  background: #667eea;
  color: white;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.message-user .version-badge {
  background: rgba(255, 255, 255, 0.3);
}

.streaming-bubble {
  min-width: 100px;
}

.streaming-dots {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: bounce 1.2s infinite ease-in-out;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
  }
  40% {
    transform: scale(1);
  }
}

.streaming-text {
  font-size: 12px;
  color: #999;
}

.chat-input-area {
  padding: 12px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
}

.input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-textarea {
  flex: 1;
  border-radius: 8px;
  resize: none;
}

.send-button {
  height: fit-content;
  padding: 8px 16px;
  border-radius: 8px;
  white-space: nowrap;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
