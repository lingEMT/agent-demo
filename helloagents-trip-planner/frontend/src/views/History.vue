<template>
  <div class="history-container">
    <a-card title="历史旅行记录" :bordered="false" class="history-card">
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
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { listTripRecords, getTripRecord, deleteTripRecord } from '@/services/api'
import type { TripRecordSummary } from '@/types'

const router = useRouter()

const loading = ref(false)
const error = ref<string | null>(null)
const records = ref<TripRecordSummary[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

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
      // 重新加载列表
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
</style>
