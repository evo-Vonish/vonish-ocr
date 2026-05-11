<template>
  <div class="mini-desk" :style="cssVars" :data-preview-appearance="style">
    <div class="mini-topbar">
      <span class="mini-topbar-brand">VonishOCR</span>
      <span class="mini-topbar-status">LOCAL HELD</span>
    </div>
    <div class="mini-body">
      <div class="mini-left">
        <div class="mini-left-title">QUEUE</div>
        <div class="mini-left-line"></div>
        <div class="mini-left-line"></div>
      </div>
      <div class="mini-center">
        <div class="mini-grid"></div>
        <div class="mini-center-ghost">DROP EVIDENCE HERE</div>
      </div>
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
  style: { type: String, default: 'evidence' },
  mode: { type: String, default: 'dark' }
})

const palette = {
  'evidence-dark': {
    bg: '#11110F', rail: '#1A1916', panel: '#222026',
    text: '#E7E1D0', muted: '#A39B8F', border: '#3D383F', accent: '#8FF6D2', grid: '#8FF6D214'
  },
  'evidence-light': {
    bg: '#F3EFE4', rail: '#E7E1D0', panel: '#DDD7C8',
    text: '#11110F', muted: '#6B6560', border: '#C5BFB3', accent: '#8FF6D2', grid: '#1A3D3214'
  },
  'professional-dark': {
    bg: '#101114', rail: '#181A1F', panel: '#20232A',
    text: '#ECE7DC', muted: '#A9A49A', border: '#3A3F49', accent: '#8FF6D2', grid: 'transparent'
  },
  'professional-light': {
    bg: '#F6F5F1', rail: '#FFFFFF', panel: '#ECE9E1',
    text: '#161615', muted: '#5F5A52', border: '#C9C4BA', accent: '#217C68', grid: 'transparent'
  },
  'hc-dark': {
    bg: '#000000', rail: '#000000', panel: '#000000',
    text: '#FFFFFF', muted: '#FFFFFF', border: '#FFFFFF', accent: '#FFFFFF', grid: 'transparent'
  },
  'hc-light': {
    bg: '#000000', rail: '#000000', panel: '#000000',
    text: '#FFFFFF', muted: '#FFFFFF', border: '#FFFFFF', accent: '#FFFFFF', grid: 'transparent'
  }
}

const cssVars = computed(() => {
  const style = props.style === 'desk' ? 'evidence' : props.style === 'mono' ? 'professional' : props.style
  const key = style === 'hc' ? 'hc-dark' : `${style}-${props.mode}`
  const p = palette[key] || palette['evidence-dark']
  return {
    '--preview-bg': p.bg,
    '--preview-rail': p.rail,
    '--preview-panel': p.panel,
    '--preview-text': p.text,
    '--preview-muted': p.muted,
    '--preview-border': p.border,
    '--preview-accent': p.accent,
    '--preview-grid': p.grid
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

.mini-topbar-status,
.mini-left-title,
.mini-right-title {
  color: var(--preview-accent);
}

.mini-body {
  flex: 1;
  display: grid;
  grid-template-columns: 60px 1fr 50px;
  gap: 4px;
  padding: 4px;
}

.mini-left,
.mini-right {
  background: var(--preview-rail);
  border: 1px solid var(--preview-border);
  border-radius: var(--r2);
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.mini-left-line,
.mini-right-line {
  background: var(--preview-panel);
  border: 1px solid var(--preview-border);
  border-radius: var(--r1);
}

.mini-left-line {
  height: 8px;
}

.mini-right-line {
  height: 20px;
}

.mini-center {
  position: relative;
  background: var(--preview-panel);
  border: 1px solid var(--preview-border);
  border-radius: var(--r2);
  display: grid;
  place-items: center;
  overflow: hidden;
}

.mini-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, var(--preview-grid) 1px, transparent 1px),
    linear-gradient(to bottom, var(--preview-grid) 1px, transparent 1px);
  background-size: 16px 16px;
}

.mini-center-ghost {
  position: relative;
  color: var(--preview-muted);
  font-size: 8px;
  text-align: center;
}

.mini-right-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid var(--preview-border);
  margin-top: auto;
}
</style>
