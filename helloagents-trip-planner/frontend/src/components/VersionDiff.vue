<template>
  <div class="version-diff">
    <!-- 版本选择器 -->
    <div class="diff-selectors">
      <a-space>
        <span class="selector-label">版本 A：</span>
        <a-select
          v-model:value="versionAIndex"
          style="width: 200px"
          :options="versionOptions"
          @change="onSelectorChange"
        />
        <span class="arrow-icon">→</span>
        <span class="selector-label">版本 B：</span>
        <a-select
          v-model:value="versionBIndex"
          style="width: 200px"
          :options="versionOptions"
          @change="onSelectorChange"
        />
      </a-space>
    </div>

    <!-- 相同版本提示 -->
    <div v-if="isSameVersion" class="same-version-hint">
      <a-alert type="info" message="已选中同一版本，无差异可比较" show-icon banner />
    </div>

    <!-- 数据为空提示 -->
    <div v-else-if="!planA || !planB" class="empty-hint">
      <a-empty description="选中的版本缺少计划数据" />
    </div>

    <!-- Diff 内容 -->
    <template v-else>
      <!-- 概览对比 -->
      <a-card title="概览对比" size="small" class="diff-section">
        <div class="overview-grid">
          <div class="overview-row">
            <span class="overview-label">天数</span>
            <span class="overview-values">
              <span class="value-old">{{ planA.days.length }}</span>
              <span class="arrow">→</span>
              <span class="value-new">{{ planB.days.length }}</span>
              <span
                v-if="planA.days.length !== planB.days.length"
                class="diff-badge"
                :class="planB.days.length > planA.days.length ? 'badge-added' : 'badge-removed'"
              >
                {{ planB.days.length > planA.days.length ? '+' : '' }}{{ planB.days.length - planA.days.length }}
              </span>
            </span>
          </div>
          <div class="overview-row">
            <span class="overview-label">日期</span>
            <span class="overview-values">
              <span class="value-old">{{ planA.start_date }} ~ {{ planA.end_date }}</span>
              <span class="arrow">→</span>
              <span class="value-new">{{ planB.start_date }} ~ {{ planB.end_date }}</span>
              <span
                v-if="planA.start_date !== planB.start_date || planA.end_date !== planB.end_date"
                class="diff-badge badge-modified"
              >已修改</span>
            </span>
          </div>
          <div class="overview-row">
            <span class="overview-label">城市</span>
            <span class="overview-values">
              <span class="value-old">{{ planA.city }}</span>
              <span class="arrow">→</span>
              <span class="value-new">{{ planB.city }}</span>
              <span
                v-if="planA.city !== planB.city"
                class="diff-badge badge-modified"
              >已修改</span>
            </span>
          </div>
        </div>

        <!-- 预算对比 -->
        <div v-if="planA.budget || planB.budget" class="budget-section">
          <a-divider style="margin: 12px 0" />
          <div class="budget-title">预算对比</div>
          <a-table
            :dataSource="budgetRows"
            :columns="budgetColumns"
            :pagination="false"
            size="small"
            bordered
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'category'">
                {{ record.category }}
              </template>
              <template v-else-if="column.key === 'oldValue'">
                <span :class="{ 'value-empty': record.oldValue === '-' }">
                  {{ record.oldValue === '-' ? '-' : `¥${record.oldValue}` }}
                </span>
              </template>
              <template v-else-if="column.key === 'newValue'">
                <span :class="{ 'value-empty': record.newValue === '-' }">
                  {{ record.newValue === '-' ? '-' : `¥${record.newValue}` }}
                </span>
              </template>
              <template v-else-if="column.key === 'delta'">
                <span
                  v-if="record.delta !== 0"
                  class="diff-amount"
                  :class="record.delta > 0 ? 'amount-up' : 'amount-down'"
                >
                  {{ record.delta > 0 ? '+' : '' }}¥{{ record.delta }}
                </span>
                <span v-else class="diff-amount amount-same">持平</span>
              </template>
            </template>
          </a-table>
        </div>
      </a-card>

      <!-- 每日行程对比 -->
      <a-card title="每日行程对比" size="small" class="diff-section">
        <a-collapse v-model:activeKey="activeDayKeys" expand-icon-position="right">
          <a-collapse-panel
            v-for="dayDiff in dayDiffs"
            :key="String(dayDiff.dayIndex)"
            :header="dayHeader(dayDiff)"
          >
            <!-- 景点对比 -->
            <div v-if="dayDiff.attractions.length > 0" class="day-category">
              <div class="category-label">🎯 景点</div>
              <div
                v-for="(item, idx) in dayDiff.attractions"
                :key="idx"
                class="diff-item"
                :class="`diff-${item.status}`"
              >
                <span class="status-tag" :class="`tag-${item.status}`">
                  {{ statusLabel(item.status) }}
                </span>
                <span :class="{ 'removed-text': item.status === 'removed' }">
                  {{ item.name }}
                </span>
                <span v-if="item.status === 'unchanged'" class="no-change-mark">✅</span>
              </div>
              <div v-if="dayDiff.attractions.length === 0 && !dayDiff.isNew" class="no-items">
                无景点
              </div>
            </div>

            <!-- 餐饮对比 -->
            <div class="day-category">
              <div class="category-label">🍽️ 餐饮</div>
              <div
                v-for="(item, idx) in dayDiff.meals"
                :key="idx"
                class="diff-item"
                :class="`diff-${item.status}`"
              >
                <span class="status-tag" :class="`tag-${item.status}`">
                  {{ statusLabel(item.status) }}
                </span>
                <span :class="{ 'removed-text': item.status === 'removed' }">
                  {{ mealTypeLabel(item.type) }}：{{ item.name }}
                </span>
                <span v-if="item.status === 'unchanged'" class="no-change-mark">✅</span>
              </div>
              <div v-if="dayDiff.meals.length === 0 && !dayDiff.isNew" class="no-items">
                无餐饮安排
              </div>
            </div>

            <!-- 住宿对比 -->
            <div class="day-category">
              <div class="category-label">🏨 住宿</div>
              <div v-if="dayDiff.hotel" class="diff-item" :class="`diff-${dayDiff.hotel.status}`">
                <span class="status-tag" :class="`tag-${dayDiff.hotel.status}`">
                  {{ statusLabel(dayDiff.hotel.status) }}
                </span>
                <span :class="{ 'removed-text': dayDiff.hotel.status === 'removed' }">
                  {{ dayDiff.hotel.name }}
                </span>
                <span v-if="dayDiff.hotel.status === 'unchanged'" class="no-change-mark">✅</span>
              </div>
              <div v-else class="no-items">无住宿安排</div>
            </div>

            <!-- 交通对比 -->
            <div class="day-category">
              <div class="category-label">🚗 交通</div>
              <div v-if="dayDiff.transportation" class="diff-item" :class="`diff-${dayDiff.transportation.status}`">
                <span class="status-tag" :class="`tag-${dayDiff.transportation.status}`">
                  {{ statusLabel(dayDiff.transportation.status) }}
                </span>
                <span :class="{ 'removed-text': dayDiff.transportation.status === 'removed' }">
                  {{ dayDiff.transportation.value }}
                </span>
                <span v-if="dayDiff.transportation.status === 'unchanged'" class="no-change-mark">✅</span>
              </div>
              <div v-else class="no-items">无交通安排</div>
            </div>
          </a-collapse-panel>
        </a-collapse>
      </a-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { PlanVersion, DayPlan, Attraction, Meal } from '@/types'

