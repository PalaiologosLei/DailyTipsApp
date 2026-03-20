<script setup>
        import { computed, ref, watch } from 'vue'
        import { invoke } from '@tauri-apps/api/core'
        import { deviceProfiles, getDeviceProfile } from './deviceProfiles'

        const sourceMode = ref('local')
        const notesDir = ref('')
        const githubUrl = ref('https://github.com/PalaiologosLei/DailyTips')
        const cloudDir = ref('C:/Users/lky14/iCloudDrive/DailyTips')
        const outputDir = ref('.dailytipsapp')
        const deviceModel = ref('iphone_17_pro')
        const width = ref('1206')
        const height = ref('2622')
        const formulaRenderer = ref('auto')
        const runState = ref('idle')
        const runtimeStatus = ref(null)
        const outputLog = ref('')

        const rendererOptions = [
          { value: 'auto', label: 'Auto (Recommended)' },
          { value: 'tectonic', label: 'Tectonic LaTeX' },
          { value: 'matplotlib', label: 'Matplotlib MathText' },
        ]

        const sourceHint = computed(() => {
          return sourceMode.value === 'local'
            ? 'Use a local markdown notes folder.'
            : 'Use a public GitHub notes repository URL.'
        })

        const isCustomSize = computed(() => deviceModel.value === 'custom')

        watch(deviceModel, (value) => {
          const profile = getDeviceProfile(value)
          if (profile.key !== 'custom') {
            width.value = String(profile.width)
            height.value = String(profile.height)
          }
        }, { immediate: true })

        async function refreshRuntimeStatus() {
          try {
            runtimeStatus.value = await invoke('get_runtime_status')
          } catch (error) {
            runtimeStatus.value = {
              repoRoot: '',
              pythonSummary: String(error),
              tectonicSummary: 'Unavailable',
              pythonOk: false,
              tectonicBundled: false,
            }
          }
        }

        function formatRunOutput(response) {
          const chunks = []
          chunks.push(`Exit code: ${response.exitCode}`)
          if (response.stdout?.trim()) {
            chunks.push('STDOUT:')
            chunks.push(response.stdout.trim())
          }
          if (response.stderr?.trim()) {
            chunks.push('STDERR:')
            chunks.push(response.stderr.trim())
          }
          return chunks.join('\n\n')
        }

        async function runGenerator() {
          outputLog.value = ''
          runState.value = 'running'
          try {
            const payload = {
              sourceMode: sourceMode.value,
              notesDir: notesDir.value,
              githubUrl: githubUrl.value,
              cloudDir: cloudDir.value,
              outputDir: outputDir.value,
              width: Number.parseInt(width.value, 10),
              height: Number.parseInt(height.value, 10),
              formulaRenderer: formulaRenderer.value,
            }
            const result = await invoke('run_python_job', { payload })
            outputLog.value = formatRunOutput(result)
            runState.value = result.success ? 'success' : 'error'
            await refreshRuntimeStatus()
          } catch (error) {
            outputLog.value = String(error)
            runState.value = 'error'
          }
        }

        refreshRuntimeStatus()
        </script>

        <template>
          <div class="shell">
            <div class="hero">
              <div>
                <p class="eyebrow">DailyTipsApp Desktop</p>
                <h1>Vue + Tauri migration started</h1>
                <p class="hero-copy">
                  This new shell keeps your Python core intact while moving the UI toward a cleaner desktop app workflow.
                </p>
              </div>
              <div class="status-card">
                <p class="status-title">Runtime</p>
                <p>{{ runtimeStatus?.pythonSummary ?? 'Checking Python...' }}</p>
                <p>{{ runtimeStatus?.tectonicSummary ?? 'Checking Tectonic...' }}</p>
              </div>
            </div>

            <div class="grid">
              <section class="panel form-panel">
                <div class="section-head">
                  <h2>Generate Wallpapers</h2>
                  <span :class="['pill', runState]">{{ runState }}</span>
                </div>

                <label class="field">
                  <span>Source mode</span>
                  <select v-model="sourceMode">
                    <option value="local">Local folder</option>
                    <option value="github">GitHub public repo</option>
                  </select>
                </label>

                <p class="field-hint">{{ sourceHint }}</p>

                <label v-if="sourceMode === 'local'" class="field">
                  <span>Notes directory</span>
                  <input v-model="notesDir" placeholder="D:/path/to/your/notes" />
                </label>

                <label v-else class="field">
                  <span>GitHub URL</span>
                  <input v-model="githubUrl" placeholder="https://github.com/owner/repo" />
                </label>

                <label class="field">
                  <span>Cloud image directory</span>
                  <input v-model="cloudDir" placeholder="C:/Users/yourname/iCloudDrive/DailyTips" />
                </label>

                <label class="field">
                  <span>App data directory</span>
                  <input v-model="outputDir" placeholder=".dailytipsapp" />
                </label>

                <div class="field two-up">
                  <label>
                    <span>Device</span>
                    <select v-model="deviceModel">
                      <option v-for="profile in deviceProfiles" :key="profile.key" :value="profile.key">
                        {{ profile.label }}
                      </option>
                    </select>
                  </label>
                  <label>
                    <span>Formula engine</span>
                    <select v-model="formulaRenderer">
                      <option v-for="option in rendererOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </option>
                    </select>
                  </label>
                </div>

                <div class="field two-up">
                  <label>
                    <span>Width</span>
                    <input v-model="width" :disabled="!isCustomSize" />
                  </label>
                  <label>
                    <span>Height</span>
                    <input v-model="height" :disabled="!isCustomSize" />
                  </label>
                </div>

                <button class="primary" :disabled="runState === 'running'" @click="runGenerator">
                  {{ runState === 'running' ? 'Running...' : 'Run Python generator' }}
                </button>
              </section>

              <section class="panel info-panel">
                <div class="section-head">
                  <h2>Status & Output</h2>
                  <button class="ghost" @click="refreshRuntimeStatus">Refresh runtime</button>
                </div>

                <div class="info-list">
                  <div>
                    <span class="info-label">Repo root</span>
                    <p>{{ runtimeStatus?.repoRoot ?? '-' }}</p>
                  </div>
                  <div>
                    <span class="info-label">Python</span>
                    <p>{{ runtimeStatus?.pythonSummary ?? '-' }}</p>
                  </div>
                  <div>
                    <span class="info-label">Tectonic</span>
                    <p>{{ runtimeStatus?.tectonicSummary ?? '-' }}</p>
                  </div>
                </div>

                <div class="log-box">{{ outputLog || 'Run output will appear here.' }}</div>
              </section>
            </div>
          </div>
        </template>
