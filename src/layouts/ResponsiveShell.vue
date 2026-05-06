<template>
  <div class="rs-shell" :data-morph="morphState">
    <header class="rs-topbar">
      <slot name="topbar" />
    </header>

    <slot v-if="morphState === 'phone-portrait'" name="top-toolbar" />

    <div class="rs-body">
      <aside v-if="showLeftRail" class="rs-left-rail" :class="{ compact: morphState === 'tablet-landscape' }">
        <slot name="left-rail" />
      </aside>

      <main class="rs-workbench">
        <slot name="workbench" />
      </main>

      <aside v-if="showRightReview" class="rs-right-review" :class="{ compact: morphState === 'tablet-landscape' }">
        <slot name="right-review" />
      </aside>
    </div>

    <BottomSheet :visible="reviewSheetOpen" height="50vh" @close="reviewSheetOpen = false">
      <slot name="right-review" />
    </BottomSheet>

    <EdgeDrawer :visible="leftDrawerOpen" side="left" width="40%" @close="leftDrawerOpen = false" @open="leftDrawerOpen = true">
      <slot name="left-rail" />
    </EdgeDrawer>
    <EdgeDrawer :visible="rightDrawerOpen" side="right" width="40%" @close="rightDrawerOpen = false" @open="rightDrawerOpen = true">
      <slot name="right-review" />
    </EdgeDrawer>

    <footer v-if="showBottomBar" class="rs-bottombar">
      <slot name="bottombar" />
    </footer>

    <button v-if="reviewFloating" class="rs-float-review" type="button" aria-label="复核灯" @click="reviewSheetOpen = true">
      <span class="float-dot"></span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import BottomSheet from '../components/BottomSheet.vue'
import EdgeDrawer from '../components/EdgeDrawer.vue'

const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)
const windowHeight = ref(typeof window !== 'undefined' ? window.innerHeight : 800)
const reviewSheetOpen = ref(false)
const leftDrawerOpen = ref(false)
const rightDrawerOpen = ref(false)

let resizeTimer = null

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  if (resizeTimer) clearTimeout(resizeTimer)
})

function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    windowWidth.value = window.innerWidth
    windowHeight.value = window.innerHeight
  }, 150)
}

const isLandscape = computed(() => windowWidth.value > windowHeight.value)
const isPortrait = computed(() => !isLandscape.value)
const w = () => windowWidth.value

const morphState = computed(() => {
  if (w() > 1440) return 'ultra-wide'
  if (w() >= 1024) return 'desktop'
  if (w() >= 768) return isLandscape.value ? 'tablet-landscape' : 'tablet-portrait'
  if (w() >= 480) return isLandscape.value ? 'phone-landscape' : 'phone-portrait'
  return 'phone-portrait'
})

const showLeftRail = computed(() =>
  ['ultra-wide', 'desktop', 'tablet-landscape', 'tablet-portrait'].includes(morphState.value)
)

const showRightReview = computed(() =>
  ['ultra-wide', 'desktop'].includes(morphState.value)
)

const showBottomBar = computed(() =>
  ['ultra-wide', 'desktop', 'tablet-landscape', 'tablet-portrait'].includes(morphState.value)
)

const reviewFloating = computed(() =>
  ['tablet-landscape', 'tablet-portrait', 'phone-landscape', 'phone-portrait'].includes(morphState.value)
)
</script>

<style scoped>
.rs-shell {
  height: 100vh;
  display: grid;
  grid-template-rows: var(--topbar-h) minmax(0, 1fr) var(--bottombar-h);
  grid-template-columns: 1fr;
  gap: var(--layout-gap);
  padding: var(--layout-pad);
  background: var(--v-bg);
  overflow: hidden;
}

.rs-shell[data-morph="phone-portrait"] {
  grid-template-rows: var(--topbar-h) auto minmax(0, 1fr);
  padding: var(--space-sm);
  gap: var(--space-sm);
  overflow-y: auto;
}

.rs-shell[data-morph="phone-landscape"] {
  grid-template-rows: var(--topbar-h) minmax(0, 1fr);
  padding: var(--space-sm);
  gap: var(--space-sm);
}