const props = defineProps<{
  versions: PlanVersion[]
}>()

// ====== 版本选择器 ======
const versionAIndex = ref(Math.max(0, props.versions.length - 2))
const versionBIndex = ref(props.versions.length - 1)
const activeDayKeys = ref<string[]>([])

const versionOptions = computed(() =>
  props.versions.map((v, i) => ({
    value: i,
    label: `v${v.version_number}${v.plan_data ? '' : ' (无数据)'}`,
    disabled: !v.plan_data,
  }))
)

const versionA = computed(() => props.versions[versionAIndex.value])
const versionB = computed(() => props.versions[versionBIndex.value])
const planA = computed(() => versionA.value?.plan_data ?? null)
const planB = computed(() => versionB.value?.plan_data ?? null)
const isSameVersion = computed(() => versionAIndex.value === versionBIndex.value)

const onSelectorChange = () => {
  activeDayKeys.value = []
}

// ====== 概览对比 ======

const budgetColumns = [
  { title: '项目', dataIndex: 'category', key: 'category', width: 100 },
  { title: 'v${versionA.value?.version_number}', dataIndex: 'oldValue', key: 'oldValue', width: 100 },
  { title: 'v${versionB.value?.version_number}', dataIndex: 'newValue', key: 'newValue', width: 100 },
  { title: '差额', dataIndex: 'delta', key: 'delta', width: 100 },
]

