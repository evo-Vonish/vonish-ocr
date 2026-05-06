<template>
  <div class="v-responsive-table">
    <!-- 宽容器：传统表格 -->
    <table v-if="_wide">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, ri) in rows" :key="ri" :class="{ highlight: row._highlight }">
          <td v-for="col in columns" :key="col.key">
            <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 中容器：横向滚动表 -->
    <div v-else-if="_medium" class="table-scroll">
      <table>
        <thead>
          <tr>
            <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in rows" :key="ri">
            <td v-for="col in columns" :key="col.key">
              <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
                {{ row[col.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 窄容器：卡片列表 -->
    <div v-else class="table-card-list">
      <div
        v-for="(row, ri) in rows"
        :key="ri"
        class="table-card"
        :class="{ highlight: row._highlight }"
      >
        <div v-for="col in columns" :key="col.key" class="table-card-row">
          <span class="tcr-label">{{ col.label }}</span>
          <span class="tcr-value">
            <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
})

const _wide = ref(true)
const _medium = ref(false)
let resizeObserver = null
let containerEl = null

onMounted(() => {
  containerEl = document.querySelector('.v-responsive-table')
  if (!containerEl) return
  _evaluate()
  resizeObserver = new ResizeObserver(_evaluate)
  resizeObserver.observe(containerEl)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

function _evaluate() {
  const w = containerEl?.clientWidth || 800
  _wide.value = w >= 500
  _medium.value = w >= 350 && w < 500
}
</script>

<style scoped>
.v-responsive-table {
  container-type: inline-size;
  width: 100%;
}

/* 传统表格 */
table {
  width: 100%;
  border-collapse: collapse;
}

th {
  background-color: var(--v-rail);
  color: var(--v-text);
  font-family: var(--font-mono);
  font-size: var(--font-caption);
  font-weight: 600;
  border-bottom: 2px solid var(--v-border);
  padding: var(--space-sm) var(--space-md);
  text-align: left;
  white-space: nowrap;
}

td {
  border-bottom: 1px solid var(--v-border);
  padding: var(--space-sm) var(--space-md);
  color: var(--v-text-muted);
  font-size: var(--font-small);
}

tr:hover td {
  background-color: var(--v-rail);
}

tr.highlight td {
  border-left: 2px solid var(--v-accent);
  background-color: var(--v-accent-dim);
}

/* 横向滚动 */
.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.table-scroll table {
  min-width: 500px;
}

/* 卡片列表 */
.table-card-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.table-card {
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--radius-sm);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.table-card.highlight {
  border-color: var(--v-accent);
  background-color: var(--v-accent-dim);
}

.table-card-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-sm);
}

.tcr-label {
  font-family: var(--font-mono);
  font-size: var(--font-micro);
  color: var(--v-text-faint);
  letter-spacing: 0.06em;
  flex-shrink: 0;
  min-width: 72px;
}

.tcr-value {
  font-size: var(--font-small);
  color: var(--v-text);
  text-align: right;
  word-break: break-word;
}
</style>
