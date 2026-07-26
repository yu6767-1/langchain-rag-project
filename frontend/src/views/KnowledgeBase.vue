<script setup>
import { ref, onMounted } from 'vue'
import { listDocuments, uploadDocument, deleteDocument, getStatsOverview } from '@/api/document'
import { ElMessage, ElMessageBox } from 'element-plus'

const documents = ref([])
const stats = ref({})
const uploading = ref(false)
const uploadRef = ref(null)
const loading = ref(true)

const ALLOWED_TYPES = '.pdf,.txt,.csv,.md,.docx,.xlsx'

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [docsRes, statsRes] = await Promise.all([
      listDocuments(),
      getStatsOverview()
    ])
    documents.value = docsRes.documents
    stats.value = statsRes
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

async function handleUpload(file) {
  uploading.value = true
  try {
    const res = await uploadDocument(file.file)
    ElMessage.success(`文件 "${file.file.name}" 上传成功，正在后台处理...`)
    // 轮询等待文档处理完成（最多等待 30 秒，每 1.5 秒检查一次）
    await pollUntilReady(res.id, 30000, 1500)
  } catch {
    // 错误已在拦截器中处理
  } finally {
    uploading.value = false
  }
  return false  // 阻止 el-upload 的默认上传行为
}

// 轮询直到文档处理完成（ready 或 error）
async function pollUntilReady(docId, maxWait, interval) {
  const startTime = Date.now()
  while (Date.now() - startTime < maxWait) {
    await new Promise(resolve => setTimeout(resolve, interval))
    await loadData()
    const doc = documents.value.find(d => d.id === docId)
    if (doc && (doc.status === 'ready' || doc.status === 'error')) {
      return
    }
  }
}

async function handleDelete(doc) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档 "${doc.filename}" 吗？知识库中的相关内容也会被移除。`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteDocument(doc.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch {
    // 用户取消或出错
  }
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function getStatusText(status) {
  const map = { processing: '处理中', ready: '已就绪', error: '处理失败' }
  return map[status] || status
}

function getStatusType(status) {
  const map = { processing: 'warning', ready: 'success', error: 'danger' }
  return map[status] || 'info'
}
</script>

<template>
  <div class="kb-container">
    <div class="kb-header">
      <h2>📁 知识库管理</h2>
      <el-button @click="loadData" :loading="loading">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 统计面板 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="4">
        <el-statistic title="文档总数" :value="stats.total_documents || 0" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="总片段数" :value="stats.total_chunks || 0" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="已就绪" :value="stats.ready_documents || 0">
          <template #suffix><el-tag type="success" size="small">✅</el-tag></template>
        </el-statistic>
      </el-col>
      <el-col :span="4">
        <el-statistic title="处理中" :value="stats.processing_documents || 0">
          <template #suffix><el-tag type="warning" size="small">⏳</el-tag></template>
        </el-statistic>
      </el-col>
      <el-col :span="4">
        <el-statistic title="失败" :value="stats.error_documents || 0">
          <template #suffix><el-tag type="danger" size="small">❌</el-tag></template>
        </el-statistic>
      </el-col>
      <el-col :span="4">
        <el-statistic title="问答次数" :value="stats.total_messages || 0" />
      </el-col>
    </el-row>

    <!-- 上传区域 -->
    <el-card class="upload-card">
      <template #header><span>📤 上传文档</span></template>
      <el-upload
        ref="uploadRef"
        drag
        :http-request="handleUpload"
        :accept="ALLOWED_TYPES"
        :limit="10"
        multiple
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF、Word(.docx)、Excel(.xlsx)、CSV、TXT、Markdown 格式，单文件最大 50MB
          </div>
        </template>
      </el-upload>
    </el-card>

    <!-- 文档列表 -->
    <el-card class="doc-list-card">
      <template #header><span>📚 已上传文档</span></template>
      <el-table :data="documents" stripe v-loading="loading" empty-text="暂无文档，请上传">
        <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="file_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.file_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="100" align="center">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="片段数" width="80" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="160" align="center">
          <template #default="{ row }">
            {{ row.uploaded_at ? new Date(row.uploaded_at).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" size="small" text @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.kb-container {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  height: 100%;
  overflow-y: auto;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.kb-header h2 {
  margin: 0;
  font-size: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stats-row .el-statistic {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.upload-card {
  margin-bottom: 20px;
}

.doc-list-card {
  margin-bottom: 20px;
}
</style>