const budgetRows = computed(() => {
  const a = planA.value?.budget
  const b = planB.value?.budget
  const items = [
    { key: 'attractions', category: '景点门票', oldValue: a?.total_attractions ?? '-', newValue: b?.total_attractions ?? '-', delta: getDelta(a?.total_attractions, b?.total_attractions) },
    { key: 'hotels', category: '酒店住宿', oldValue: a?.total_hotels ?? '-', newValue: b?.total_hotels ?? '-', delta: getDelta(a?.total_hotels, b?.total_hotels) },
    { key: 'meals', category: '餐饮', oldValue: a?.total_meals ?? '-', newValue: b?.total_meals ?? '-', delta: getDelta(a?.total_meals, b?.total_meals) },
    { key: 'transportation', category: '交通', oldValue: a?.total_transportation ?? '-', newValue: b?.total_transportation ?? '-', delta: getDelta(a?.total_transportation, b?.total_transportation) },
    { key: 'total', category: '总计', oldValue: a?.total ?? '-', newValue: b?.total ?? '-', delta: getDelta(a?.total, b?.total) },
  ]
  return items
})

function getDelta(oldVal: number | undefined, newVal: number | undefined): number {
  if (oldVal === undefined && newVal === undefined) return 0
  if (oldVal === undefined) return newVal!
  if (newVal === undefined) return -oldVal
  return newVal - oldVal
}

// ====== 每日行程对比 ======

interface DiffItem {
  name: string
  status: 'added' | 'removed' | 'modified' | 'unchanged'
  type?: string
  value?: string
}

interface DayDiff {
  dayIndex: number
  date: string
  status: 'added' | 'removed' | 'modified' | 'unchanged'
  isNew: boolean
  attractions: DiffItem[]
  meals: DiffItem[]
  hotel: DiffItem | null
  transportation: DiffItem | null
}

function compareAttractions(oldList: Attraction[], newList: Attraction[]): DiffItem[] {
  const result: DiffItem[] = []
  const oldNames = new Set(oldList.map((a) => a.name))
  const newNames = new Set(newList.map((a) => a.name))

  for (const attr of oldList) {
    if (newNames.has(attr.name)) {
      result.push({ name: attr.name, status: 'unchanged' })
    } else {
      result.push({ name: attr.name, status: 'removed' })
    }
  }
  for (const attr of newList) {
    if (!oldNames.has(attr.name)) {
      result.push({ name: attr.name, status: 'added' })
    }
  }
  return result
}

function compareMeals(oldList: Meal[], newList: Meal[]): DiffItem[] {
  const result: DiffItem[] = []
  const oldKeys = new Set(oldList.map((m) => `${m.type}:${m.name}`))
  const newKeys = new Set(newList.map((m) => `${m.type}:${m.name}`))

  for (const meal of oldList) {
    const key = `${meal.type}:${meal.name}`
    if (newKeys.has(key)) {
      result.push({ name: meal.name, type: meal.type, status: 'unchanged' })
    } else {
      result.push({ name: meal.name, type: meal.type, status: 'removed' })
    }
  }
  for (const meal of newList) {
    const key = `${meal.type}:${meal.name}`
    if (!oldKeys.has(key)) {
      result.push({ name: meal.name, type: meal.type, status: 'added' })
    }
  }
  return result
}

