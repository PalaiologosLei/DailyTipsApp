<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { invoke } from '@tauri-apps/api/core'
import { open } from '@tauri-apps/plugin-dialog'

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

const rendererStatus = computed(() => runtime.value?.formulaSupport ?? '正在检测公式引擎...')
const isRunning = computed(() => runState.value === 'running')
const selectedGroupImages = computed(() => {
  if (!settings.background_group) return backgroundLibrary.value.images
  return backgroundLibrary.value.images.filter((image) => image.groupName === settings.background_group)
})

function appendLog(message) {
  outputLog.value = `${outputLog.value}${outputLog.value ? '\n' : ''}${message}`
}

function applySettings(nextSettings = {}) {
  Object.assign(settings, nextSettings)
}

function setLibrary(library) {
  backgroundLibrary.value = library ?? { groups: [], images: [] }
  const groups = backgroundLibrary.value.groups ?? []
  const images = backgroundLibrary.value.images ?? []

  if (groups.length && !groups.includes(settings.background_group)) {
    settings.background_group = groups[0]
  }
  if (!groups.length) settings.background_group = ''

  const imageIds = images.map((item) => item.id)
  if (imageIds.length && !imageIds.includes(settings.background_image_id)) {
    settings.background_image_id = imageIds[0]
  }
  if (!imageIds.length) settings.background_image_id = ''
}

function ensureOptionSelections() {
  const deviceKeys = devices.value.map((item) => item.key)
  if (deviceKeys.length && !deviceKeys.includes(settings.device_model)) settings.device_model = deviceKeys[0]

  const rendererKeys = formulaRenderers.value.map((item) => item.key)
  if (rendererKeys.length && !rendererKeys.includes(settings.formula_renderer)) settings.formula_renderer = rendererKeys[0]

  const textFontKeys = textFonts.value.map((item) => item.key)
  if (textFontKeys.length && !textFontKeys.includes(settings.text_font_family)) settings.text_font_family = textFontKeys[0]

  const mathFontKeys = mathFonts.value.map((item) => item.key)
  if (mathFontKeys.length && !mathFontKeys.includes(settings.math_font_family)) settings.math_font_family = mathFontKeys[0]
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
    const data = await invoke('bootstrap_app_state')
    applySettings(data.settings)
    devices.value = data.devices
    textFonts.value = data.textFonts
    mathFonts.value = data.mathFonts
    formulaRenderers.value = data.formulaRenderers
    runtime.value = data.runtime
    setLibrary(data.backgroundLibrary)
    ensureOptionSelections()
    syncDeviceDimensions()
    outputLog.value = '桌面端已就绪，当前使用本地 Markdown 目录。'
  } finally {
    booting.value = false
  }
}

async function persistSettingsNow() {
  const data = await invoke('save_app_settings', { settings: { ...settings } })
  applySettings(data.settings)
  runtime.value = data.runtime
}

watch(
  () => ({ ...settings }),
  () => {
    if (booting.value) return
    clearTimeout(persistTimer.value)
    persistTimer.value = setTimeout(() => {
      persistSettingsNow().catch((error) => {
        appendLog(`保存设置失败：${error.message}`)
      })
    }, 250)
  },
  { deep: true },
)

watch(
  () => settings.device_model,
  () => syncDeviceDimensions(),
)

async function pickDirectory(fieldName) {
  const selected = await open({ directory: true, multiple: false })
  if (typeof selected === 'string') settings[fieldName] = selected
}

