<template>
  <div class="history-container">
    <a-card :bordered="false" class="history-card">
      <template #title>
        <div class="card-title">
          <span>历史旅行记录</span>
          <a-tabs v-model:activeKey="viewMode" size="small" @change="onViewModeChange">
            <a-tab-pane key="records" tab="记录列表" />
            <a-tab-pane key="conversations" tab="对话视图" />
          </a-tabs>
        </div>
      </template>

      <!-- ===== 记录列表视图 ===== -->
      <template v-if="viewMode === 'records'">
        <!-- 空状态 -->
        <div v-if="!loading && records.length === 0" class="empty-state">
          <a-empty description="暂无历史记录">
            <template #image>
              <div class="empty-icon">📋</div>
            </template>
            <p class="empty-text">还没有保存的旅行计划，去生成一个吧！</p>
            <a-button type="primary" @click="goHome">开始规划旅行</a-button>
          </a-empty>
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="loading-state">
          <a-spin size="large" />
          <p class="loading-text">加载中...</p>
        </div>

        <!-- 错误状态 -->
        <div v-if="error" class="error-state">
          <a-result status="error" title="加载失败" :sub-title="error">
            <template #extra>
              <a-button type="primary" @click="fetchHistory">重新加载</a-button>
            </template>
          </a-result>
        </div>

        <!-- 历史记录表格 -->
        <a-table
          v-if="!loading && records.length > 0"
          :data-source="records"
          :columns="columns"
          :pagination="pagination"
          :loading="loading"
          row-key="id"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title'">
              <a>{{ record.title }}</a>
            </template>
            <template v-if="column.key === 'created_at'">
              {{ formatDate(record.created_at) }}
            </template>
            <template v-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="loadTrip(record.id)">
                  加载
                </a-button>
                <a-popconfirm
                  title="确定要删除这条记录吗？"
                  @confirm="deleteTrip(record.id)"
                  ok-text="确定"
                  cancel-text="取消"
                >
                  <a-button type="link" size="small" danger>
                    删除
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </template>

      <!-- ===== 对话视图 ===== -->
      <template v-if="viewMode === 'conversations'">
        <!-- 空状态 -->
        <div v-if="!loadingConvs && conversations.length === 0" class="empty-state">
          <a-empty description="暂无对话">
            <template #image>
              <div class="empty-icon">💬</div>
            </template>
            <p class="empty-text">还没有对话记录</p>
            <a-button type="primary" @click="goHome">开始规划旅行</a-button>
          </a-empty>
        </div>

        <!-- 加载中 -->
        <div v-if="loadingConvs" class="loading-state">
          <a-spin size="large" />
          <p class="loading-text">加载中...</p>
        </div>

        <!-- 错误状态 -->
        <div v-if="convError" class="error-state">
          <a-result status="error" title="加载失败" :sub-title="convError">
            <template #extra>
              <a-button type="primary" @click="fetchConversations">重新加载</a-button>
            </template>
          </a-result>
        </div>

        <!-- 对话卡片列表 -->
        <div v-if="!loadingConvs && conversations.length > 0" class="conversation-list">
          <a-card
            v-for="conv in conversations"
            :key="conv.conversation_id"
            size="small"
            class="conversation-card"
            hoverable
            @click="loadConversation(conv)"
          >
            <div class="conv-header">
              <span class="conv-title">{{ conv.title }}</span>
              <span class="conv-city">{{ conv.city }}</span>
            </div>
            <div class="conv-meta">
              <span class="conv-versions">共 {{ conv.total_versions }} 个版本</span>
              <span class="conv-date">{{ formatDate(conv.updated_at) }}</span>
            </div>
            <template #actions>
              <a-button type="link" size="small" @click.stop="loadLatestPlan(conv)">
                加载最新计划
              </a-button>
            </template>
          </a-card>

          <!-- 分页 -->
          <div v-if="totalConvs > pageSize" class="conv-pagination">
            <a-pagination
              v-model:current="convPage"
              :total="totalConvs"
              :page-size="pageSize"
              @change="onConvPageChange"
              size="small"
            />
          </div>
        </div>
      </template>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { listTripRecords, getTripRecord, deleteTripRecord, listConversations, getConversation } from '@/services/api'
import type { TripRecordSummary, ConversationSummary } from '@/types'

const router = useRouter()

const viewMode = ref<'records' | 'conversations'>('records')

// 记录列表状态
const loading = ref(false)
const error = ref<string | null>(null)
const records = ref<TripRecordSummary[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 对话列表状态
const loadingConvs = ref(false)
const convError = ref<string | null>(null)
const conversations = ref<ConversationSummary[]>([])
const totalConvs = ref(0)
const convPage = ref(1)

const columns = [
  { title: '标题', dataIndex: 'title', key: 'title' },
  { title: '城市', dataIndex: 'city', key: 'city' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', width: 150 },
]

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: false,
})

const getSessionId = (): string | null => {
  return localStorage.getItem('trip_session_id')
}

const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

