<template>
  <Teleport to="body">
    <div class="settings-backdrop" @click.self="close" @keydown.esc.stop="close">
      <section ref="dialog" class="application-settings" role="dialog" aria-modal="true" aria-labelledby="application-settings-title" tabindex="-1" @keydown.tab="trapFocus">
        <header><div><h2 id="application-settings-title">应用设置</h2><p>连接、模型与个人偏好 · 保存后用于后续请求</p></div><button aria-label="关闭设置" @click="close">✕</button></header>
        <div class="settings-layout">
          <nav aria-label="设置分类"><button v-for="item in tabs" :key="item[0]" :class="{selected:tab===item[0]}" @click="tab=item[0]">{{item[1]}}</button></nav>
          <div class="settings-body">
            <p v-if="error" class="settings-error" role="alert">{{error}}</p><p v-if="notice" class="settings-notice" role="status">{{notice}}</p>
            <div v-if="!draft"><p>正在载入设置…</p><button @click="load">重新载入</button></div>
            <fieldset v-else :disabled="busy || disabled">
              <template v-if="tab==='connections'">
                <h3>连接与 API</h3><p>百炼原生聊天、生图和视频使用中国站接口；其他兼容连接目前用于聊天与嵌入。密钥不会出现在导出文件中。</p>
                <article v-for="connection in draft.connections" :key="connection.id" class="connection-card">
                  <label>连接名称<input v-model="connection.name" maxlength="80" /></label>
                  <label>服务类型<select v-model="connection.provider" @change="providerChanged(connection)"><option value="dashscope">阿里云百炼</option><option value="ollama">Ollama 本地</option><option value="compatible">兼容聊天 / 嵌入 API</option></select></label>
                  <label>服务地址<input v-model="connection.base_url" :readonly="connection.provider==='dashscope'" placeholder="http://127.0.0.1:11434" /></label>
                  <label v-if="connection.provider!=='ollama'">API Key<input v-model="connection.api_key" :type="showKey[connection.id]?'text':'password'" autocomplete="new-password" :placeholder="connection.has_key?'已配置；留空保持原值':'尚未配置'" /></label>
                  <div class="button-row"><button v-if="connection.provider!=='ollama'" @click="showKey[connection.id]=!showKey[connection.id]">{{showKey[connection.id]?'隐藏':'显示'}}新填写的密钥</button><button v-if="connection.has_key" @click="connection.clear_key=!connection.clear_key">{{connection.clear_key?'取消清除':'清除已保存密钥'}}</button><button @click="test(connection)">保存并测试连接</button><button @click="removeConnection(connection)">删除连接</button></div>
                  <label v-if="connection.id==='bailian'"><input type="checkbox" v-model="connection.use_environment_key" />允许使用系统环境变量密钥</label><p v-if="connection.id==='bailian'">留空保持原密钥。清除密钥会同时停用环境变量回退，但不修改系统环境变量。</p>
                  <p v-if="application.models[connection.id]">已读取 {{application.models[connection.id].length}} 个模型。连接成功不代表所有模型都支持每种功能。</p>
                </article>
                <button @click="addConnection">＋ 添加连接</button><p>密钥存储：{{draft.credential_storage}}。本地失败不会自动切换到云端。</p>
              </template>
              <template v-if="tab==='models'">
                <h3>按功能选择模型</h3><p>云端会接收分配给该功能的消息、资料或图片。请分别检查文档回答与嵌入连接；两者都选择本机，文档处理才全程留在本地。</p>
                <article v-for="module in modules" :key="module[0]" class="module-card">
                  <h4>{{module[1]}}</h4><p>{{module[2]}}</p>
                  <label>连接<select v-model="draft.modules[module[0]].connection"><option v-for="connection in eligible(module[0])" :key="connection.id" :value="connection.id">{{connection.name}}</option></select></label>
                  <label>模型<input v-model="draft.modules[module[0]].model" :list="'settings-models-'+module[0]" placeholder="选择或填写模型 ID" /><datalist :id="'settings-models-'+module[0]"><option v-for="model in application.models[draft.modules[module[0]].connection] || []" :key="model.id" :value="model.id" /></datalist></label>
                  <div class="button-row"><button @click="listModels(module[0])">刷新可选模型</button><button @click="checkCapabilities(module[0])">检查模型能力</button></div>
                </article>
                <p>更换嵌入连接或模型后会清空内存索引，下次文档问答自动重建；原文文件不删除。Agent 目前仍为百炼工具，Codex 与本地执行尚未接入。联网搜索仅在百炼聊天可用，搜图使用对应的百炼工具。</p>
              </template>
              <template v-if="tab==='identity'">
                <h3>角色与头像</h3><label>你的昵称<input v-model="draft.appearance.user_name" maxlength="100" /></label><label>助手显示名称<input v-model="draft.appearance.assistant_name" maxlength="100" /></label>
                <label>头像形状<select v-model="draft.appearance.avatar_shape"><option value="circle">圆形</option><option value="rounded">圆角方形</option></select></label>
                <AvatarPicker v-model="draft.appearance.user_avatar" fallback="/avatars/dania.png" label="你的头像" @busy-change="busy=$event" :shape="draft.appearance.avatar_shape" />
                <AvatarPicker v-model="draft.appearance.assistant_avatar" fallback="/avatars/Castorice.gif" label="助手头像" @busy-change="busy=$event" :shape="draft.appearance.avatar_shape" />
                <p>支持 PNG、JPG/JPEG、WebP、GIF，最多 10 MB。静态头像可裁剪，动画保留原文件。保存设置后生效。</p>
                <label>角色设定<textarea v-model="draft.appearance.system_prompt" rows="6" maxlength="8000" placeholder="留空使用默认遐蝶角色设定" /></label><p>用于聊天与文档回答；显示名称本身不会改变模型角色。</p><button @click="draft.appearance.system_prompt=''">恢复默认角色设定</button>
              </template>
              <template v-if="tab==='appearance'">
                <h3>背景与外观</h3><label>背景模式<select v-model="draft.appearance.background_mode"><option value="default">默认视频</option><option value="video">自定义视频</option><option value="image">自定义图片</option><option value="color">纯色</option><option value="gradient">渐变</option></select></label>
                <label v-if="['video','image'].includes(draft.appearance.background_mode)">选择背景文件<input type="file" :accept="draft.appearance.background_mode==='video'?'.mp4,.webm':'.png,.jpg,.jpeg,.webp,.gif'" @change="uploadBackground" /></label>
                <p v-if="draft.appearance.background_asset">已保存背景文件：{{draft.appearance.background_asset.split('/').pop()}} <button @click="draft.appearance.background_asset='';draft.appearance.background_mode='default'">恢复默认背景</button></p>
                <label>背景颜色<input type="color" v-model="draft.appearance.background_color" /></label><label>画面适配<select v-model="draft.appearance.background_fit"><option value="cover">填满并裁剪</option><option value="contain">完整显示</option></select></label>
                <label>遮罩亮度 {{Math.round(draft.appearance.background_dim*100)}}%<input type="range" min="0" max=".85" step=".01" v-model.number="draft.appearance.background_dim" /></label><label>背景模糊 {{draft.appearance.background_blur}}px<input type="range" min="0" max="20" v-model.number="draft.appearance.background_blur" /></label>
                <label><input type="checkbox" v-model="draft.appearance.pause_hidden" />窗口隐藏时暂停视频</label><label><input type="checkbox" v-model="draft.appearance.reduce_motion" />减少动画并暂停视频</label>
                <label>聊天字号 {{draft.appearance.font_size}}px<input type="range" min="12" max="24" v-model.number="draft.appearance.font_size" /></label>
                <label><input type="checkbox" v-model="draft.appearance.music_enabled" />允许背景音乐</label><label>音乐音量 {{Math.round(draft.appearance.music_volume*100)}}%<input type="range" min="0" max="1" step=".01" v-model.number="draft.appearance.music_volume" /></label>
                <label>发送快捷键<select v-model="draft.appearance.send_key"><option value="enter">Enter 发送，Shift+Enter 换行</option><option value="ctrl-enter">Ctrl/⌘+Enter 发送，Enter 换行</option></select></label>
                <p>视频静音循环播放；MP4、WebM 最大 200 MB，实际编码不兼容时会显示错误。背景保存在应用数据目录。标题大小与位置不随聊天字号改变。</p><slot name="general" />
              </template>
              <template v-if="tab==='parameters'"><h3>功能默认参数</h3><p>以下参数沿用原有自动保存机制，修改即保存；连接、模型与头像使用底部“保存设置”。生成中参数不可修改。</p><slot name="parameters" /></template>
              <template v-if="tab==='data'">
                <h3>数据与隐私</h3><p>所有连接都由你指定；本地失败不会自动转云端。配置云端模型后，对应功能的数据会发送至该连接。</p><button @click="diagnose">刷新运行状态</button><pre v-if="diagnostics">{{diagnostics}}</pre>
                <h4>备份与恢复</h4><p>导出不包含 API Key、原始上传文件及自定义媒体文件。恢复媒体仍需保留原数据目录。历史记录存储于当前应用浏览器数据中。</p>
                <div class="button-row"><button @click="exportData">导出设置与聊天记录</button><label>导入备份<input type="file" accept="application/json,.json" @change="importData" /></label><button @click="clearIndex">清空内存检索索引</button></div>
                <p>清空聊天记录会刷新页面，请先停止生成并导出备份。</p><button :disabled="disabled" @click="clearHistory">清空聊天记录</button>
              </template>
              <template v-if="tab==='about'"><h3>关于与诊断</h3><p>本次设置升级处于开发验证阶段，尚未生成新安装包。</p><p>已有能力：百炼聊天与工具、图片与视频接口、Ollama 聊天与嵌入、兼容聊天与嵌入接口。</p><p>暂未开放：Codex 执行、本地 Agent 工具执行、其他服务商生图视频、自动更新、托盘。不会用无效开关代替这些能力。</p><button @click="diagnose">检查后台</button><div v-if="desktop" class="button-row"><button @click="desktop.openData()">打开数据目录</button><button @click="desktop.openLogs()">查看后台日志</button><button @click="desktop.resetWindow()">恢复默认窗口大小</button><button @click="restartDesktop">重启桌面应用</button></div><p v-else>浏览器开发版不提供本机目录与窗口操作。桌面开发版已接入对应入口，窗口位置与大小自动记忆。</p><pre v-if="diagnostics">{{diagnostics}}</pre></template>
            </fieldset>
          </div>
        </div>
        <footer><span v-if="disabled">有任务正在进行，停止或完成后可修改设置。</span><span v-else>密钥仅用于服务认证，不进入对话内容或导出文件。</span><button :disabled="busy" @click="load">重新载入</button><button :disabled="busy || disabled || !draft" @click="save">{{busy?'处理中…':'保存设置'}}</button></footer>
      </section>
    </div>
  </Teleport>