.rs-shell[data-morph="phone-portrait"] .rs-body,
.rs-shell[data-morph="phone-landscape"] .rs-body {
  overflow: visible;
}

.rs-topbar {
  grid-column: 1;
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-inline: var(--space-md);
  min-width: 0;
  height: var(--topbar-h);
  overflow-x: auto;
}

.rs-bottombar {
  grid-column: 1;
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: clamp(8px, 1.5vw, 16px);
  padding-inline: var(--space-md);
  font-family: var(--font-mono);
  font-size: var(--font-caption);
  min-width: 0;
  height: var(--bottombar-h);
  overflow-x: auto;
  white-space: nowrap;
}

/* ── 主体三栏 ── */
.rs-body {
  grid-column: 1;
  display: grid;
  grid-template-columns: var(--left-rail-w) minmax(0, 1fr) var(--right-review-w);
  gap: var(--layout-gap);
  min-height: 0;
  overflow: hidden;
  transition: grid-template-columns 0.3s ease;
}

.rs-left-rail,
.rs-right-review,
.rs-workbench {
  overflow: auto;
  min-width: 0;
}

.rs-left-rail {
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding: clamp(8px, 1.5vw, var(--space-md));
}

.rs-right-review {
  background: var(--v-rail);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding: clamp(8px, 1.5vw, var(--space-md));
}

.rs-workbench {
  background: var(--v-panel);
  border: 1px solid var(--v-border);
  border-radius: var(--r4);
  padding: clamp(8px, 2vw, var(--space-lg));
}

/* ── 形态：超宽屏 ── */
.rs-shell[data-morph="ultra-wide"] .rs-body {
  grid-template-columns: var(--left-rail-w) minmax(0, 1fr) var(--right-review-w);
}

/* ── 形态：桌面 ── */
.rs-shell[data-morph="desktop"] .rs-body {
  grid-template-columns: var(--left-rail-w) minmax(0, 1fr) var(--right-review-w);
}

/* ── 形态：平板横屏 ── */
.rs-shell[data-morph="tablet-landscape"] .rs-body {
  grid-template-columns: 200px minmax(0, 1fr) 240px;
}

.rs-shell[data-morph="tablet-landscape"] .rs-left-rail.compact {
  width: 80px;
  overflow: hidden;
  transition: width 0.3s ease;
}

.rs-shell[data-morph="tablet-landscape"] .rs-left-rail.compact:hover {
  width: 200px;
  position: relative;
  z-index: 10;
}

/* ── 形态：平板竖屏 ── */
.rs-shell[data-morph="tablet-portrait"] .rs-body {
  grid-template-columns: 1fr;
  grid-template-rows: auto minmax(0, 1fr);
}

.rs-shell[data-morph="tablet-portrait"] .rs-left-rail {
  max-height: 120px;
  overflow-x: auto;
  overflow-y: hidden;
  display: flex;
  gap: var(--space-sm);
  flex-wrap: nowrap;
  border-radius: var(--r4);
}

/* ── 形态：手机横屏 ── */
.rs-shell[data-morph="phone-landscape"] .rs-body {
  grid-template-columns: 1fr;
}

/* ── 形态：手机竖屏 ── */
.rs-shell[data-morph="phone-portrait"] .rs-body {
  grid-template-columns: 1fr;
}

/* ── 浮动复核灯圆点 ── */
.rs-float-review {
  position: fixed;
  bottom: var(--space-lg);
  right: var(--space-lg);
  z-index: 20;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--v-rail);
  border: 1px solid var(--v-border-strong);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.3);
  transition: all 0.2s;
}

.rs-float-review:hover {
  border-color: var(--v-accent);
  box-shadow: var(--glow-active);
}

.rs-float-review .float-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--v-accent);
  box-shadow: 0 0 12px var(--v-accent-32);
  animation: float-breath 1600ms ease-in-out infinite;
}

@keyframes float-breath {
  0%, 100% { opacity: 0.6; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1); }
}

/* ── 动画过渡 ── */
.rs-shell,
.rs-body {
  transition: grid-template-rows 0.3s ease, grid-template-columns 0.3s ease, gap 0.3s ease, padding 0.3s ease;
}
</style>
