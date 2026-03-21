<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

const booting = ref(true)
const runState = ref('idle')
const outputLog = ref('')
const runtime = ref(null)
const backgroundLibrary = ref({ groups: [], images: [] })
const devices = ref([])
const textFonts = ref([])
const mathFonts = ref([])
const formulaRenderers = ref([])
const persistTimer = ref(null)
const rustScanSummary = ref(null)

const settings = reactive({
  local_path: '',
  output_dir: '.dailytipsapp',
  cloud_dir: 'C:/Users/lky14/iCloudDrive/DailyTips',
  device_model: 'iphone_17_pro',
  width: '1206',
  height: '2622',
  background_mode: 'white',
  background_group: '',
  background_image_id: '',
  show_content_panel: true,
  panel_opacity: 212,
  text_font_family: 'microsoft_yahei',
  math_font_family: 'dejavusans',
  formula_renderer: 'auto',
  text_color: '#000000',
  math_color: '#000000',
})

async function tauriInvoke(command, payload = {}) {
  const globalInvoke = window.__TAURI__?.core?.invoke
  if (typeof globalInvoke === 'function') {
    return globalInvoke(command, payload)
  }

  const module = await import('@tauri-apps/api/core')
  if (typeof module.invoke === 'function') {
    return module.invoke(command, payload)
  }

  throw new Error('Tauri invoke is unavailable in the current runtime.')
}

async function tauriOpen(options) {
  const module = await import('@tauri-apps/plugin-dialog')
  if (typeof module.open === 'function') {
    return module.open(options)
  }
  throw new Error('Tauri dialog plugin is unavailable in the current runtime.')
}

const isRunning = computed(() => runState.value === 'running')

const rendererStatus = computed(() => {
  const effective = runtime.value?.formulaBackendEffective ?? runtime.value?.formula_backend_effective
  if (effective === 'tectonic') return '当前使用 Tectonic LaTeX'
  if (effective === 'matplotlib') return '当前使用 Matplotlib MathText'
  if (effective === 'plain') return '当前回退到纯文本模式'
  return '正在检测公式渲染环境...'
})

const runtimeSummary = computed(() => {
  const pythonOk = runtime.value?.pythonOk ?? runtime.value?.python_ok
  const tectonicBundled = runtime.value?.tectonicBundled ?? runtime.value?.tectonic_bundled
  const repoRoot = runtime.value?.repoRoot ?? runtime.value?.repo_root ?? '-'

  return [
    pythonOk ? 'Python 渲染后端已就绪' : '未找到可用的 Python 渲染后端',
    tectonicBundled ? '已检测到内置 Tectonic' : '未检测到内置 Tectonic，将按规则回退',
    `项目目录：${repoRoot}`,
    rendererStatus.value,
  ]
})

const specificImageOptions = computed(() => {
  if (!settings.background_group) return backgroundLibrary.value.images
  return backgroundLibrary.value.images.filter((image) => image.groupName === settings.background_group)
})

function normalizeOption(item) {
  if (typeof item === 'string') {
    return { key: item, label: item, width: undefined, height: undefined }
  }
  if (!item || typeof item !== 'object') {
    return { key: '', label: '' }
  }
  return {
    key: item.key ?? item.id ?? item.value ?? '',
    label: item.label ?? item.name ?? item.title ?? item.key ?? item.id ?? '',
    width: item.width,
    height: item.height,
  }
}

function normalizeOptionLabel(key, fallbackLabel) {
  const labelMap = {
    auto: '自动（推荐）',
    tectonic: 'Tectonic LaTeX',
    matplotlib: 'Matplotlib MathText',
    custom: '自定义',
    microsoft_yahei: 'Microsoft YaHei',
    simhei: 'SimHei',
    simsun: 'SimSun',
    dejavusans: 'DejaVu Sans',
    stixsans: 'STIX Sans',
    dejavuserif: 'DejaVu Serif',
    stix: 'STIX',
    cm: 'Computer Modern',
  }
  return labelMap[key] ?? fallbackLabel ?? key
}

function normalizeOptions(items) {
  return Array.isArray(items)
    ? items
        .map(normalizeOption)
        .map((item) => ({
          ...item,
          label: normalizeOptionLabel(item.key, item.label),
        }))
        .filter((item) => item.key)
    : []
}

