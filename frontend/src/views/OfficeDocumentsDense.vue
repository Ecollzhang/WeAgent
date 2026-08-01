<template>
  <div class="office-page">
    <AppSidebar />
    <main class="main">
      <header class="page-head">
        <div><h2>公文审批</h2><p>业务申请、逐级审批、公文流转与模板复用</p></div>
        <el-button type="primary" size="small" @click="openDoc()">新建公文</el-button>
      </header>

      <section class="summary">
        <div class="summary-metrics"><div class="metric"><small>我发起的</small><b>{{ docs.length }}</b></div><div class="metric warn"><small>待我处理</small><b>{{ pending.length }}</b></div><div class="metric success"><small>已通过</small><b>{{ approved.length }}</b></div></div>
        <div class="template-launch"><div class="launch-label"><b>快捷发起</b></div><div class="launch-buttons"><button v-for="item in quickTypes" :key="item.key" @click="fromType(item.key)"><i :class="item.icon"></i>{{ item.label }}</button></div></div>
      </section>

      <el-tabs v-model="tab" class="office-tabs">
        <el-tab-pane label="公文工作台" name="workbench">
          <section class="section-card">
            <div class="section-head"><div><b>我提交的公文</b><span>起草、提交与发布</span></div><el-button type="text" size="mini" @click="openDoc()">+ 新建</el-button></div>
            <el-table :data="docs" size="small" class="dense-table" empty-text="暂无我发起的公文，点击右上角新建或使用快捷模板。">
              <el-table-column label="事项" min-width="280"><template slot-scope="{row}"><button class="title-link" @click="detail(row)">{{ row.title }}</button><small class="row-type">{{ typeLabel(row.document_type) }}</small></template></el-table-column>
              <el-table-column label="审批人" width="112"><template slot-scope="{row}"><div v-if="row.reviewer_name" class="sender-person reviewer-person"><img :src="avatar(row.reviewer_name)" /><span>{{ row.reviewer_name }}</span></div><span v-else class="reviewer-empty">{{ row.status === 'draft' ? '未提交审批' : '审批中' }}</span></template></el-table-column>
              <el-table-column label="接收人 / 确认" min-width="175"><template slot-scope="{row}"><el-popover v-if="recipientAvatarNames((row.recipient_summary || {}).names).length" placement="bottom-start" width="230" trigger="click" popper-class="recipient-popover"><div class="recipient-popover-head">全部接收人（{{ ((row.recipient_summary || {}).names || []).length }}）</div><div class="recipient-popover-list"><span v-for="name in ((row.recipient_summary || {}).names || [])" :key="name"><img :src="avatar(name)" /><b>{{ name }}</b></span></div><div slot="reference" class="recipient-avatars" :title="'点击查看全部接收人：' + recipientLabel(row.recipient_summary)"><img v-for="name in recipientAvatarNames((row.recipient_summary || {}).names)" :key="name" :src="avatar(name)" :alt="name" /><em v-if="((row.recipient_summary || {}).names || []).length > 3">+{{ ((row.recipient_summary || {}).names || []).length - 3 }}</em></div></el-popover><span v-else class="recipient-text">未指定</span><small v-if="recipientAvatarNames((row.recipient_summary || {}).names).length" class="recipient-names">{{ recipientLabel(row.recipient_summary) }}</small><small v-if="row.status === 'published'" class="receipt-state">已确认 {{ (row.recipient_summary || {}).confirmed || 0 }}/{{ (row.recipient_summary || {}).total || 0 }}</small></template></el-table-column>
              <el-table-column label="状态" width="92"><template slot-scope="{row}"><el-tag size="mini" :type="tag(row.status)">{{ state(row.status) }}</el-tag></template></el-table-column>
              <el-table-column label="更新时间" width="138"><template slot-scope="{row}"><span class="time">{{ dateTime(row.updated_at) }}</span></template></el-table-column>
              <el-table-column label="操作" width="130"><template slot-scope="{row}"><el-button v-if="row.status==='draft'" type="text" size="mini" @click="submit(row)">提交审批</el-button><el-button v-if="row.status==='approved'" type="text" size="mini" @click="publish(row)">发布</el-button><span v-if="!['draft','approved'].includes(row.status)" class="muted">—</span></template></el-table-column>
            </el-table>
          </section>

          <section class="section-card approval-card">
            <div class="section-head"><div><b>待我审批</b><span>请及时处理需要流转的事项</span></div><el-tag size="mini" type="warning">{{ pending.length }} 项待处理</el-tag></div>
            <el-table :data="pending" size="small" class="dense-table" empty-text="当前没有待处理审批事项。">
              <el-table-column label="审批事项" min-width="250"><template slot-scope="{row}"><button class="title-link" @click="approvalDetail(row)">{{ row.title }}</button><small class="row-type">{{ typeLabel(row.document_type) }} · {{ row.submitter_name || '提交人' }}</small></template></el-table-column>
              <el-table-column label="发送人" width="106"><template slot-scope="{row}"><div class="sender-person"><img :src="avatar(row.submitter_name)" /><span>{{ row.submitter_name || '提交人' }}</span></div></template></el-table-column>
              <el-table-column label="接收人" min-width="135"><template slot-scope="{row}"><el-popover v-if="recipientAvatarNames(row.recipient_names).length" placement="bottom-start" width="230" trigger="click" popper-class="recipient-popover"><div class="recipient-popover-head">全部接收人（{{ (row.recipient_names || []).length }}）</div><div class="recipient-popover-list"><span v-for="name in (row.recipient_names || [])" :key="name"><img :src="avatar(name)" /><b>{{ name }}</b></span></div><div slot="reference" class="recipient-avatars" :title="'点击查看全部接收人：' + recipientNames(row.recipient_names)"><img v-for="name in recipientAvatarNames(row.recipient_names)" :key="name" :src="avatar(name)" :alt="name" /><em v-if="(row.recipient_names || []).length > 3">+{{ (row.recipient_names || []).length - 3 }}</em></div></el-popover><span v-else class="recipient-text">未指定</span><small v-if="recipientAvatarNames(row.recipient_names).length" class="recipient-names">{{ recipientNames(row.recipient_names) }}</small></template></el-table-column>
              <el-table-column label="提交时间" width="138"><template slot-scope="{row}"><span class="time">{{ dateTime(row.created_at) }}</span></template></el-table-column>
              <el-table-column label="操作" width="142"><template slot-scope="{row}"><el-button type="success" size="mini" @click="approve(row)">通过</el-button><el-button type="danger" size="mini" @click="reject(row)">驳回</el-button></template></el-table-column>
            </el-table>
          </section>
          <section class="approval-tip"><i class="el-icon-info"></i><span>点击事项名称可查看正文；审批结果将同步给提交人，并更新公文状态。</span></section>
        </el-tab-pane>

        <el-tab-pane label="模板库" name="templates">
          <section class="template-toolbar"><div><b>公文模板库</b><p>内置模板可直接使用和预览；自建模板支持编辑、复制与删除。</p></div><el-button type="primary" size="small" @click="openTemplate()">新建模板</el-button></section>
          <div class="template-grid">
            <article v-for="item in templates" :key="item.id" class="template-card">
              <div class="template-card-head"><i :class="templateIcon(item.document_type)"></i><el-tag size="mini" :type="item.is_system ? 'info' : 'success'">{{ item.is_system ? '内置' : '自建' }}</el-tag></div>
              <b>{{ item.name }}</b><p>{{ templatePreview(item.content) }}</p>
              <footer><button @click="useTemplate(item)">使用模板</button><button @click="previewTemplate(item)">预览</button><button v-if="!item.is_system" @click="openTemplate(item)">编辑</button><button v-if="!item.is_system" class="danger" @click="removeTemplate(item)">删除</button></footer>
            </article>
            <el-empty v-if="!templates.length" description="暂无模板" :image-size="70" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </main>

    <el-dialog :title="form.id ? '编辑公文' : '新建公文'" :visible.sync="docVisible" width="650px">
      <el-form :model="form" label-width="75px" size="small"><el-form-item label="标题"><el-input v-model="form.title" /></el-form-item><el-form-item label="类型"><el-select v-model="form.document_type" style="width:100%"><el-option v-for="item in documentTypes" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item><el-form-item label="接收人"><el-select v-model="form.recipientIds" multiple filterable collapse-tags placeholder="请选择需接收并确认的成员" style="width:100%"><el-option v-for="member in members" :key="member.user_id" :label="member.display_name" :value="member.user_id" /></el-select></el-form-item><el-form-item label="正文"><el-input v-model="form.content" type="textarea" :rows="10" /></el-form-item></el-form>
      <span slot="footer"><el-button @click="docVisible=false">取消</el-button><el-button type="primary" @click="saveDoc">保存草稿</el-button></span>
    </el-dialog>
    <el-dialog title="模板管理" :visible.sync="templateVisible" width="620px">
      <el-form :model="templateForm" label-width="80px" size="small"><el-form-item label="模板名称"><el-input v-model="templateForm.name" /></el-form-item><el-form-item label="适用类型"><el-select v-model="templateForm.document_type" style="width:100%"><el-option v-for="item in documentTypes" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item><el-form-item label="模板正文"><el-input v-model="templateForm.content" type="textarea" :rows="10" /></el-form-item></el-form>
      <span slot="footer"><el-button @click="templateVisible=false">取消</el-button><el-button type="primary" @click="saveTemplate">保存模板</el-button></span>
    </el-dialog>
    <el-dialog :title="previewTitle" :visible.sync="previewVisible" width="620px"><pre>{{ previewContent }}</pre></el-dialog>
    <el-dialog title="公文详情" :visible.sync="detailVisible" width="650px"><div class="detail-title">{{ current && current.title }}</div><pre>{{ content }}</pre><section v-if="current && current.recipients && current.recipients.length" class="receipt-panel"><div class="receipt-head"><b>接收确认（{{ (current.recipient_summary || {}).confirmed || 0 }}/{{ (current.recipient_summary || {}).total || 0 }}）</b><span>发布后跟踪知悉情况</span></div><div class="receipt-list"><span v-for="item in current.recipients" :key="item.user_id"><img :src="avatar(item.display_name)" /><b>{{ item.display_name }}</b><small :class="{ confirmed: receiptConfirmed(item.user_id) }">{{ receiptConfirmed(item.user_id) ? '已确认' : '待确认' }}</small></span></div><el-button v-if="canConfirmCurrent" type="primary" size="mini" @click="confirmReceipt">确认已知悉</el-button></section></el-dialog>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
