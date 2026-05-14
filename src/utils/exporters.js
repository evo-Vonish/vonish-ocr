import JSZip from 'jszip'

function escapeXml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')
}

function safeName(name = 'ocr-result') {
  return String(name).replace(/\.[^.]+$/, '').replace(/[\\/:*?"<>|]/g, '_') || 'ocr-result'
}

function getPolished(result = {}) {
  return result.ai?.polished || result.text || ''
}

function getRaw(result = {}) {
  return result.text || ''
}

export function buildExportText(result, mode = 'polished', filename = 'ocr-result') {
  const raw = getRaw(result)
  const polished = getPolished(result)
  if (mode === 'raw') return raw
  if (mode === 'compare') {
    return [
      `# ${safeName(filename)} 双结果对比`,
      '',
      '## 原文本',
      '',
      raw || '（无内容）',
      '',
      '## 修复后',
      '',
      polished || '（无内容）',
      '',
      '## Diff',
      '',
      ...(result.ai?.diff || []).map(d => `- ${d.original || '-'} -> ${d.fixed || '-'}${d.reason ? `：${d.reason}` : ''}`),
    ].join('\n')
  }
  return polished
}

export function buildMarkdown(result, mode = 'polished', filename = 'ocr-result') {
  const title = safeName(filename)
  const body = buildExportText(result, mode, filename)
  if (mode === 'raw') return `# ${title} 原文本\n\n${body}\n`
  if (mode === 'polished') return `# ${title} 修复后\n\n${body}\n`
  return `${body}\n`
}

function docParagraph(text) {
  const lines = String(text || '').split(/\r?\n/)
  return lines.map(line => `<w:p><w:r><w:t xml:space="preserve">${escapeXml(line || ' ')}</w:t></w:r></w:p>`).join('')
}

function buildDocXml(sections) {
  const content = sections.map((section, index) => {
    const breakPage = index > 0 ? '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' : ''
    return `${breakPage}<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>${escapeXml(section.title)}</w:t></w:r></w:p>${docParagraph(section.body)}`
  }).join('')
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>${content}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body>
</w:document>`
}

async function makeDocxBlob(sections) {
  const zip = new JSZip()
  zip.file('[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>`)
  zip.folder('_rels').file('.rels', `<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`)
  zip.folder('word').file('document.xml', buildDocXml(sections))
  return zip.generateAsync({ type: 'blob', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
}

export async function downloadBlob(blobOrText, filename, mimeType = 'text/plain;charset=utf-8') {
  const blob = blobOrText instanceof Blob ? blobOrText : new Blob([blobOrText], { type: mimeType })

  // 优先原生保存对话框
  if (typeof window !== 'undefined' && window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({ suggestedName: filename, types: [{ accept: { [mimeType]: [`.${filename.split('.').pop() || 'txt'}`] } }] })
      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()
      return true
    } catch (e) {
      if (e?.name === 'AbortError') return false // user cancelled
      console.warn('原生保存对话框失败，降级浏览器下载:', e)
    }
  }

  // 浏览器兜底
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  return true
}

export async function exportSingle(result, filename, mode, format) {
  const base = safeName(filename)
  if (format === 'txt') {
    await downloadBlob(buildExportText(result, mode, filename), `${base}.txt`, 'text/plain;charset=utf-8')
  } else if (format === 'md') {
    await downloadBlob(buildMarkdown(result, mode, filename), `${base}.md`, 'text/markdown;charset=utf-8')
  } else if (format === 'docx') {
    const blob = await makeDocxBlob([{ title: `${base} ${modeLabel(mode)}`, body: buildExportText(result, mode, filename) }])
    await downloadBlob(blob, `${base}.docx`)
  }
}

export async function copyResult(result, mode = 'polished') {
  await navigator.clipboard.writeText(buildExportText(result, mode))
}

export async function exportBatch(items, { mode = 'polished', format = 'md', output = 'zip', onProgress } = {}) {
  const completed = items.filter(item => item.result)
  if (!completed.length) return
  if (output === 'merged') {
    const title = `vonish-ocr-${modeLabel(mode)}`
    if (format === 'docx') {
      const sections = completed.map(({ task, result }) => ({
        title: `${safeName(task.name)} ${modeLabel(mode)}`,
        body: buildExportText(result, mode, task.name),
      }))
      const blob = await makeDocxBlob(sections)
      await downloadBlob(blob, `${title}.docx`)
    } else {
      const ext = format === 'txt' ? 'txt' : 'md'
      const body = completed.map(({ task, result }) => buildMarkdown(result, mode, task.name)).join('\n\n---\n\n')
      await downloadBlob(body, `${title}.${ext}`, ext === 'md' ? 'text/markdown;charset=utf-8' : 'text/plain;charset=utf-8')
    }
    onProgress?.(completed.length, completed.length)
    return
  }

  const zip = new JSZip()
  for (let i = 0; i < completed.length; i += 1) {
    const { task, result } = completed[i]
    const base = safeName(task.name)
    if (format === 'docx') {
      zip.file(`${base}.docx`, await makeDocxBlob([{ title: `${base} ${modeLabel(mode)}`, body: buildExportText(result, mode, task.name) }]))
    } else if (format === 'txt') {
      zip.file(`${base}.txt`, buildExportText(result, mode, task.name))
    } else {
      zip.file(`${base}.md`, buildMarkdown(result, mode, task.name))
    }
    onProgress?.(i + 1, completed.length)
    // 中文注释：批量保存逐项写入 ZIP，给浏览器事件循环让步，避免一次性阻塞界面。
    await new Promise(resolve => setTimeout(resolve, 0))
  }
  const blob = await zip.generateAsync({ type: 'blob' })
  await downloadBlob(blob, `vonish-ocr-${modeLabel(mode)}.zip`, 'application/zip')
}

export function modeLabel(mode) {
  return ({ raw: '原文本', polished: '修复后', compare: '双结果对比' })[mode] || mode
}