async function importImages() {
  if (!settings.background_group) {
    appendLog('请先选择一个背景分组。')
    return
  }
  const selected = await open({
    multiple: true,
    filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp', 'bmp'] }],
  })
  if (!selected || !Array.isArray(selected) || selected.length === 0) return
  try {
    const library = await invoke('import_background_images', {
      payload: { groupName: settings.background_group, paths: selected },
    })
    setLibrary(library)
    appendLog(`已导入 ${selected.length} 张背景图到分组 ${settings.background_group}。`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function previewRustScan() {
  if (!settings.local_path.trim()) {
    appendLog('请先选择本地 Markdown 目录。')
    return
  }
  try {
    const summary = await invoke('scan_local_markdown', { payload: { notesDir: settings.local_path } })
    rustScanSummary.value = summary
    appendLog(`Rust 预扫描完成：发现 ${summary.markdownFileCount} 个 Markdown 文件，识别 ${summary.itemCount} 个条目。`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function runGenerator() {
  runState.value = 'running'
  outputLog.value = ''
  try {
    const data = await invoke('run_generation_pipeline', { settings: { ...settings } })
    runtime.value = data.runtime
    setLibrary(data.backgroundLibrary)
    const summary = data.summary
    appendLog(`来源：${summary.source_description}`)
    appendLog(`扫描 Markdown 文件：${summary.markdown_file_count}`)
    appendLog(`识别条目：${summary.item_count}`)
    appendLog(`输出图片：${summary.image_count}`)
    appendLog(`新增 ${summary.created_count}，更新 ${summary.updated_count}，未变 ${summary.unchanged_count}，删除 ${summary.deleted_count}`)
    appendLog(`元数据目录：${summary.data_dir}`)
    appendLog(`云盘目录：${summary.cloud_dir}`)
    appendLog(`索引文件：${summary.index_path}`)
    runState.value = 'success'
  } catch (error) {
    appendLog(error.message)
    runState.value = 'error'
  }
}

async function clearGenerated() {
  if (!window.confirm('这会清空生成图片与元数据，是否继续？')) return
  try {
    const summary = await invoke('clear_generated_outputs_in_rust', { settings: { ...settings } })
    appendLog(`已清空：元数据 ${summary.removedMetadataCount} 项，图片 ${summary.removedCloudCount} 张，索引 ${summary.removedIndexCount} 个。`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function clearLibrary() {
  if (!window.confirm('这会清空背景图库中的用户图片，是否继续？')) return
  try {
    const library = await invoke('clear_background_library')
    setLibrary(library)
    appendLog('背景图库已清空。')
  } catch (error) {
    appendLog(error.message)
  }
}

async function addGroup() {
  const name = window.prompt('请输入新分组名称：')?.trim()
  if (!name) return
  try {
    const library = await invoke('create_background_group', { payload: { name } })
    setLibrary(library)
    settings.background_group = name.replace(/[\\/]/g, '_')
    appendLog(`已创建分组：${settings.background_group}`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function deleteGroup() {
  if (!settings.background_group) return
  if (!window.confirm(`确定删除分组 ${settings.background_group} 吗？`)) return
  try {
    const target = settings.background_group
    const library = await invoke('delete_background_group', { payload: { groupName: target } })
    setLibrary(library)
    appendLog(`已删除分组：${target}`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function deleteImage() {
  if (!settings.background_image_id) return
  if (!window.confirm(`确定删除背景图 ${settings.background_image_id} 吗？`)) return
  try {
    const target = settings.background_image_id
    const library = await invoke('delete_background_image', { payload: { imageId: target } })
    setLibrary(library)
    appendLog(`已删除背景图：${target}`)
  } catch (error) {
    appendLog(error.message)
  }
}

onMounted(() => {
  bootstrap().catch((error) => {
    outputLog.value = error.message
    booting.value = false
  })
})
</script>

<template>
  <div class="shell">
    <div class="hero">
      <div>
        <p class="eyebrow">DailyTipsApp Desktop</p>
        <h1>公式壁纸生成器</h1>
        <p class="hero-copy">仅保留本地 Markdown 工作流：扫描笔记、生成图片、同步到云盘目录。</p>
      </div>
      <div class="status-card">
        <p class="status-title">运行状态</p>
        <p>{{ runtime?.pythonSummary ?? '正在检测 Python...' }}</p>
        <p>{{ runtime?.tectonicSummary ?? '正在检测 Tectonic...' }}</p>
        <p>{{ rendererStatus }}</p>
      </div>
    </div>

    <div class="grid">
      <section class="panel stack-lg">
        <div class="section-head">
          <div>
            <h2>生成配置</h2>
            <p class="section-copy">当前桌面端默认使用 Rust 编排本地扫描，再交给 Python 渲染图片。</p>
          </div>
          <span :class="['pill', runState]">{{ runState }}</span>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>iPhone 型号</span>
            <select v-model="settings.device_model">
              <option v-for="device in devices" :key="device.key" :value="device.key">{{ device.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>公式引擎</span>
            <select v-model="settings.formula_renderer">
              <option v-for="renderer in formulaRenderers" :key="renderer.key" :value="renderer.key">{{ renderer.label }}</option>
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
              <option v-for="group in backgroundLibrary.groups" :key="group" :value="group">{{ group }}</option>
            </select>
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>指定背景图</span>
            <select v-model="settings.background_image_id">
              <option value="">未选择</option>
              <option v-for="image in backgroundLibrary.images" :key="image.id" :value="image.id">{{ image.id }}</option>
            </select>
          </label>
          <label class="field">
            <span>正文字体</span>
            <select v-model="settings.text_font_family">
              <option v-for="font in textFonts" :key="font.key" :value="font.key">{{ font.label }}</option>
            </select>
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>公式字体</span>
            <select v-model="settings.math_font_family">
              <option v-for="font in mathFonts" :key="font.key" :value="font.key">{{ font.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>正文颜色</span>
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
          <input v-model="settings.panel_opacity" max="255" min="0" type="range" />
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
          <p v-if="rustScanSummary.items?.length">来源：{{ rustScanSummary.items[0].sourcePath }}:{{ rustScanSummary.items[0].sourceLine }}</p>
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
            <p class="section-copy">支持分组管理、导入背景图，以及按规则参与渲染。</p>
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
                :class="['list-item', { active: group === settings.background_group }]"
                type="button"
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
                v-for="image in selectedGroupImages"
                :key="image.id"
                :class="['list-item', { active: image.id === settings.background_image_id }]"
                type="button"
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
  align-items: center;
}

.section-head h2,
.library-head h3,
.preview-card h3 {
  margin: 0;
}

.section-copy,
.hero-copy,
.status-card p,
.preview-card p {
  margin: 8px 0 0;
}

.pill {
  padding: 8px 14px;
  border-radius: 999px;
  background: #e7f1ff;
  color: #3467c9;
  font-weight: 700;
  text-transform: capitalize;
}

.pill.running {
  background: #fff1cb;
  color: #a66a00;
}

.pill.success {
  background: #e0f6ea;
  color: #1f7a46;
}

.pill.error {
  background: #ffe2e2;
  color: #bc2f2f;
}

.two-up {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-weight: 600;
  color: #32506f;
}

.field span {
  font-size: 14px;
}

.field input,
.field select,
.field textarea,
button {
  font: inherit;
}

.field input,
.field select,
.field textarea {
  width: 100%;
  border: 1px solid #b8d5e4;
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.96);
  color: #183754;
  outline: none;
}

.field textarea {
  resize: vertical;
  min-height: 220px;
}

.input-action {
  align-items: center;
}

.input-action input {
  flex: 1;
}

.inline-toggle {
  justify-content: flex-end;
}

.inline-toggle input {
  width: 22px;
  height: 22px;
}

button {
  border: 0;
  border-radius: 16px;
  padding: 12px 18px;
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
}

button:hover {
  transform: translateY(-1px);
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

button.primary {
  background: linear-gradient(135deg, #2f6af5, #3ca2ff);
  color: white;
  box-shadow: 0 12px 24px rgba(49, 110, 246, 0.26);
}

button.ghost {
  background: rgba(232, 244, 255, 0.96);
  color: #235487;
}

button.danger {
  background: #f04d4d;
  color: white;
}

button.small {
  padding: 10px 14px;
  border-radius: 14px;
}

.preview-card {
  border-radius: 22px;
  padding: 18px;
}

.library-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.list-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow: auto;
  padding-right: 4px;
}

.list-item {
  width: 100%;
  text-align: left;
  background: rgba(241, 247, 255, 0.95);
  color: #234260;
}

.list-item.active {
  background: linear-gradient(135deg, #2f6af5, #4cb5ff);
  color: white;
}

@media (max-width: 1100px) {
  .hero,
  .grid,
  .library-grid,
  .two-up {
    grid-template-columns: 1fr;
    display: grid;
  }

  .status-card {
    min-width: 0;
  }
}
</style>