function normalizeLibrary(library) {
  const groups = Array.isArray(library?.groups) ? library.groups.map((group) => String(group)) : []
  const images = Array.isArray(library?.images)
    ? library.images
        .map((image) => ({
          id: image?.id ?? '',
          groupName: image?.groupName ?? image?.group_name ?? '',
          name: image?.name ?? image?.id ?? '',
          path: image?.path ?? '',
        }))
        .filter((image) => image.id)
    : []
  return { groups, images }
}

function appendLog(message) {
  outputLog.value = `${outputLog.value}${outputLog.value ? '\n' : ''}${message}`
}

function applySettings(nextSettings = {}) {
  Object.assign(settings, nextSettings)
}

function setLibrary(library) {
  backgroundLibrary.value = normalizeLibrary(library)
  const groups = backgroundLibrary.value.groups
  const images = backgroundLibrary.value.images

  if (groups.length > 0 && !groups.includes(settings.background_group)) {
    settings.background_group = groups[0]
  }
  if (groups.length === 0) {
    settings.background_group = ''
  }

  const visibleImageIds = specificImageOptions.value.map((image) => image.id)
  if (visibleImageIds.length > 0 && !visibleImageIds.includes(settings.background_image_id)) {
    settings.background_image_id = visibleImageIds[0]
  }
  if (visibleImageIds.length === 0) {
    const allImageIds = images.map((image) => image.id)
    settings.background_image_id = allImageIds[0] ?? ''
  }
}

function ensureOptionSelections() {
  const deviceKeys = devices.value.map((item) => item.key)
  if (deviceKeys.length > 0 && !deviceKeys.includes(settings.device_model)) {
    settings.device_model = deviceKeys[0]
  }

  const rendererKeys = formulaRenderers.value.map((item) => item.key)
  if (rendererKeys.length > 0 && !rendererKeys.includes(settings.formula_renderer)) {
    settings.formula_renderer = rendererKeys[0]
  }

  const textFontKeys = textFonts.value.map((item) => item.key)
  if (textFontKeys.length > 0 && !textFontKeys.includes(settings.text_font_family)) {
    settings.text_font_family = textFontKeys[0]
  }

  const mathFontKeys = mathFonts.value.map((item) => item.key)
  if (mathFontKeys.length > 0 && !mathFontKeys.includes(settings.math_font_family)) {
    settings.math_font_family = mathFontKeys[0]
  }
}

function syncDeviceDimensions() {
  const profile = devices.value.find((item) => item.key === settings.device_model)
  if (profile && profile.key !== 'custom') {
    settings.width = String(profile.width)
    settings.height = String(profile.height)
  }
}

async function bootstrap() {
  booting.value = true
  try {
    const data = await tauriInvoke('bootstrap_app_state')
    applySettings(data?.settings ?? {})
    devices.value = normalizeOptions(data?.devices ?? data?.deviceProfiles)
    textFonts.value = normalizeOptions(data?.textFonts ?? data?.text_fonts)
    mathFonts.value = normalizeOptions(data?.mathFonts ?? data?.math_fonts)
    formulaRenderers.value = normalizeOptions(data?.formulaRenderers ?? data?.formula_renderers)
    runtime.value = data?.runtime ?? null
    setLibrary(data?.backgroundLibrary ?? data?.background_library)
    ensureOptionSelections()
    syncDeviceDimensions()
    outputLog.value = '桌面端已就绪，当前仅支持本地 Markdown 目录工作流。'
  } catch (error) {
    const message = error?.message ?? String(error)
    outputLog.value = `启动失败：${message}`
    throw error
  } finally {
    booting.value = false
  }
}

async function persistSettingsNow() {
  const data = await tauriInvoke('save_app_settings', { settings: { ...settings } })
  applySettings(data?.settings ?? {})
  runtime.value = data?.runtime ?? runtime.value
}

watch(
  () => ({ ...settings }),
  () => {
    if (booting.value) return
    clearTimeout(persistTimer.value)
    persistTimer.value = setTimeout(() => {
      persistSettingsNow().catch((error) => {
        appendLog(`保存设置失败：${error?.message ?? error}`)
      })
    }, 250)
  },
  { deep: true },
)

watch(
  () => settings.device_model,
  () => syncDeviceDimensions(),
)

