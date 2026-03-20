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

const settings = reactive({
  language: 'zh',
  source_mode: 'local',
  local_path: '',
  github_url: 'https://github.com/PalaiologosLei/DailyTips',
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

const selectedGroupImages = computed(() => {
  if (!settings.background_group) {
    return backgroundLibrary.value.images
  }
  return backgroundLibrary.value.images.filter((image) => image.groupName === settings.background_group)
})

const rendererStatus = computed(() => runtime.value?.formulaSupport ?? 'Checking formula engine...')
const isRunning = computed(() => runState.value === 'running')
const sourceHint = computed(() => settings.source_mode === 'local'
  ? 'Use a local markdown folder for extraction.'
  : 'Use a public GitHub notes repository URL.')

async function invokeApi(command, payload = {}) {
  const response = await invoke('run_python_api', { request: { command, payload } })
  if (!response.success) {
    throw new Error(response.stderr?.trim() || response.stdout?.trim() || `Python API failed with exit code ${response.exitCode}`)
  }
  return response.data ?? null
}

function applySettings(nextSettings = {}) {
  Object.assign(settings, nextSettings)
}

function syncDeviceDimensions() {
  const profile = devices.value.find((item) => item.key === settings.device_model)
  if (profile && profile.key !== 'custom') {
    settings.width = String(profile.width)
    settings.height = String(profile.height)
  }
}

function appendLog(message) {
  outputLog.value = `${outputLog.value}${outputLog.value ? '\\n' : ''}${message}`
}

function setLibrary(library) {
  backgroundLibrary.value = library ?? { groups: [], images: [] }
  const groups = backgroundLibrary.value.groups ?? []
  const images = backgroundLibrary.value.images ?? []
  if (groups.length && !groups.includes(settings.background_group)) {
    settings.background_group = groups[0]
  }
  if (!groups.length) {
    settings.background_group = ''
  }
  const imageIds = images.map((item) => item.id)
  if (imageIds.length && !imageIds.includes(settings.background_image_id)) {
    settings.background_image_id = imageIds[0]
  }
  if (!imageIds.length) {
    settings.background_image_id = ''
  }
}

async function bootstrap() {
  booting.value = true
  try {
    const data = await invokeApi('bootstrap')
    applySettings(data.settings)
    devices.value = data.devices
    textFonts.value = data.textFonts
    mathFonts.value = data.mathFonts
    formulaRenderers.value = data.formulaRenderers
    runtime.value = data.runtime
    setLibrary(data.backgroundLibrary)
    syncDeviceDimensions()
    outputLog.value = 'Desktop shell connected. Settings loaded from .gui_settings.json.'
  } finally {
    booting.value = false
  }
}

async function persistSettingsNow() {
  const data = await invokeApi('save-settings', { settings: { ...settings } })
  runtime.value = data.runtime
}

watch(
  () => ({ ...settings }),
  () => {
    if (booting.value) return
    clearTimeout(persistTimer.value)
    persistTimer.value = setTimeout(() => {
      persistSettingsNow().catch((error) => {
        appendLog(`Settings save failed: ${error.message}`)
      })
    }, 250)
  },
  { deep: true },
)

watch(
  () => settings.device_model,
  () => {
    syncDeviceDimensions()
  },
)


async function pickDirectory(fieldName) {
  const selected = await open({ directory: true, multiple: false })
  if (typeof selected === 'string') {
    settings[fieldName] = selected
  }
}

async function importImages() {
  if (!settings.background_group) {
    appendLog('Pick or create a background group first.')
    return
  }
  const selected = await open({
    multiple: true,
    filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp', 'bmp'] }],
  })
  if (!selected || !Array.isArray(selected) || selected.length === 0) return
  try {
    const data = await invokeApi('import-images', { groupName: settings.background_group, paths: selected })
    setLibrary(data.backgroundLibrary)
    appendLog(`Imported ${selected.length} image(s) into ${settings.background_group}.`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function runGenerator() {
  runState.value = 'running'
  outputLog.value = ''
  try {
    const data = await invokeApi('run', { settings: { ...settings } })
    runtime.value = data.runtime
    setLibrary(data.backgroundLibrary)
    const summary = data.summary
    appendLog(`Source: ${summary.source_description}`)
    appendLog(`Markdown files: ${summary.markdown_file_count}`)
    appendLog(`Items: ${summary.item_count}`)
    appendLog(`Images: ${summary.image_count}`)
    appendLog(`Created ${summary.created_count}, updated ${summary.updated_count}, unchanged ${summary.unchanged_count}, deleted ${summary.deleted_count}`)
    appendLog(`App data dir: ${summary.data_dir}`)
    appendLog(`Cloud dir: ${summary.cloud_dir}`)
    appendLog(`Image index: ${summary.index_path}`)
    runState.value = 'success'
  } catch (error) {
    appendLog(error.message)
    runState.value = 'error'
  }
}

async function clearGenerated() {
  if (!window.confirm('Clear generated images, cache metadata, and cloud index files?')) return
  try {
    const data = await invokeApi('clear-generated', { settings: { ...settings } })
    setLibrary(data.backgroundLibrary)
    appendLog(`Cleared generated outputs: metadata ${data.summary.removed_metadata_count}, cloud images ${data.summary.removed_cloud_count}, indexes ${data.summary.removed_index_count}.`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function clearLibrary() {
  if (!window.confirm('Clear user background images from the library?')) return
  try {
    const data = await invokeApi('clear-library')
    setLibrary(data.backgroundLibrary)
    appendLog(`Cleared background library: ${data.summary.removed_background_count} images removed.`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function addGroup() {
  const name = window.prompt('New background group name')?.trim()
  if (!name) return
  try {
    const data = await invokeApi('add-group', { name })
    setLibrary(data.backgroundLibrary)
    settings.background_group = name
    appendLog(`Added group: ${name}`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function deleteGroup() {
  if (!settings.background_group) return
  if (!window.confirm(`Delete group '${settings.background_group}' and all its images?`)) return
  try {
    const groupName = settings.background_group
    const data = await invokeApi('delete-group', { groupName })
    setLibrary(data.backgroundLibrary)
    appendLog(`Deleted group: ${groupName}`)
  } catch (error) {
    appendLog(error.message)
  }
}

async function deleteImage() {
  if (!settings.background_image_id) return
  if (!window.confirm(`Delete image '${settings.background_image_id}'?`)) return
  try {
    const imageId = settings.background_image_id
    const data = await invokeApi('delete-image', { imageId })
    setLibrary(data.backgroundLibrary)
    appendLog(`Deleted image: ${imageId}`)
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
        <h1>Modern desktop shell for your wallpaper workflow</h1>
        <p class="hero-copy">
          The new Vue + Tauri shell is now talking to the existing Python core. You can already load settings,
          run generation jobs, clear outputs, and manage background groups while we continue migrating the rest.
        </p>
      </div>
      <div class="status-card">
        <p class="status-title">Runtime</p>
        <p>{{ runtime?.pythonSummary ?? 'Checking Python...' }}</p>
        <p>{{ runtime?.tectonicSummary ?? 'Checking Tectonic...' }}</p>
        <p>{{ rendererStatus }}</p>
      </div>
    </div>

    <div class="grid">
      <section class="panel stack-lg">
        <div class="section-head">
          <div>
            <h2>Generator</h2>
            <p class="section-copy">Core run controls, persisted settings, and formula rendering options.</p>
          </div>
          <span :class="['pill', runState]">{{ runState }}</span>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>Language</span>
            <select v-model="settings.language">
              <option value="zh">??</option>
              <option value="en">English</option>
            </select>
          </label>
          <label class="field">
            <span>iPhone model</span>
            <select v-model="settings.device_model">
              <option v-for="device in devices" :key="device.key" :value="device.key">{{ device.label }}</option>
            </select>
          </label>
        </div>

        <label class="field">
          <span>Source mode</span>
          <select v-model="settings.source_mode">
            <option value="local">Local folder</option>
            <option value="github">GitHub public repo</option>
          </select>
        </label>

        <p class="field-hint">{{ sourceHint }}</p>

        <label v-if="settings.source_mode === 'local'" class="field">
          <span>Notes directory</span>
          <div class="input-action">
            <input v-model="settings.local_path" placeholder="D:/path/to/your/notes" />
            <button class="ghost small" type="button" @click="pickDirectory('local_path')">Browse</button>
          </div>
        </label>

        <label v-else class="field">
          <span>GitHub URL</span>
          <input v-model="settings.github_url" placeholder="https://github.com/owner/repo" />
        </label>

        <div class="two-up compact">
          <label class="field">
            <span>Cloud image directory</span>
            <div class="input-action">
              <input v-model="settings.cloud_dir" placeholder="C:/Users/yourname/iCloudDrive/DailyTips" />
              <button class="ghost small" type="button" @click="pickDirectory('cloud_dir')">Browse</button>
            </div>
          </label>
          <label class="field">
            <span>App data directory</span>
            <input v-model="settings.output_dir" placeholder=".dailytipsapp" />
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>Width</span>
            <input v-model="settings.width" :disabled="settings.device_model !== 'custom'" />
          </label>
          <label class="field">
            <span>Height</span>
            <input v-model="settings.height" :disabled="settings.device_model !== 'custom'" />
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>Formula engine</span>
            <select v-model="settings.formula_renderer">
              <option v-for="renderer in formulaRenderers" :key="renderer.key" :value="renderer.key">{{ renderer.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>Background mode</span>
            <select v-model="settings.background_mode">
              <option value="white">White background</option>
              <option value="specific">Specific image</option>
              <option value="random_group">Random from group</option>
              <option value="random_all">Random from all</option>
            </select>
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>Specific background</span>
            <select v-model="settings.background_image_id">
              <option value="">None</option>
              <option v-for="image in backgroundLibrary.images" :key="image.id" :value="image.id">{{ image.id }}</option>
            </select>
          </label>
          <label class="field">
            <span>Background group</span>
            <select v-model="settings.background_group">
              <option value="">None</option>
              <option v-for="group in backgroundLibrary.groups" :key="group" :value="group">{{ group }}</option>
            </select>
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>Text font</span>
            <select v-model="settings.text_font_family">
              <option v-for="font in textFonts" :key="font.key" :value="font.key">{{ font.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>Formula font</span>
            <select v-model="settings.math_font_family">
              <option v-for="font in mathFonts" :key="font.key" :value="font.key">{{ font.label }}</option>
            </select>
          </label>
        </div>

        <div class="two-up compact">
          <label class="field">
            <span>Text color</span>
            <input v-model="settings.text_color" type="color" />
          </label>
          <label class="field">
            <span>Formula color</span>
            <input v-model="settings.math_color" type="color" />
          </label>
        </div>

        <label class="field inline-toggle">
          <span>Translucent card</span>
          <input v-model="settings.show_content_panel" type="checkbox" />
        </label>

        <label class="field">
          <span>Card opacity: {{ settings.panel_opacity }}</span>
          <input v-model="settings.panel_opacity" type="range" min="0" max="255" />
        </label>

        <div class="button-row">
          <button class="primary" :disabled="isRunning || booting" @click="runGenerator">
            {{ isRunning ? 'Running?' : 'Run wallpaper generator' }}
          </button>
          <button class="ghost" :disabled="booting" @click="clearGenerated">Clear generated</button>
          <button class="danger" :disabled="booting" @click="clearLibrary">Clear library</button>
        </div>
      </section>

      <section class="panel stack-lg">
        <div class="section-head">
          <div>
            <h2>Background Library</h2>
            <p class="section-copy">Group and image metadata already lives here. Native file picking is the next migration step.</p>
          </div>
        </div>

        <div class="two-up panels-tight">
          <div class="subpanel">
            <div class="subpanel-head">
              <strong>Groups</strong>
              <div class="mini-actions">
                <button class="ghost small" @click="addGroup">Add</button>
                <button class="danger small" @click="deleteGroup">Delete</button>
              </div>
            </div>
            <div class="listbox">
              <button
                v-for="group in backgroundLibrary.groups"
                :key="group"
                class="list-item"
                :class="{ active: settings.background_group === group }"
                @click="settings.background_group = group"
              >
                {{ group }}
              </button>
            </div>
          </div>

          <div class="subpanel">
            <div class="subpanel-head">
              <strong>Images</strong>
              <div class="mini-actions">
                <button class="ghost small" @click="importImages">Import</button>
                <button class="danger small" @click="deleteImage">Delete</button>
              </div>
            </div>
            <div class="listbox">
              <button
                v-for="image in selectedGroupImages"
                :key="image.id"
                class="list-item"
                :class="{ active: settings.background_image_id === image.id }"
                @click="settings.background_image_id = image.id"
              >
                {{ image.id }}
              </button>
            </div>
          </div>
        </div>

        <div class="runtime-card">
          <p class="status-title">Current runtime snapshot</p>
          <p><strong>Repo:</strong> {{ runtime?.repoRoot ?? '-' }}</p>
          <p><strong>Python:</strong> {{ runtime?.pythonSummary ?? '-' }}</p>
          <p><strong>Tectonic:</strong> {{ runtime?.tectonicSummary ?? '-' }}</p>
          <p><strong>Formula backend:</strong> {{ runtime?.formulaBackendEffective ?? '-' }}</p>
        </div>

        <div class="log-box">{{ outputLog || 'Run output will appear here.' }}</div>
      </section>
    </div>
  </div>
</template>
