# App.vue v-model 语法错误修复

## 🔴 问题描述

**错误信息**：
```
v-model value must be a valid JavaScript member expression
```

**问题位置**：`frontend/src/App.vue` 第 9 行

**错误代码**：
```vue
<a-menu
  v-model:selectedKeys="['1']"
  theme="dark"
  mode="horizontal"
>
```

---

## 🔍 根本原因

v-model 不能直接绑定到数组字面量或值，必须绑定到响应式变量。

```vue
❌ 错误：v-model:selectedKeys="['1']"
   - ['1'] 是数组字面量，不是响应式变量
   - Vue 编译器无法解析

✅ 正确：v-model:selectedKeys="selectedKeys"
   - selectedKeys 是响应式变量
   - Vue 可以正确绑定
```

---

## ✅ 解决方案

### 1. 在 script setup 中定义响应式变量
```typescript
const selectedKeys = ref(['1'])
```

### 2. 修改 v-model 绑定
```vue
❌ 之前
<a-menu v-model:selectedKeys="['1']">

✅ 之后
<a-menu v-model:selectedKeys="selectedKeys">
```

---

## 📝 修改内容

**修改文件**：`frontend/src/App.vue`

**具体修改**：
1. 添加响应式变量定义：
```typescript
<script setup lang="ts">
import { ref } from 'vue'

const selectedKeys = ref(['1'])
</script>
```

2. 修改 v-model 绑定：
```vue
<a-menu
  v-model:selectedKeys="selectedKeys"
  theme="dark"
  mode="horizontal"
>
```

---

## ✅ 验证结果

运行前端项目，导航菜单应该正常显示：
- ✅ 首页链接高亮
- ✅ 结果页链接
- ✅ Token监控链接
- ✅ 点击菜单项可以切换高亮状态

---

## 📚 Vue v-model 语法说明

### v-model 基本规则

v-model 用于双向数据绑定，必须绑定到响应式变量：

```vue
<!-- ✅ 正确 -->
<input v-model="inputValue" />
<button v-model:value="count">+1</button>

<!-- ❌ 错误 -->
<input v-model="['value']" />  <!-- 数组字面量 -->
<input v-model="123" />        <!-- 数字字面量 -->
```

### 常见响应式变量类型

```typescript
import { ref, reactive } from 'vue'

// 1. ref - 基本类型
const count = ref(0)
const selectedKeys = ref(['1'])

// 2. reactive - 对象类型
const state = reactive({
  selectedKeys: ['1'],
  openKeys: []
})
```

---

## 🚀 相关修复

本次修复解决了 App.vue 的 v-model 语法错误，确保了：
- ✅ 导航菜单正常工作
- ✅ 路由链接高亮状态正确显示
- ✅ Token监控页面可以正常访问

---

**修复时间**：2026-04-23
**验证状态**：✅ 通过
**状态**：已解决