watch(
  () => settings.background_group,
  () => {
    const visibleImageIds = specificImageOptions.value.map((image) => image.id)
    if (visibleImageIds.length > 0 && !visibleImageIds.includes(settings.background_image_id)) {
      settings.background_image_id = visibleImageIds[0]
    }
    if (visibleImageIds.length === 0 && settings.background_mode === 'specific') {
      settings.background_image_id = ''
    }
  },
)

async function pickDirectory(fieldName) {
  const selected = await tauriOpen({ directory: true, multiple: false })
  if (typeof selected === 'string') {
    settings[fieldName] = selected
  }
}

async function importImages() {
  if (!settings.background_group) {
    appendLog('请先选择一个背景分组。')
    return
  }
  const selected = await tauriOpen({
    multiple: true,
    filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp', 'bmp'] }],
  })
  if (!selected || !Array.isArray(selected) || selected.length === 0) return

  try {
    const library = await tauriInvoke('import_background_images', {
      payload: { groupName: settings.background_group, paths: selected },
    })
    setLibrary(library)
    appendLog(`已导入 ${selected.length} 张背景图到分组 ${settings.background_group}。`)
  } catch (error) {
    appendLog(error?.message ?? String(error))
  }
}

async function previewRustScan() {
  if (!settings.local_path.trim()) {
    appendLog('请先选择本地 Markdown 目录。')
    return
  }
  try {
    const summary = await tauriInvoke('scan_local_markdown', { payload: { notesDir: settings.local_path } })
    rustScanSummary.value = summary
    appendLog(`Rust 预扫描完成：发现 ${summary.markdownFileCount} 个 Markdown 文件，识别 ${summary.itemCount} 个条目。`)
  } catch (error) {
    appendLog(error?.message ?? String(error))
  }
}

async function runGenerator() {
  runState.value = 'running'
  outputLog.value = ''
  try {
    const data = await tauriInvoke('run_generation_pipeline', { settings: { ...settings } })
    runtime.value = data?.runtime ?? runtime.value
    setLibrary(data?.backgroundLibrary ?? data?.background_library)
    const summary = data?.summary ?? {}
    appendLog(`来源：${summary.source_description ?? summary.sourceDescription ?? '-'}`)
    appendLog(`扫描 Markdown 文件：${summary.markdown_file_count ?? summary.markdownFileCount ?? 0}`)
    appendLog(`识别条目：${summary.item_count ?? summary.itemCount ?? 0}`)
    appendLog(`输出图片：${summary.image_count ?? summary.imageCount ?? 0}`)
    appendLog(
      `新增 ${summary.created_count ?? summary.createdCount ?? 0}，更新 ${summary.updated_count ?? summary.updatedCount ?? 0}，未变 ${
        summary.unchanged_count ?? summary.unchangedCount ?? 0
      }，删除 ${summary.deleted_count ?? summary.deletedCount ?? 0}`,
    )
    appendLog(`元数据目录：${summary.data_dir ?? summary.dataDir ?? '-'}`)
    appendLog(`云盘目录：${summary.cloud_dir ?? summary.cloudDir ?? '-'}`)
    appendLog(`索引文件：${summary.index_path ?? summary.indexPath ?? '-'}`)
    runState.value = 'success'
  } catch (error) {
    appendLog(error?.message ?? String(error))
    runState.value = 'error'
  }
}

async function clearGenerated() {
  if (!window.confirm('这会清空生成图片与元数据，是否继续？')) return
  try {
    const summary = await tauriInvoke('clear_generated_outputs_in_rust', { settings: { ...settings } })
    appendLog(
      `已清空：元数据 ${summary.removedMetadataCount} 项，图片 ${summary.removedCloudCount} 张，索引 ${summary.removedIndexCount} 个。`,
    )
  } catch (error) {
    appendLog(error?.message ?? String(error))
  }
}

async function clearLibrary() {
  if (!window.confirm('这会清空背景图库中的用户图片，是否继续？')) return
  try {
    const library = await tauriInvoke('clear_background_library')
    setLibrary(library)
    appendLog('背景图库已清空。')
  } catch (error) {
    appendLog(error?.message ?? String(error))
  }
}

