// 类型定义

export interface Location {
  longitude: number
  latitude: number
}

export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  rating?: number
  image_url?: string
  ticket_price?: number
}

export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  name: string
  address?: string
  location?: Location
  description?: string
  estimated_cost?: number
}

export interface Hotel {
  name: string
  address: string
  location?: Location
  price_range: string
  rating: string
  distance: string
  type: string
  estimated_cost?: number
}

export interface Budget {
  total_attractions: number
  total_hotels: number
  total_meals: number
  total_transportation: number
  total: number
}

export interface DayPlan {
  date: string
  day_index: number
  description: string
  transportation: string
  accommodation: string
  hotel?: Hotel
  attractions: Attraction[]
  meals: Meal[]
}

export interface WeatherInfo {
  date: string
  day_weather: string
  night_weather: string
  day_temp: number
  night_temp: number
  wind_direction: string
  wind_power: string
}

export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}

export interface TripFormData {
  city: string
  start_date: string
  end_date: string
  travel_days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input: string
}

export interface TripPlanResponse {
  success: boolean
  message: string
  data?: TripPlan
}

// ============ SSE流式响应类型 ============

export interface SSEProgressData {
  stage: string
  progress: number
  message: string
}

export interface SSEPartialResult {
  type: 'attractions' | 'weather' | 'hotels'
  content: string
}

export interface SSEErrorData {
  error: string
  code: string
}

export interface SSEFinalResult {
  success: boolean
  message: string
  data?: TripPlan
}

export interface StreamCallbacks {
  onProgress?: (data: SSEProgressData) => void
  onPartialResult?: (data: SSEPartialResult) => void
  onFinalResult?: (data: SSEFinalResult) => void
  onError?: (data: SSEErrorData) => void
}

// ============ 历史记录类型 ============

export interface TripRecordSummary {
  id: string
  title: string
  city: string
  created_at: string | null
  updated_at: string | null
}

export interface TripRecordDetail extends TripRecordSummary {
  request_data: TripFormData
  plan_data: TripPlan | null
}

export interface SaveTripRequest {
  session_id: string
  title: string
  request_data: string
  plan_data?: string
}

export interface TripRecordListResponse {
  success: boolean
  data: TripRecordSummary[]
  total: number
  page: number
  page_size: number
}

// ============ 对话记忆/版本管理类型 ============

export interface PlanVersion {
  id: string
  version_number: number
  is_current: boolean
  modification_request: string | null
  created_at: string
  plan_data?: TripPlan | null
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  plan_id?: string
  version_number?: number
}

export interface ConversationSummary {
  conversation_id: string
  title: string
  latest_version: number
  total_versions: number
  city: string
  created_at: string
  updated_at: string
  latest_plan_id: string
}

export interface TripPlanMeta {
  plan_id: string
  conversation_id: string
  version_number: number
}

export interface ModificationRequest {
  plan_id: string
  modification_text: string
  session_id: string
}

