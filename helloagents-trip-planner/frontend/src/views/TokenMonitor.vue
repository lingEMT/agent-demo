<template>
  <div class="token-monitor">
    <a-card title="Token使用监控" :bordered="false">
      <template #extra>
        <a-space>
          <a-tag color="blue">24小时</a-tag>
          <a-tag color="green">7天</a-tag>
          <a-tag color="orange">30天</a-tag>
        </a-space>
      </template>

      <!-- 统计卡片 -->
      <a-row :gutter="16" class="stats-cards">
        <a-col :span="6">
          <a-statistic
            title="总请求数"
            :value="stats.total_requests || 0"
            suffix="次"
          >
            <template #prefix>
              <FileTextOutlined />
            </template>
          </a-statistic>
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="Token总数"
            :value="stats.total_tokens || 0"
            suffix=" tokens"
          >
            <template #prefix>
              <CodeOutlined />
            </template>
          </a-statistic>
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="成本"
            :value="stats.total_cost || 0"
            :precision="4"
            suffix="元"
            :value-style="{ color: '#3f8600' }"
          >
            <template #prefix>
              <MoneyCollectOutlined />
            </template>
          </a-statistic>
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="输入Token"
            :value="stats.input_tokens || 0"
            suffix=" tokens"
          >
            <template #prefix>
              <InboxOutlined />
            </template>
          </a-statistic>
        </a-col>
      </a-row>

      <!-- 每日统计 -->
      <a-card title="每日Token使用趋势" :bordered="false" style="margin-top: 24px">
        <div ref="dailyChartRef" style="height: 350px;"></div>
      </a-card>

      <!-- 模型统计 -->
      <a-card title="模型使用统计" :bordered="false" style="margin-top: 24px">
        <a-table
          :columns="modelColumns"
          :data-source="modelStats"
          :pagination="false"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'total_tokens'">
              <a-statistic :value="record.total_tokens" :precision="0" />
            </template>
            <template v-else-if="column.key === 'total_cost'">
              <a-statistic :value="record.total_cost" :precision="4" />
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 错误统计 -->
      <a-card title="错误统计" :bordered="false" style="margin-top: 24px">
        <a-statistic
          title="总错误数"
          :value="errorStats.total_errors || 0"
          :value-style="{ color: '#cf1322' }"
        >
          <template #prefix>
            <AlertOutlined />
          </template>
        </a-statistic>

        <div v-if="errorStats.errors.length > 0" style="margin-top: 16px">
          <a-list
            size="small"
            :data-source="errorStats.errors"
            :pagination="{ pageSize: 5 }"
          >
            <template #renderItem="{ item }">
              <a-list-item>
                <a-space>
                  <a-tag color="red">{{ item.error }}</a-tag>
                  <a-tag>{{ item.count }} 次</a-tag>
                </a-space>
              </a-list-item>
            </template>
          </a-list>
        </div>
      </a-card>

      <!-- Token使用排行 -->
      <a-card title="Token使用量排行" :bordered="false" style="margin-top: 24px">
        <div v-if="loading" class="loading">
          <a-spin />
        </div>
        <div v-else class="ranking-list">
          <a-list
            size="small"
            :data-source="topTokens"
          >
            <template #renderItem="{ item }">
              <a-list-item>
                <a-space style="width: 100%">
                  <a-avatar size="small" style="background-color: #1890ff">
                    {{ item.rank }}
                  </a-avatar>
                  <div style="flex: 1">
                    <div class="token-name">{{ item.token_key }}</div>
                    <a-progress
                      :percent="getPercent(item.total_tokens)"
                      :show-info="false"
                      size="small"
                    />
                  </div>
                  <a-statistic
                    :value="item.total_tokens"
                    :precision="0"
                    :value-style="{ fontSize: '14px' }"
                  />
                </a-space>
              </a-list-item>
            </template>
          </a-list>
        </div>
      </a-card>

      <!-- API端点说明 -->
      <a-card title="API端点" :bordered="false" style="margin-top: 24px">
        <a-list size="small">
          <a-list-item>
            <a-list-item-meta title="GET /api/token-monitor/summary" />
            <template #description>
              获取token使用摘要
            </template>
          </a-list-item>
          <a-list-item>
            <a-list-item-meta title="GET /api/token-monitor/stats" />
            <template #description>
              获取token使用统计
            </template>
          </a-list-item>
          <a-list-item>
            <a-list-item-meta title="GET /api/token-monitor/daily" />
            <template #description>
              获取每日token使用统计
            </template>
          </a-list-item>
          <a-list-item>
            <a-list-item-meta title="GET /api/token-monitor/models" />
            <template #description>
              获取各模型使用统计
            </template>
          </a-list-item>
          <a-list-item>
            <a-list-item-meta title="GET /api/token-monitor/errors" />
            <template #description>
              获取错误统计
            </template>
          </a-list-item>
        </a-list>
      </a-card>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { message } from 'ant-design-vue'