async function addGroup() {
  const name = window.prompt('请输入新分组名称：')?.trim()
  if (!name) return
  try {
    const library = await tauriInvoke('create_background_group', { payload: { name } })
    setLibrary(library)
    settings.background_group = name.replace(/[\\/]/g, '_')
    appendLog(`已创建分组：${settings.background_group}`)
  } catch (error) {
    appendLog(error?.message ?? String(error))
  }
}

async function deleteGroup() {
  if (!settings.background_group) return
  if (!window.confirm(`确定删除分组 ${settings.background_group} 吗？`)) return
  try {
    const target = settings.background_group
    const library = await tauriInvoke('delete_background_group', { payload: { groupName: target } })
    setLibrary(library)
    appendLog(`已删除分组：${target}`)
  } catch (error) {
    appendLog(error?.message ?? String(error))
  }
}

async function deleteImage() {
  if (!settings.background_image_id) return
  if (!window.confirm(`确定删除背景图 ${settings.background_image_id} 吗？`)) return
  try {
    const target = settings.background_image_id
    const library = await tauriInvoke('delete_background_image', { payload: { imageId: target } })
    setLibrary(library)
    appendLog(`已删除背景图：${target}`)
  } catch (error) {
    appendLog(error?.message ?? String(error))
  }
}

onMounted(() => {
  bootstrap().catch(() => {})
})
</script>

