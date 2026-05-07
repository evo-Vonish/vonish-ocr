<template>
  <div class="mini-desk" :style="cssVars">
    <!-- 顶部栏 -->
    <div class="mini-topbar">
      <span class="mini-topbar-brand">VonishOCR</span>
      <span class="mini-topbar-status">LOCAL HELD</span>
    </div>
    <!-- 主体 -->
    <div class="mini-body">
      <!-- 左抽屉 -->
      <div class="mini-left">
        <div class="mini-left-title">EVIDENCE QUEUE</div>
        <div class="mini-left-line"></div>
        <div class="mini-left-line"></div>
      </div>
      <!-- 中央台 -->
      <div class="mini-center">
        <div class="mini-center-ghost">DROP EVIDENCE HERE</div>
      </div>
      <!-- 复核灯 -->
      <div class="mini-right">
        <div class="mini-right-title">AUDIT</div>
        <div class="mini-right-line"></div>
        <div class="mini-right-dot"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  style: { type: String, default: 'desk' },
  mode: { type: String, default: 'dark' }
})

const palette = {
  'desk-dark': {
    bg: '#11110F', rail: '#1A1916', panel: '#222026',
    text: '#E7E1D0', muted: '#A39B8F', border: '#3D383F', accent: '#8FF6D2'
  },
  'desk-light': {
    bg: '#ECE6D8', rail: '#F8F3E7', panel: '#FFFBEF',
    text: '#1A1713', muted: '#5F574B', border: '#C9BEAA', accent: '#0F6B55'
  },
  'mono-dark': {
    bg: '#0A0A0A', rail: '#1A1A1A', panel: '#222222',
    text: '#F5F5F0', muted: '#B0B0B0', border: '#4A4A4A', accent: '#FFFFFF'
  },
  'mono-light': {
    bg: '#F5F5F0', rail: '#E8E8E3', panel: '#FFFFFF',
    text: '#0A0A0A', muted: '#7A7A7A', border: '#C0C0B8', accent: '#0A0A0A'
  },
  'hc-dark': {
    bg: '#000000', rail: '#000000', panel: '#000000',
    text: '#FFFFFF', muted: '#FFFFFF', border: '#FFFFFF', accent: '#FFFFFF'
  },
  'hc-light': {
    bg: '#FFFFFF', rail: '#FFFFFF', panel: '#FFFFFF',
    text: '#000000', muted: '#000000', border: '#000000', accent: '#000000'
  }
}

const cssVars = computed(() => {
  const key = `${props.style}-${props.mode}`
  const p = palette[key] || palette['desk-dark']
  return {
    '--preview-bg': p.bg,
    '--preview-rail': p.rail,
    '--preview-panel': p.panel,
    '--preview-text': p.text,
    '--preview-muted': p.muted,
    '--preview-border': p.border,
    '--preview-accent': p.accent
  }
})
</script>

<style scoped>
.mini-desk {
  width: 100%;
  height: 180px;
  background: var(--preview-bg);
  border: 1px solid var(--preview-border);
  border-radius: var(--r3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.04em;
}

.mini-topbar {
  height: 24px;
  background: var(--preview-rail);
  border-bottom: 1px solid var(--preview-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  color: var(--preview-text);
}

.mini-topbar-status {
  color: var(--preview-accent);
}

.mini-body {
  flex: 1;
  display: grid;
  grid-template-columns: 60px 1fr 50px;
  gap: 4px;
  padding: 4px;
}

.mini-left {
  background: var(--preview-rail);
  border: 1px solid var(--preview-border);
  border-radius: var(--r2);
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.mini-left-title {
  color: var(--preview-accent);
  font-size: 7px;
  margin-bottom: 2px;
}

.mini-left-line {
  height: 8px;
  background: var(--preview-panel);
  border: 1px solid var(--preview-border);
  border-radius: var(--r1);
}

.mini-center {
  background: var(--preview-panel);
  border: 1px solid var(--preview-border);
  border-radius: var(--r2);
  display: grid;
  place-items: center;
}

.mini-center-ghost {
  color: var(--preview-muted);
  font-size: 8px;
  text-align: center;
}

.mini-right {
  background: var(--preview-rail);
  border: 1px solid var(--preview-border);
  border-radius: var(--r2);
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.mini-right-title {
  color: var(--preview-accent);
  font-size: 7px;
}

.mini-right-line {
  height: 20px;
  background: var(--preview-panel);
  border: 1px solid var(--preview-border);
  border-radius: var(--r1);
}

.mini-right-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid var(--preview-border);
  margin-top: auto;
}
</style>
