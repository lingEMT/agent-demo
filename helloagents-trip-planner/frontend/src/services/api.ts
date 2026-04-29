import axios from 'axios'
import type { TripFormData, TripPlanResponse, StreamCallbacks } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2分钟超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

/**
 * 生成旅行计划
 */
export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '生成旅行计划失败')
  }
}

/**
 * 流式生成旅行计划 (SSE)
 * 使用 fetch + ReadableStream 解析 SSE 事件流
 */
export async function generateTripPlanStream(
  formData: TripFormData,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/trip/plan/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData),
    signal
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('响应体不可读')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // 解析SSE格式：event: xxx\ndata: {...}\n\n
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // 保留最后一个不完整的行

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const rawData = line.slice(6)
          try {
            const data = JSON.parse(rawData)
            switch (currentEvent) {
              case 'progress':
                callbacks.onProgress?.(data)
                break
              case 'partial_result':
                callbacks.onPartialResult?.(data)
                break
              case 'final_result':
                callbacks.onFinalResult?.(data)
                break
              case 'error':
                callbacks.onError?.(data)
                break
            }
          } catch (parseError) {
            console.warn('SSE数据解析失败:', rawData)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

export default apiClient

// ============ 历史记录 API ============

/**
 * 保存旅行计划到历史记录
 */
export async function saveTripRecord(params: {
  session_id: string
  title: string
  request_data: string
  plan_data?: string
}): Promise<any> {
  try {
    const queryParams = new URLSearchParams({
      session_id: params.session_id,
      title: params.title,
      request_data: params.request_data,
    })
    if (params.plan_data) {
      queryParams.append('plan_data', params.plan_data)
    }
    const response = await apiClient.post(`/api/history/save?${queryParams.toString()}`)
    return response.data
  } catch (error: any) {
    console.error('保存历史记录失败:', error)
    // fire-and-forget，不抛出异常
    return null
  }
}

/**
 * 获取历史记录列表
 */
export async function listTripRecords(
  session_id: string,
  page: number = 1,
  page_size: number = 20
): Promise<any> {
  try {
    const response = await apiClient.get('/api/history/list', {
      params: { session_id, page, page_size }
    })
    return response.data
  } catch (error: any) {
    console.error('获取历史记录列表失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '获取历史记录列表失败')
  }
}

/**
 * 获取单个旅行计划详情
 */
export async function getTripRecord(recordId: string): Promise<any> {
  try {
    const response = await apiClient.get(`/api/history/${recordId}`)
    return response.data
  } catch (error: any) {
    console.error('获取历史记录详情失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '获取历史记录详情失败')
  }
}

/**
 * 删除旅行计划记录
 */
export async function deleteTripRecord(recordId: string): Promise<any> {
  try {
    const response = await apiClient.delete(`/api/history/${recordId}`)
    return response.data
  } catch (error: any) {
    console.error('删除历史记录失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '删除历史记录失败')
  }
}