const quickTypes = [
  { key: 'notice', type: 'notice', templateName: '会议通知', label: '会议通知', icon: 'el-icon-message' },
  { key: 'leave', type: 'request', templateName: '请假申请', label: '请假申请', icon: 'el-icon-date' },
  { key: 'reimbursement', type: 'request', templateName: '报销申请', label: '报销申请', icon: 'el-icon-wallet' },
  { key: 'procurement', type: 'request', templateName: '采购申请', label: '采购申请', icon: 'el-icon-goods' },
]
const documentTypes = [{ value: 'notice', label: '通知' }, { value: 'request', label: '申请' }, { value: 'report', label: '报告' }, { value: 'minutes', label: '会议纪要' }]
export default {
  components: { AppSidebar },
  data: () => ({ tab: 'workbench', quickTypes, documentTypes, docVisible: false, templateVisible: false, detailVisible: false, previewVisible: false, previewTitle: '', previewContent: '', current: null, form: { document_type: 'notice' }, templateForm: { document_type: 'notice' } }),
  computed: {
    ws() { return this.$store.getters['workspace/activeWorkspace'] || {} },
    members() { return (this.$store.state.office.organization || { members: [] }).members },
    currentUser() { return this.$store.getters['user/currentUser'] || {} },
    docs() { return this.$store.state.office.documents || [] },
    approvals() { return this.$store.state.office.approvals || [] },
    templates() { return this.$store.state.office.templates || [] },
    pending() { return this.approvals.filter(x => x.can_handle) },
    approved() { return this.docs.filter(x => ['approved', 'published'].includes(x.status)) },
    content() { return this.current ? this.current.content : '' },
    canConfirmCurrent() { return this.current && this.current.status === 'published' && (this.current.recipients || []).some(item => item.user_id === this.currentUser.id) && !this.receiptConfirmed(this.currentUser.id) },
  },
  watch: { 'ws.id': { immediate: true, handler() { this.load() } } },
  methods: {
    load() { if (this.ws.id && this.ws.domain === 'office') return Promise.all(['loadDocuments', 'loadApprovals', 'loadTemplates', 'loadOrganization'].map(a => this.$store.dispatch('office/' + a, this.ws.id))) },
    openDoc() { this.form = { document_type: 'notice', recipientIds: [] }; this.docVisible = true },
    fromType(key) { const item = quickTypes.find(x => x.key === key); const x = this.templates.find(a => a.is_system && a.name === item.templateName) || this.templates.find(a => a.is_system && a.document_type === item.type); this.form = { title: x ? x.name : item.templateName, content: x ? x.content : '', document_type: item.type, recipientIds: [] }; this.docVisible = true },
    useTemplate(item) { this.form = { title: item.name, content: item.content, document_type: item.document_type, recipientIds: [] }; this.tab = 'workbench'; this.docVisible = true },
    async saveDoc() { if (!this.form.title || !this.form.content) return this.$message.warning('请填写标题和正文'); const recipients = this.members.filter(item => this.form.recipientIds.includes(item.user_id)).map(item => ({ user_id: item.user_id, display_name: item.display_name })); await this.$store.dispatch('office/createDocument', { title: this.form.title, content: this.form.content, document_type: this.form.document_type, recipients, workspace_id: this.ws.id }); this.docVisible = false; this.$message.success('公文草稿已保存'); this.load() },
    async submit(row) { await this.$store.dispatch('office/submitDocument', { id: row.id, data: {}, workspaceId: this.ws.id }); this.$message.success('已提交审批') },
    async publish(row) { await this.$store.dispatch('office/publishDocument', { id: row.id, workspaceId: this.ws.id }); this.$message.success('公文已发布') },
    async detail(row) { this.current = await this.$store.dispatch('office/getDocument', row.id); this.detailVisible = true },
    async approvalDetail(row) { const result = await this.$store.dispatch('office/getApproval', row.id); this.current = result.document; this.detailVisible = true },
    receiptConfirmed(userId) { return (this.current && this.current.receipts || []).some(item => item.recipient_id === userId && item.confirmed_at) },
    async confirmReceipt() { await this.$store.dispatch('office/confirmDocumentReceipt', { id: this.current.id, workspaceId: this.ws.id }); this.current = await this.$store.dispatch('office/getDocument', this.current.id); this.$message.success('已确认知悉该公文') },
    async approve(row) { await this.$store.dispatch('office/approve', { id: row.id, data: {}, workspaceId: this.ws.id }); this.$message.success('审批已通过') },
    async reject(row) { try { const result = await this.$prompt('请填写驳回意见', '驳回审批', { inputPattern: /\S+/, inputErrorMessage: '驳回意见不能为空' }); await this.$store.dispatch('office/reject', { id: row.id, data: { comment: result.value }, workspaceId: this.ws.id }); this.$message.success('已驳回并通知提交人') } catch (e) {} },
    openTemplate(item) { this.templateForm = item ? { ...item } : { document_type: 'notice' }; this.templateVisible = true },
    async saveTemplate() { if (!this.templateForm.name || !this.templateForm.content) return this.$message.warning('请填写模板名称和正文'); if (this.templateForm.id) await this.$store.dispatch('office/updateTemplate', { id: this.templateForm.id, data: this.templateForm, workspaceId: this.ws.id }); else await this.$store.dispatch('office/createTemplate', { ...this.templateForm, workspace_id: this.ws.id }); this.templateVisible = false; this.$message.success('模板已保存') },
    async removeTemplate(item) { try { await this.$confirm(`确认删除模板“${item.name}”吗？`, '删除模板', { type: 'warning' }); await this.$store.dispatch('office/deleteTemplate', { id: item.id, workspaceId: this.ws.id }); this.$message.success('模板已删除') } catch (e) {} },
    previewTemplate(item) { this.previewTitle = item.name; this.previewContent = item.content || '暂无模板内容'; this.previewVisible = true },
    state(s) { return ({ draft: '草稿', reviewing: '审批中', approved: '已批准', published: '已发布', rejected: '已驳回' })[s] || s },
    tag(s) { return ({ draft: 'info', reviewing: 'warning', approved: 'success', published: 'success', rejected: 'danger' })[s] || '' },
    typeLabel(t) { return (documentTypes.find(x => x.value === t) || {}).label || '公文' },
    templateIcon(t) { return ({ notice: 'el-icon-message', request: 'el-icon-document', report: 'el-icon-tickets', minutes: 'el-icon-notebook-2' })[t] || 'el-icon-document' },
    templatePreview(value) { return String(value || '暂无模板说明').replace(/\s+/g, ' ').slice(0, 55) },
    dateTime(value) { return String(value || '—').replace('T', ' ').slice(0, 16) },
    recipientAvatarNames(names) { return Array.isArray(names) ? names.filter(Boolean).slice(0, 3) : [] },
    recipientNames(names) { return Array.isArray(names) && names.length ? names.slice(0, 3).join('、') + (names.length > 3 ? ' 等' : '') : '未指定' },
    recipientLabel(summary) { return this.recipientNames((summary || {}).names) || '未指定' },
    avatar(name) { const key = String(name || '').charAt(0); const map = { '王': 'wang-manager', '李': 'li-lead', '周': 'zhou-lead', '张': 'zhang-lead', '陈': 'chen-member', '刘': 'liu-member', '赵': 'zhao-member', '杨': 'yang-member', '吴': 'wu-member', '孙': 'sun-member', '钱': 'qian-member', '冯': 'feng-member' }; try { return require(`../assets/office-avatars/${map[key] || 'wang-manager'}.png`) } catch (e) { return '' } },
  },
}
</script>