function compareHotel(oldDay: DayPlan | undefined, newDay: DayPlan | undefined): DiffItem | null {
  const oldName = oldDay?.hotel?.name || oldDay?.accommodation
  const newName = newDay?.hotel?.name || newDay?.accommodation
  if (!oldName && !newName) return null
  if (!oldName) return { name: newName || '', status: 'added' }
  if (!newName) return { name: oldName, status: 'removed' }
  if (oldName === newName) return { name: oldName, status: 'unchanged' }
  // Different hotels: show combined label with modified status
  return { name: `${oldName} → ${newName}`, status: 'modified' }
}

function compareTransportation(oldDay: DayPlan | undefined, newDay: DayPlan | undefined): DiffItem | null {
  const oldT = oldDay?.transportation
  const newT = newDay?.transportation
  if ((!oldT || oldT === '无' || oldT === '') && (!newT || newT === '无' || newT === '')) return null
  if (!oldT || oldT === '无' || oldT === '') return { name: newT || '', value: newT || '', status: 'added' }
  if (!newT || newT === '无' || newT === '') return { name: oldT, value: oldT, status: 'removed' }
  if (oldT === newT) return { name: oldT, value: oldT, status: 'unchanged' }
  // Different transportation: show combined label with modified status
  return { name: `${oldT} → ${newT}`, value: `${oldT} → ${newT}`, status: 'modified' }
}

const dayDiffs = computed<DayDiff[]>(() => {
  if (!planA.value || !planB.value) return []
  const aDays = planA.value.days
  const bDays = planB.value.days
  const allIndices = new Set<number>()
  for (const d of aDays) allIndices.add(d.day_index)
  for (const d of bDays) allIndices.add(d.day_index)
  const sorted = Array.from(allIndices).sort((a, b) => a - b)

  const daysMapA = new Map<number, DayPlan>()
  const daysMapB = new Map<number, DayPlan>()
  for (const d of aDays) daysMapA.set(d.day_index, d)
  for (const d of bDays) daysMapB.set(d.day_index, d)

  return sorted.map((idx) => {
    const oldDay = daysMapA.get(idx)
    const newDay = daysMapB.get(idx)

    if (!oldDay && newDay) {
      // New day only in B
      return {
        dayIndex: idx,
        date: newDay.date,
        status: 'added' as const,
        isNew: true,
        attractions: newDay.attractions.map((a) => ({ name: a.name, status: 'added' as const })),
        meals: newDay.meals.map((m) => ({ name: m.name, type: m.type, status: 'added' as const })),
        hotel: newDay.hotel ? { name: newDay.hotel.name, status: 'added' as const } : (newDay.accommodation ? { name: newDay.accommodation, status: 'added' as const } : null),
        transportation: newDay.transportation && newDay.transportation !== '无' ? { name: newDay.transportation, value: newDay.transportation, status: 'added' as const } : null,
      }
    }

    if (oldDay && !newDay) {
      // Day only in A
      return {
        dayIndex: idx,
        date: oldDay.date,
        status: 'removed' as const,
        isNew: false,
        attractions: oldDay.attractions.map((a) => ({ name: a.name, status: 'removed' as const })),
        meals: oldDay.meals.map((m) => ({ name: m.name, type: m.type, status: 'removed' as const })),
        hotel: oldDay.hotel ? { name: oldDay.hotel.name, status: 'removed' as const } : (oldDay.accommodation ? { name: oldDay.accommodation, status: 'removed' as const } : null),
        transportation: oldDay.transportation && oldDay.transportation !== '无' ? { name: oldDay.transportation, value: oldDay.transportation, status: 'removed' as const } : null,
      }
    }

    // Both days exist — compare
    const attrDiffs = compareAttractions(oldDay!.attractions, newDay!.attractions)
    const mealDiffs = compareMeals(oldDay!.meals, newDay!.meals)
    const hotelDiff = compareHotel(oldDay, newDay)
    const transDiff = compareTransportation(oldDay, newDay)

    const hasChanges =
      attrDiffs.some((d) => d.status !== 'unchanged') ||
      mealDiffs.some((d) => d.status !== 'unchanged') ||
      hotelDiff !== null ||
      transDiff !== null

    return {
      dayIndex: idx,
      date: oldDay!.date,
      status: hasChanges ? 'modified' as const : 'unchanged' as const,
      isNew: false,
      attractions: attrDiffs,
      meals: mealDiffs,
      hotel: hotelDiff,
      transportation: transDiff,
    }
  })
})