import {
  FileTextOutlined,
  CodeOutlined,
  MoneyCollectOutlined,
  InboxOutlined,
  AlertOutlined
} from '@ant-design/icons-vue'
import * as echarts from 'echarts'

interface TokenStats {
  total_requests: number
  total_tokens: number
  total_cost: number
  input_tokens: number
  output_tokens: number
}

interface ModelStats {
  model: string
  total_requests: number
  total_tokens: number
  input_tokens: number
  output_tokens: number
  total_cost: number
}

interface DailyStats {
  date: string
  total_requests: number
  total_tokens: number
  input_tokens: number
  output_tokens: number
  total_cost: number
}

interface TopToken {
  token_key: string
  total_tokens: number
  rank: number
}

const stats = ref<TokenStats>({
  total_requests: 0,
  total_tokens: 0,
  total_cost: 0,
  input_tokens: 0,
  output_tokens: 0
})

const modelStats = ref<ModelStats[]>([])
const errorStats = ref<{ total_errors: number; errors: any[] }>({
  total_errors: 0,
  errors: []
})

const topTokens = ref<TopToken[]>([])
const dailyChartRef = ref<HTMLDivElement>()
let dailyChart: echarts.ECharts | null = null

const modelColumns = [
  {
    title: '模型',
    dataIndex: 'model',
    key: 'model',
    width: 200
  },
  {
    title: '请求数',
    dataIndex: 'total_requests',
    key: 'total_requests',
    width: 120,
    align: 'right'
  },
  {
    title: 'Token总数',
    key: 'total_tokens',
    width: 150,
    align: 'right'
  },
  {
    title: '输入Token',
    dataIndex: 'input_tokens',
    key: 'input_tokens',
    width: 120,
    align: 'right'
  },
  {
    title: '输出Token',
    dataIndex: 'output_tokens',
    key: 'output_tokens',
    width: 120,
    align: 'right'
  },
  {
    title: '成本',
    key: 'total_cost',
    width: 150,
    align: 'right'
  }
]

const getPercent = (value: number) => {
  const max = Math.max(...topTokens.value.map(t => t.total_tokens))
  return max > 0 ? Math.round((value / max) * 100) : 0
}

const fetchStats = async () => {
  try {
    const [summaryRes, modelsRes, errorsRes, topTokensRes] = await Promise.all([
      fetch('/api/token-monitor/summary'),
      fetch('/api/token-monitor/models'),
      fetch('/api/token-monitor/errors'),
      fetch('/api/token-monitor/top-tokens?hours=24&limit=10')
    ])

    const summaryData = await summaryRes.json()
    const modelsData = await modelsRes.json()
    const errorsData = await errorsRes.json()
    const topTokensData = await topTokensRes.json()

    if (summaryData.success) {
      stats.value = summaryData.data.last_24h
    }

    if (modelsData.success) {
      modelStats.value = modelsData.data
    }

    if (errorsData.success) {
      errorStats.value = errorsData.data
    }

    if (topTokensData.success) {
      topTokens.value = topTokensData.data.top_tokens.map((item: any, index: number) => ({
        ...item,
        rank: index + 1
      }))
    }
  } catch (error) {
    message.error('获取统计数据失败')
    console.error('Fetch stats error:', error)
  }
}

const fetchDailyStats = async () => {
  try {
    const res = await fetch('/api/token-monitor/daily?days=7')
    const data = await res.json()

    if (data.success) {
      initDailyChart(data.data.stats)
    }
  } catch (error) {
    console.error('Fetch daily stats error:', error)
  }
}

const initDailyChart = (dailyStats: DailyStats[]) => {
  if (!dailyChartRef.value) return

  dailyChart = echarts.init(dailyChartRef.value)

  const dates = dailyStats.map(d => d.date)
  const tokenCounts = dailyStats.map(d => d.total_tokens)
  const inputTokens = dailyStats.map(d => d.input_tokens)
  const outputTokens = dailyStats.map(d => d.output_tokens)

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['总Token', '输入Token', '输出Token']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates
    },
    yAxis: {
      type: 'value',
      name: 'Token数量'
    },
    series: [
      {
        name: '总Token',
        type: 'line',
        smooth: true,
        data: tokenCounts,
        itemStyle: {
          color: '#1890ff'
        }
      },
      {
        name: '输入Token',
        type: 'line',
        smooth: true,
        data: inputTokens,
        itemStyle: {
          color: '#52c41a'
        }
      },
      {
        name: '输出Token',
        type: 'line',
        smooth: true,
        data: outputTokens,
        itemStyle: {
          color: '#faad14'
        }
      }
    ]
  }

  dailyChart.setOption(option)
}

const resizeChart = () => {
  dailyChart?.resize()
}

onMounted(() => {
  fetchStats()
  fetchDailyStats()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  dailyChart?.dispose()
})
</script>

<style scoped>
.token-monitor {
  padding: 24px;
}

.stats-cards {
  margin-bottom: 24px;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 24px;
}

.ranking-list .token-name {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.ranking-list :deep(.ant-progress) {
  margin: 4px 0;
}
</style>