</template>
<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import AvatarPicker from './AvatarPicker.vue'
import { application, defaultAppearance, loadApplicationSettings, refreshModels, saveApplicationSettings, settingsRequest } from '../composables/useApplicationSettings.js'
const props = defineProps({ disabled: Boolean })
const emit = defineEmits(['close'])
const draft = ref(null), dialog = ref(null), busy = ref(false), error = ref(''), notice = ref(''), tab = ref('connections'), showKey = ref({}), diagnostics = ref('')
const tabs = [['connections','连接与 API'],['models','模型与功能'],['identity','角色与头像'],['appearance','背景与外观'],['parameters','功能参数'],['data','数据与隐私'],['about','关于与诊断']]
const modules = [['chat','普通聊天','本地与云端可切换。'],['vision','图片理解','需要视觉模型；OCR 模式跟随普通聊天。'],['document','文档回答','阅读检索片段并回答，不等同于嵌入模型。'],['embedding','文档检索','使用专用嵌入模型；索引与查询始终使用同一配置。'],['agent','Agent','目前仅支持百炼托管工具。'],['search_image','文字搜图','百炼图片搜索工具。'],['image_search','以图搜图','百炼图片检索工具，需要参考图片。'],['image','图片生成','当前仅适配百炼原生图片接口，参数需与模型兼容。'],['video','视频生成','当前仅适配百炼视频接口；不会通过连接测试生成视频。']]
const clone = value => JSON.parse(JSON.stringify(value))
const desktop = window.castoriceDesktop
const previousFocus = document.activeElement
function close() { if (busy.value) return; if (draft.value && JSON.stringify(draft.value) !== JSON.stringify(application.config) && !confirm('放弃尚未保存的连接、头像和外观设置？')) return; emit('close') }
function trapFocus(event) { const elements = [...dialog.value.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled)')].filter(el => el.offsetParent !== null); const first=elements[0],last=elements.at(-1); if (event.shiftKey && (document.activeElement===first || document.activeElement===dialog.value)) { event.preventDefault();last?.focus() } else if (!event.shiftKey && document.activeElement===last) { event.preventDefault();first?.focus() } }
async function load() { error.value=''; await loadApplicationSettings(); if (application.config) draft.value=clone(application.config); else error.value=application.error }
async function save() { if(props.disabled)return; busy.value=true;error.value='';notice.value='';try { draft.value=clone(await saveApplicationSettings(draft.value));notice.value='设置已保存，后续请求使用新配置。' } catch(e){error.value=e.message} finally{busy.value=false} }
function eligible(module) { return draft.value.connections.filter(c => !['agent','search_image','image_search','image','video'].includes(module) || c.provider==='dashscope') }
function providerChanged(c) { c.base_url=c.provider==='ollama'?'http://127.0.0.1:11434':c.provider==='dashscope'?'https://dashscope.aliyuncs.com/compatible-mode/v1':'';c.api_key='';c.clear_key=true }
function addConnection() { draft.value.connections.push({id:crypto.randomUUID(),name:'新连接',provider:'compatible',base_url:'',has_key:false,api_key:''}) }
function removeConnection(c) { if(Object.values(draft.value.modules).some(r=>r.connection===c.id)){error.value='请先将使用此连接的功能分配到其他连接，再删除。';return} draft.value.connections=draft.value.connections.filter(item=>item.id!==c.id) }
async function test(c) { await save(); if(error.value)return; try { const result=await refreshModels(c.id);notice.value=`连接成功，读取 ${result.models.length} 个模型，用时 ${result.latency_ms} ms；未发起生成请求。` }catch(e){error.value=e.message} }
async function listModels(module) { if(!application.config?.connections.some(c=>c.id===draft.value.modules[module].connection)){error.value='请先保存新连接';return} try{await refreshModels(draft.value.modules[module].connection);notice.value='模型列表已刷新；未列出的模型可手动输入 ID。'}catch(e){error.value=e.message} }
async function checkCapabilities(module) { try{const r=draft.value.modules[module];const result=await settingsRequest('/capabilities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(r)});notice.value=`${result.capabilities.join('、') || '未报告能力'}。${result.note}`}catch(e){error.value=e.message} }
async function uploadBackground(event) { const file=event.target.files?.[0];event.target.value='';if(!file)return;if(file.size>200*1048576){error.value='背景文件不能超过 200 MB';return}busy.value=true;try{const form=new FormData();form.append('file',file);const result=await settingsRequest('/asset?kind=background',{method:'POST',body:form});draft.value.appearance.background_asset=result.url;draft.value.appearance.background_mode=result.type;notice.value='媒体已保存，请保存设置以应用背景。'}catch(e){error.value=e.message}finally{busy.value=false} }
async function diagnose(){try{diagnostics.value=JSON.stringify(await settingsRequest('/diagnostics'),null,2)}catch(e){error.value=e.message} }
async function clearIndex(){try{notice.value=(await settingsRequest('/clear-index',{method:'POST'})).message}catch(e){error.value=e.message}}
function restartDesktop(){if(confirm('重启会停止当前任务。确定重启？'))desktop.restart()}
function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function exportData(){try{const storage={};for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(key.startsWith('castorice_'))storage[key]=localStorage.getItem(key)}download({format:'castorice-backup-v1',settings:application.config,storage},'Castorice-backup.json')}catch(e){error.value='备份失败：'+e.message} }
async function importData(event){const file=event.target.files?.[0];event.target.value='';if(!file)return;try{if(file.size>20*1048576)throw new Error('备份不能超过 20 MB');const data=JSON.parse(await file.text());if(data.format!=='castorice-backup-v1'||!data.settings||!data.storage)throw new Error('不是有效的 Castorice 备份');if(!confirm('导入会覆盖同名聊天记录和设置。密钥不会从备份恢复，是否继续？'))return;const incoming=clone(data.settings);incoming.revision=application.config.revision;for(const c of incoming.connections){delete c.api_key;delete c.secret;delete c.clear_key}await saveApplicationSettings(incoming);for(const [key,value]of Object.entries(data.storage)){if(key.startsWith('castorice_')&&typeof value==='string')localStorage.setItem(key,value)}location.reload()}catch(e){error.value='导入失败：'+e.message} }
function clearHistory(){if(!confirm('确定清空当前应用中所有聊天和生成历史？此操作无法撤销。'))return;for(const key of Object.keys(localStorage))if(key.startsWith('castorice_')&&!['castorice_preferences_v1','castorice_font','castorice_lang'].includes(key))localStorage.removeItem(key);location.reload()}
onMounted(async()=>{document.body.style.overflow='hidden';await load();await nextTick();dialog.value?.focus()})
onBeforeUnmount(()=>{document.body.style.overflow='';previousFocus?.focus?.()})
</script>
<style scoped>
.settings-backdrop{position:fixed;inset:0;background:#080512b8;backdrop-filter:blur(10px);z-index:200000;display:flex;align-items:center;justify-content:center;padding:24px}.application-settings{width:min(100%,1060px);height:min(90vh,850px);background:#171224;color:#eee8fb;border:1px solid #67517e;border-radius:22px;box-shadow:0 25px 100px #0008;display:flex;flex-direction:column;overflow:hidden;font:14px/1.6 system-ui,sans-serif}.application-settings header{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;border-bottom:1px solid #473651}.application-settings h2{margin:0;font-size:23px}.application-settings p{color:#baadc9;margin:6px 0 14px}.settings-layout{display:flex;min-height:0;flex:1}.settings-layout nav{width:160px;padding:14px;flex-shrink:0;border-right:1px solid #473651;overflow:auto}.settings-layout nav button{display:block;width:100%;text-align:left;margin-bottom:8px}.selected{background:#76538f!important}.settings-body{flex:1;overflow:auto;padding:20px 28px;min-width:0}.application-settings fieldset{border:0;margin:0;padding:0;min-width:0}.application-settings label{display:block;margin:12px 0}.application-settings input:not([type=checkbox]):not([type=range]):not([type=color]),.application-settings select,.application-settings textarea{display:block;width:100%;box-sizing:border-box;margin-top:6px;background:#100c1d;color:#f4edff;border:1px solid #62516f;border-radius:9px;padding:10px;font:inherit}.application-settings input[type=range]{display:block;width:100%}.application-settings input[type=color]{margin-left:12px}.application-settings button{background:#30223f;color:#eee8fb;border:1px solid #685178;border-radius:9px;padding:8px 12px;cursor:pointer}.application-settings button:disabled,.application-settings fieldset:disabled{opacity:.6}.application-settings :focus-visible{outline:2px solid #cca3fc;outline-offset:3px}.connection-card,.module-card{padding:14px 18px;margin:14px 0;background:#21192f;border:1px solid #493752;border-radius:14px}.button-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}footer{padding:14px 24px;border-top:1px solid #473651;display:flex;gap:10px;align-items:center}footer span{margin-right:auto;color:#c2b4cd;font-size:12px}.settings-error{color:#ffb6bf!important}.settings-notice{color:#aee7d5!important}pre{white-space:pre-wrap;word-break:break-all;background:#100c1d;padding:14px;border-radius:10px}h3{font-size:19px;margin:0 0 15px}h4{margin:0 0 8px;font-size:15px}@media(max-width:700px){.settings-backdrop{padding:4px}.application-settings{height:96vh}.settings-layout nav{width:95px;padding:8px}.settings-body{padding:15px}.application-settings header,footer{padding:12px}footer span{display:none}}
</style>