<style scoped>
.office-page{display:flex;min-height:100vh;padding:12px;gap:12px;background:#f3f6fb}.main{flex:1;min-width:0;padding:18px 22px;background:#fff;border-radius:12px}.page-head{display:flex;align-items:flex-start;justify-content:space-between;padding-bottom:13px;border-bottom:1px solid #edf0f5}.page-head h2{margin:0 0 4px;color:#172f4d}.page-head p{margin:0;color:#8294aa;font-size:13px}.summary{display:flex;align-items:stretch;gap:12px;margin:13px 0}.summary-metrics{display:flex;gap:9px}.metric{width:116px;min-height:64px;padding:9px 14px;border:1px solid #e3ebf5;border-radius:8px;background:#fbfcff}.metric b,.metric small{display:block}.metric small{color:#617894;font-size:12px;font-weight:600}.metric b{margin-top:3px;color:#4088df;font-size:21px;line-height:25px}.metric.warn b{color:#ef9b43}.metric.success b{color:#43b681}.template-launch{display:flex;flex:1;align-items:center;gap:15px;padding:9px 15px;border:1px solid #e3ebf5;border-radius:8px;background:linear-gradient(90deg,#fbfdff,#f8fbff)}.launch-label{min-width:76px;padding-right:14px;border-right:1px solid #e3ebf4}.launch-label b{display:block;color:#3f5672;font-size:13px;white-space:nowrap}.launch-buttons{display:flex;flex-wrap:wrap;gap:8px}.launch-buttons button{padding:7px 11px;border:1px solid #dce7f4;border-radius:5px;background:#fff;color:#526a85;font-size:12px;cursor:pointer}.launch-buttons button i{margin-right:5px;color:#5b94e4}.launch-buttons button:hover{border-color:#7daff1;color:#2879e5;background:#f5f9ff}.office-tabs /deep/ .el-tabs__header{margin-bottom:13px}.section-card{min-width:0;margin-bottom:13px;padding:12px;border:1px solid #e3ebf4;border-radius:9px;background:#fff}.approval-card{background:linear-gradient(112deg,#fff,#fbfdff)}.section-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:9px}.section-head b{color:#2d4664;font-size:15px}.section-head span{display:block;margin-top:3px;color:#8a9aae;font-size:11px}.dense-table /deep/ .el-table__header th{background:#f6f8fc;color:#8494a7;font-size:11px}.dense-table /deep/ .el-table__cell{padding:8px 0}.title-link{display:block;max-width:100%;overflow:hidden;padding:0;border:0;background:transparent;color:#397bd6;font-size:12px;text-align:left;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}.title-link:hover{text-decoration:underline}.row-type,.receipt-state,.recipient-names{display:block;margin-top:3px;color:#9aa9bb;font-size:10px}.receipt-state{color:#39a56e}.recipient-names{max-width:150px;overflow:hidden;color:#60758d;text-overflow:ellipsis;white-space:nowrap}.person-text,.recipient-text{display:block;overflow:hidden;color:#60758d;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.recipient-avatars{display:flex;align-items:center;height:27px;padding-left:2px;cursor:pointer}.recipient-avatars img{width:25px;height:25px;margin-left:-5px;border:2px solid #fff;border-radius:50%;object-fit:cover;box-shadow:0 1px 3px rgba(60,83,112,.15)}.recipient-avatars img:first-child{margin-left:0}.recipient-avatars em{display:inline-flex;align-items:center;justify-content:center;width:23px;height:23px;margin-left:3px;border-radius:50%;background:#edf3fb;color:#6480a1;font-size:9px;font-style:normal}.recipient-popover-head{margin-bottom:8px;color:#546b86;font-size:12px;font-weight:700}.recipient-popover-list{display:flex;flex-wrap:wrap;gap:8px}.recipient-popover-list span{display:flex;align-items:center;gap:5px;min-width:96px;padding:4px 6px;border-radius:6px;background:#f6f9fd;color:#536a84;font-size:11px}.recipient-popover-list img{width:24px;height:24px;border-radius:50%;object-fit:cover}.recipient-popover-list b{font-weight:500}.sender-person{display:flex;align-items:center;gap:6px;min-width:0;color:#60758d;font-size:11px}.sender-person img{width:24px;height:24px;border-radius:50%;object-fit:cover}.sender-person span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.reviewer-empty{color:#9baabd;font-size:11px}.time,.muted{color:#8493a6;font-size:11px}.approval-tip{display:flex;gap:7px;margin-top:-2px;padding:10px 12px;border-radius:7px;background:#f6f9fd;color:#7c8da1;font-size:11px}.approval-tip i{color:#5b97ea;font-size:14px}.template-toolbar{display:flex;align-items:center;justify-content:space-between;padding:2px 0 13px}.template-toolbar b{color:#2d4664;font-size:16px}.template-toolbar p{margin:5px 0 0;color:#8999aa;font-size:12px}.template-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.template-card{min-height:155px;padding:13px;border:1px solid #e2eaf4;border-radius:9px;background:linear-gradient(150deg,#fff,#f9fbff)}.template-card-head{display:flex;align-items:center;justify-content:space-between}.template-card-head>i{color:#6197e7;font-size:20px}.template-card>b{display:block;margin-top:10px;color:#405872;font-size:14px}.template-card p{height:32px;overflow:hidden;margin:7px 0;color:#8797aa;font-size:11px;line-height:1.5}.template-card footer{display:flex;gap:10px;margin-top:10px}.template-card button{padding:0;border:0;background:transparent;color:#3b80df;font-size:11px;cursor:pointer}.template-card button:hover{text-decoration:underline}.template-card .danger{color:#e35d5d}.detail-title{margin-bottom:10px;color:#2e4765;font-size:17px;font-weight:700}pre{max-height:310px;overflow:auto;padding:14px;border-radius:7px;background:#f7f9fc;color:#4f6279;line-height:1.7;white-space:pre-wrap}.receipt-panel{margin-top:13px;padding:12px;border:1px solid #e2eaf4;border-radius:8px;background:#fbfdff}.receipt-head{display:flex;justify-content:space-between}.receipt-head b{color:#3e5672;font-size:14px}.receipt-head span{color:#91a0b1;font-size:11px}.receipt-list{display:flex;gap:10px;margin:11px 0}.receipt-list span{width:47px;text-align:center}.receipt-list img{width:34px;height:34px;border-radius:50%;object-fit:cover}.receipt-list b,.receipt-list small{display:block;overflow:hidden;margin-top:3px;color:#597089;font-size:10px;text-overflow:ellipsis;white-space:nowrap}.receipt-list small{margin-top:1px;color:#a1afbd}.receipt-list small.confirmed{color:#36aa70}@media(max-width:850px){.summary{flex-wrap:wrap}.template-launch{min-width:100%}}@media(max-width:760px){.template-launch{align-items:flex-start;flex-direction:column;gap:10px}.launch-label{border:0;padding:0}.template-grid{grid-template-columns:1fr}}
</style>