// ====== 辅助函数 ======

function statusLabel(status: string): string {
  switch (status) {
    case 'added': return '新增'
    case 'removed': return '移除'
    case 'unchanged': return '不变'
    case 'modified': return '修改'
    default: return ''
  }
}

function mealTypeLabel(type: string | undefined): string {
  switch (type) {
    case 'breakfast': return '早餐'
    case 'lunch': return '午餐'
    case 'dinner': return '晚餐'
    case 'snack': return '小吃'
    default: return type || '餐饮'
  }
}

function dayHeader(dayDiff: DayDiff): string {
  const base = `第${dayDiff.dayIndex + 1}天`
  switch (dayDiff.status) {
    case 'unchanged': return `${base} ✅ 无变化`
    case 'added': return `${base} 🟢 新增`
    case 'removed': return `${base} 🔴 已移除`
    case 'modified': return `${base} 🔵 已修改`
    default: return base
  }
}
</script>

<style scoped>
.version-diff {
  padding: 4px 0;
}

.diff-selectors {
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  text-align: center;
}

.selector-label {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
}

.arrow-icon {
  font-size: 18px;
  color: #999;
  margin: 0 4px;
}

.same-version-hint,
.empty-hint {
  margin: 40px 0;
  text-align: center;
}

.diff-section {
  margin-bottom: 16px;
}

/* 概览对比 */
.overview-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.overview-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.overview-label {
  width: 50px;
  font-weight: 600;
  color: #333;
  flex-shrink: 0;
}

.overview-values {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.value-old {
  color: #999;
  text-decoration: line-through;
}

.arrow {
  color: #999;
}

.value-new {
  color: #333;
  font-weight: 500;
}

.value-empty {
  color: #ccc;
}

.diff-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.badge-added {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.badge-removed {
  background: #fff2f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

.badge-modified {
  background: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}

/* 预算对比 */
.budget-section {
  margin-top: 8px;
}

.budget-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.diff-amount {
  font-weight: 600;
}

.amount-up {
  color: #ff4d4f;
}

.amount-down {
  color: #52c41a;
}

.amount-same {
  color: #999;
  font-weight: normal;
}

/* 每日行程对比 */
.day-category {
  margin-bottom: 12px;
}

.category-label {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
}

.diff-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  font-size: 13px;
}

.diff-added {
  background: #f6ffed;
  border-left: 3px solid #52c41a;
}

.diff-removed {
  background: #fff2f0;
  border-left: 3px solid #ff4d4f;
}

.diff-modified {
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.diff-unchanged {
  background: transparent;
  border-left: 3px solid transparent;
}

.status-tag {
  display: inline-block;
  padding: 0 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.tag-added {
  background: #52c41a;
  color: white;
}

.tag-removed {
  background: #ff4d4f;
  color: white;
}

.tag-unchanged {
  background: #d9d9d9;
  color: #666;
}

.tag-modified {
  background: #1890ff;
  color: white;
}

.removed-text {
  text-decoration: line-through;
  color: #999;
}

.no-change-mark {
  margin-left: auto;
  font-size: 12px;
}

.no-items {
  padding: 4px 8px;
  color: #bbb;
  font-size: 12px;
  font-style: italic;
}
</style>