<template>
  <div class="shell">
    <div class="hero">
      <div>
        <p class="eyebrow">DailyTipsApp Desktop</p>
        <h1>公式壁纸生成器</h1>
        <p class="hero-copy">扫描本地 Markdown 笔记，提取知识点，生成锁屏公式壁纸，并同步到云盘目录。</p>
      </div>
      <div class="status-card">
        <p class="status-title">运行状态</p>
        <p v-for="line in runtimeSummary" :key="line">{{ line }}</p>
      </div>
    </div>

    <div class="grid">
      <section class="panel stack-lg">
        <div class="section-head">
          <div>
            <h2>生成配置</h2>
            <p class="section-copy">当前桌面端使用 Rust 负责扫描和增量判断，再调用渲染后端生成图片。</p>
          </div>
          <span :class="['pill', runState]">{{ runState }}</span>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>iPhone 型号</span>
            <select v-model="settings.device_model">
              <option v-for="device in devices" :key="device.key" :value="device.key">
                {{ device.label || device.key }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>公式渲染引擎</span>
            <select v-model="settings.formula_renderer">
              <option v-for="renderer in formulaRenderers" :key="renderer.key" :value="renderer.key">
                {{ renderer.label || renderer.key }}
              </option>
            </select>
          </label>
        </div>

        <label class="field">
          <span>本地笔记目录</span>
          <div class="input-action">
            <input v-model="settings.local_path" placeholder="D:/path/to/your/notes" />
            <button class="ghost small" type="button" @click="pickDirectory('local_path')">选择</button>
          </div>
        </label>

        <div class="two-up compact">
          <label class="field">
            <span>云盘图片目录</span>
            <div class="input-action">
              <input v-model="settings.cloud_dir" placeholder="C:/Users/yourname/iCloudDrive/DailyTips" />
              <button class="ghost small" type="button" @click="pickDirectory('cloud_dir')">选择</button>
            </div>
          </label>
          <label class="field">
            <span>应用数据目录</span>
            <input v-model="settings.output_dir" placeholder=".dailytipsapp" />
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>宽度</span>
            <input v-model="settings.width" :disabled="settings.device_model !== 'custom'" />
          </label>
          <label class="field">
            <span>高度</span>
            <input v-model="settings.height" :disabled="settings.device_model !== 'custom'" />
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>背景模式</span>
            <select v-model="settings.background_mode">
              <option value="white">纯白背景</option>
              <option value="specific">指定图片</option>
              <option value="random_group">指定分组随机</option>
              <option value="random_all">全部随机</option>
            </select>
          </label>
          <label class="field">
            <span>背景分组</span>
            <select v-model="settings.background_group">
              <option value="">未选择</option>
              <option v-for="group in backgroundLibrary.groups" :key="group" :value="group">
                {{ group }}
              </option>
            </select>
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>指定背景图</span>
            <select v-model="settings.background_image_id">
              <option value="">未选择</option>
              <option v-for="image in specificImageOptions" :key="image.id" :value="image.id">
                {{ image.id }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>正文字体</span>
            <select v-model="settings.text_font_family">
              <option v-for="font in textFonts" :key="font.key" :value="font.key">
                {{ font.label || font.key }}
              </option>
            </select>
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>公式字体</span>
            <select v-model="settings.math_font_family">
              <option v-for="font in mathFonts" :key="font.key" :value="font.key">
                {{ font.label || font.key }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>正文字色</span>
            <input v-model="settings.text_color" type="color" />
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>公式颜色</span>
            <input v-model="settings.math_color" type="color" />
          </label>
          <label class="field inline-toggle">
            <span>显示内容卡片</span>
            <input v-model="settings.show_content_panel" type="checkbox" />
          </label>
        </div>

        <label class="field">
          <span>卡片透明度</span>
          <input v-model="settings.panel_opacity" type="range" min="0" max="255" />
          <small>{{ settings.panel_opacity }}</small>
        </label>

        <div class="actions">
          <button class="ghost" type="button" @click="previewRustScan" :disabled="isRunning">Rust 预扫描</button>
          <button class="danger" type="button" @click="clearGenerated" :disabled="isRunning">清空生成结果</button>
          <button class="primary" type="button" @click="runGenerator" :disabled="isRunning || booting">
            {{ isRunning ? '生成中...' : '开始生成' }}
          </button>
        </div>

        <div v-if="rustScanSummary" class="preview-card">
          <h3>Rust 预扫描结果</h3>
          <p>Markdown 文件：{{ rustScanSummary.markdownFileCount }}</p>
          <p>识别条目：{{ rustScanSummary.itemCount }}</p>
          <p v-if="rustScanSummary.items?.length">首条标题：{{ rustScanSummary.items[0].title }}</p>
          <p v-if="rustScanSummary.items?.length">
            来源：{{ rustScanSummary.items[0].sourcePath }}:{{ rustScanSummary.items[0].sourceLine }}
          </p>
        </div>

        <label class="field">
          <span>运行日志</span>
          <textarea v-model="outputLog" rows="10" readonly />
        </label>
      </section>

      <section class="panel stack-lg">
        <div class="section-head">
          <div>
            <h2>背景图库</h2>
            <p class="section-copy">支持分组管理、导入背景图，并按规则参与渲染。</p>
          </div>
          <button class="ghost small" type="button" @click="importImages">导入图片</button>
        </div>

        <div class="library-grid">
          <div>
            <div class="library-head">
              <h3>分组</h3>
              <div class="mini-actions">
                <button class="ghost small" type="button" @click="addGroup">新增</button>
                <button class="danger small" type="button" @click="deleteGroup">删除</button>
              </div>
            </div>
            <div class="list-box">
              <button
                v-for="group in backgroundLibrary.groups"
                :key="group"
                type="button"
                :class="['list-item', { active: group === settings.background_group }]"
                @click="settings.background_group = group"
              >
                {{ group }}
              </button>
            </div>
          </div>

          <div>
            <div class="library-head">
              <h3>图片</h3>
              <div class="mini-actions">
                <button class="danger small" type="button" @click="deleteImage">删除</button>
                <button class="ghost small" type="button" @click="clearLibrary">清空图库</button>
              </div>
            </div>
            <div class="list-box">
              <button
                v-for="image in specificImageOptions"
                :key="image.id"
                type="button"
                :class="['list-item', { active: image.id === settings.background_image_id }]"
                @click="settings.background_image_id = image.id"
              >
                {{ image.id }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
:global(body) {
  margin: 0;
  font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
  background: linear-gradient(180deg, #f5fbff 0%, #eef4ff 100%);
  color: #16324f;
}

:global(*) {
  box-sizing: border-box;
}

.shell {
  min-height: 100vh;
  padding: 28px;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: stretch;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 10px;
  color: #5b7997;
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: 40px;
  line-height: 1.1;
}

.hero-copy,
.section-copy,
.status-card p,
.preview-card p,
small {
  color: #5f7691;
}

.status-card,
.panel,
.preview-card {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(110, 154, 191, 0.22);
  box-shadow: 0 18px 40px rgba(87, 121, 155, 0.12);
  backdrop-filter: blur(18px);
}

.status-card {
  min-width: 320px;
  border-radius: 24px;
  padding: 20px 22px;
}

.status-title {
  margin: 0 0 12px;
  font-weight: 700;
  color: #24486d;
}

.grid {
  display: grid;
  grid-template-columns: 1.35fr 0.95fr;
  gap: 24px;
}

.panel {
  border-radius: 28px;
  padding: 24px;
}

.stack-lg {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.section-head,
.library-head,
.actions,
.mini-actions,
.input-action,
.two-up,
.library-grid {
  display: flex;
  gap: 14px;
}

.section-head,
.library-head {
  justify-content: space-between;
  align-items: flex-start;
}

.library-grid,
.two-up {
  align-items: stretch;
}

.library-grid > *,
.two-up > * {
  flex: 1;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  color: #355372;
}

.field span {
  font-weight: 600;
}

.inline-toggle {
  justify-content: center;
}

input,
select,
textarea,
button {
  font: inherit;
}

input,
select,
textarea {
  width: 100%;
  border-radius: 16px;
  border: 1px solid rgba(111, 166, 194, 0.4);
  background: rgba(255, 255, 255, 0.96);
  padding: 14px 16px;
  color: #173251;
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

input:focus,
select:focus,
textarea:focus {
  border-color: #50adc9;
  box-shadow: 0 0 0 4px rgba(80, 173, 201, 0.14);
}

input[type='checkbox'] {
  width: auto;
  transform: scale(1.15);
  accent-color: #3f90ff;
}

input[type='color'] {
  min-height: 52px;
  padding: 8px;
}

input[type='range'] {
  padding: 0;
  background: transparent;
  border: none;
  box-shadow: none;
}

textarea {
  resize: vertical;
}

.input-action {
  align-items: center;
}

.input-action input {
  flex: 1;
}

button {
  border: none;
  border-radius: 16px;
  padding: 14px 18px;
  cursor: pointer;
  font-weight: 700;
  transition: transform 0.14s ease, box-shadow 0.14s ease, opacity 0.14s ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
}

button:disabled {
  opacity: 0.56;
  cursor: not-allowed;
}

.primary {
  background: linear-gradient(135deg, #3074ff 0%, #1c5cff 100%);
  color: #ffffff;
  box-shadow: 0 12px 28px rgba(48, 116, 255, 0.24);
}

.ghost {
  background: rgba(255, 255, 255, 0.92);
  color: #2f557d;
  border: 1px solid rgba(111, 166, 194, 0.36);
}

.danger {
  background: #f04e5e;
  color: #ffffff;
  box-shadow: 0 12px 28px rgba(240, 78, 94, 0.22);
}

.small {
  padding: 10px 14px;
  border-radius: 14px;
}

.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 88px;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.pill.idle {
  background: rgba(128, 146, 166, 0.12);
  color: #5f7691;
}

.pill.running {
  background: rgba(53, 138, 255, 0.16);
  color: #2167dd;
}

.pill.success {
  background: rgba(43, 177, 120, 0.16);
  color: #1b8f5d;
}

.pill.error {
  background: rgba(240, 78, 94, 0.14);
  color: #cc3040;
}

.preview-card {
  border-radius: 22px;
  padding: 16px 18px;
}

.preview-card h3,
.library-head h3,
.section-head h2 {
  margin: 0 0 6px;
}

.list-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 280px;
  max-height: 420px;
  overflow: auto;
  padding: 8px;
  border-radius: 20px;
  background: rgba(244, 249, 255, 0.9);
  border: 1px solid rgba(111, 166, 194, 0.2);
}

.list-item {
  text-align: left;
  background: #ffffff;
  color: #27496f;
  border: 1px solid transparent;
  box-shadow: none;
}

.list-item.active {
  background: linear-gradient(135deg, rgba(60, 123, 255, 0.14), rgba(88, 200, 255, 0.12));
  border-color: rgba(60, 123, 255, 0.25);
}

@media (max-width: 1200px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .hero {
    flex-direction: column;
  }

  .status-card {
    min-width: 0;
  }
}

@media (max-width: 820px) {
  .shell {
    padding: 18px;
  }

  h1 {
    font-size: 32px;
  }

  .two-up,
  .library-grid,
  .section-head {
    flex-direction: column;
  }
}
</style>