// 切换视图
const onViewModeChange = (key: string) => {
  if (key === 'conversations' && conversations.value.length === 0) {
    fetchConversations()
  }
}

// ===== 记录列表 =====

const fetchHistory = async () => {
  const sessionId = getSessionId()
  if (!sessionId) {
    records.value = []
    total.value = 0
    return
  }

  loading.value = true
  error.value = null

  try {
    const result = await listTripRecords(sessionId, currentPage.value, pageSize.value)
    records.value = result.data || []
    total.value = result.total || 0
    pagination.total = total.value
    pagination.current = currentPage.value
  } catch (e: any) {
    error.value = e.message || '加载历史记录失败'
    console.error('加载历史记录失败:', e)
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: any) => {
  currentPage.value = pag.current
  pageSize.value = pag.pageSize
  fetchHistory()
}

const loadTrip = async (recordId: string) => {
  try {
    const result = await getTripRecord(recordId)
    if (result.success && result.data) {
      const planData = result.data.plan_data
      if (planData) {
        sessionStorage.setItem('tripPlan', JSON.stringify(planData))
        message.success('加载成功')
        router.push('/result')
      } else {
        message.warning('该记录没有完整的旅行计划数据')
      }
    } else {
      message.error('加载失败')
    }
  } catch (e: any) {
    message.error(e.message || '加载失败')
  }
}

const deleteTrip = async (recordId: string) => {
  try {
    const result = await deleteTripRecord(recordId)
    if (result.success) {
      message.success('删除成功')
      records.value = records.value.filter((r) => r.id !== recordId)
      total.value -= 1
      pagination.total = total.value
    } else {
      message.error(result.message || '删除失败')
    }
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

// ===== 对话列表 =====

const fetchConversations = async () => {
  const sessionId = getSessionId()
  if (!sessionId) {
    conversations.value = []
    totalConvs.value = 0
    return
  }

  loadingConvs.value = true
  convError.value = null

  try {
    const result = await listConversations(sessionId, convPage.value, pageSize.value)
    conversations.value = result.data || []
    totalConvs.value = result.total || 0
  } catch (e: any) {
    convError.value = e.message || '加载对话列表失败'
    console.error('加载对话列表失败:', e)
  } finally {
    loadingConvs.value = false
  }
}

const onConvPageChange = (page: number) => {
  convPage.value = page
  fetchConversations()
}

const loadConversation = async (conv: ConversationSummary) => {
  // 加载对话的完整版本链
  try {
    const result = await getConversation(conv.conversation_id)
    if (result.success && result.versions && result.versions.length > 0) {
      // 找到最新的有 plan_data 的版本
      const latestWithData = [...result.versions]
        .reverse()
        .find((v: any) => v.plan_data)

      if (latestWithData && latestWithData.plan_data) {
        sessionStorage.setItem('tripPlan', JSON.stringify(latestWithData.plan_data))
        sessionStorage.setItem('tripPlanMeta', JSON.stringify({
          plan_id: latestWithData.id,
          conversation_id: conv.conversation_id,
          version_number: latestWithData.version_number,
        }))
        message.success('加载对话成功')
        router.push('/result')
      } else {
        message.warning('该对话没有完整的计划数据')
      }
    } else {
      message.error('加载对话失败')
    }
  } catch (e: any) {
    message.error(e.message || '加载对话失败')
  }
}

const loadLatestPlan = async (conv: ConversationSummary) => {
  // 加载对话的最新计划版本
  try {
    const result = await getConversation(conv.conversation_id)
    if (result.success && result.versions) {
      const latest = result.versions.find((v: any) => v.is_current) || result.versions[result.versions.length - 1]
      if (latest && latest.plan_data) {
        sessionStorage.setItem('tripPlan', JSON.stringify(latest.plan_data))
        sessionStorage.setItem('tripPlanMeta', JSON.stringify({
          plan_id: latest.id,
          conversation_id: conv.conversation_id,
          version_number: latest.version_number,
        }))
        message.success('加载最新计划成功')
        router.push('/result')
      } else {
        message.warning('没有完整的计划数据')
      }
    }
  } catch (e: any) {
    message.error(e.message || '加载失败')
  }
}

const goHome = () => {
  router.push('/')
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.history-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
}

.history-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-text {
  color: #999;
  margin-bottom: 16px;
}

.loading-state {
  padding: 60px 0;
  text-align: center;
}

.loading-text {
  margin-top: 16px;
  color: #999;
}

.error-state {
  padding: 20px 0;
}

/* 对话卡片列表 */
.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conversation-card {
  border-radius: 8px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.conversation-card:hover {
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.2);
  transform: translateY(-2px);
}

.conv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.conv-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.conv-city {
  font-size: 12px;
  padding: 2px 8px;
  background: #667eea;
  color: white;
  border-radius: 10px;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
}

.conv-versions {
  color: #667eea;
  font-weight: 500;
}

.conv-pagination {
  text-align: center;
  margin-top: 20px;
}
</style>
