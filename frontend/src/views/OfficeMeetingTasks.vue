<template>
  <div class="office-page">
    <AppSidebar />
    <main class="main">
      <header class="head">
        <div>
          <h2>{{ t("title") }}</h2>
          <p>{{ t("subtitle") }}</p>
        </div>
        <div class="head-actions">
          <el-tag type="primary"
            >{{ t("meeting") }} {{ meetings.length }}</el-tag
          >
          <el-tag type="warning">{{ t("todo") }} {{ openTasks.length }}</el-tag>
          <el-button size="small" @click="openTask">{{
            t("newTask")
          }}</el-button>
          <el-button size="small" type="primary" @click="openMeeting">{{
            t("newMeeting")
          }}</el-button>
        </div>
      </header>

      <section class="workbench">
        <section class="meeting-column panel">
          <div class="panel-head">
            <div>
              <b>{{ t("meetingSchedule") }}</b
              ><span>{{ t("scheduleHint") }}</span>
            </div>
            <div class="schedule-head-actions"><el-button size="mini" @click="goToday">{{ t("today") }}</el-button><el-button size="mini" icon="el-icon-date" circle @click="load"></el-button></div>
          </div>
          <div class="schedule-week">
            <button class="week-shift" @click="shiftWeek(-1)"><i class="el-icon-arrow-left"></i></button>
            <button v-for="day in scheduleDays" :key="day.key" class="schedule-day" :class="{ active: selectedScheduleDate === day.key, weekend: day.weekend, 'has-meeting': hasMeetingOn(day.key) }" @click="selectedScheduleDate = day.key"><small>{{ day.label }}</small><b>{{ day.text }}</b><i v-if="hasMeetingOn(day.key)" class="schedule-dot"></i></button>
            <button class="week-shift" @click="shiftWeek(1)"><i class="el-icon-arrow-right"></i></button>
          </div>
          <div class="meeting-list schedule-list" v-if="scheduleMeetings.length">
            <div
              v-for="meeting in scheduleMeetings"
              :key="meeting.id"
              class="meeting-card schedule-row"
              :class="{
                active: selectedMeeting && selectedMeeting.id === meeting.id,
              }"
              @click="selectMeeting(meeting)"
            >
              <div class="meeting-time">
                <b>{{ time(meeting.start_time) }}</b
                ><small>{{ time(meeting.end_time) }}</small>
              </div>
              <div class="meeting-main">
                <b><i></i>{{ meeting.title }}</b>
                <small>{{ meetingStatus(meeting.status) }}&nbsp;&nbsp;{{ meeting.location || t("online") }} · {{ participants(meeting).length }} {{ t("attendees") }}</small>
                <div class="avatars">
                  <img
                    v-for="person in participants(meeting).slice(0, 4)"
                    :key="person.user_id || person.display_name"
                    :src="avatar(person.display_name)"
                    :title="person.display_name"
                  /><em v-if="participants(meeting).length > 4"
                    >+{{ participants(meeting).length - 4 }}</em
                  >
                </div>
              </div>
              <div class="schedule-actions">
                <a v-if="meeting.meeting_link" :href="meeting.meeting_link" target="_blank" rel="noopener noreferrer" class="schedule-link" @click.stop><i class="el-icon-link"></i>{{ t("enterMeeting") }}</a>
                <span v-else class="schedule-link disabled"><i class="el-icon-link"></i>{{ t("noMeetingLink") }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else :image-size="52" :description="t('emptyDayMeeting')" />

          <section class="meeting-detail">
            <div class="detail-title">
              <b>{{ t("meetingDetail") }}</b
              ><el-tag v-if="selectedMeeting" size="mini" type="primary">{{
                meetingStatus(selectedMeeting.status)
              }}</el-tag>
            </div>
            <template v-if="selectedMeeting">
              <div class="reference-detail">
                <div class="reference-top">
                  <div class="reference-meta">
                    <div class="reference-meta-row">
                      <i class="el-icon-tickets"></i>
                      <div><small>{{ t("subject") }}</small><b>{{ selectedMeeting.title }}</b></div>
                    </div>
                    <div class="reference-meta-row">
                      <i class="el-icon-time"></i>
                      <div><small>{{ t("time") }}</small><b>{{ dateTime(selectedMeeting.start_time) }} - {{ time(selectedMeeting.end_time) }}</b></div>
                    </div>
                    <div class="reference-meta-row">
                      <i class="el-icon-location-outline"></i>
                      <div><small>{{ t("place") }}</small><b>{{ selectedMeeting.location || t("online") }}</b></div>
                    </div>
                    <div class="reference-meta-row meeting-link-row">
                      <i class="el-icon-link"></i>
                      <div><small>{{ t("tencent") }}</small><a v-if="selectedMeeting.meeting_link" :href="selectedMeeting.meeting_link" target="_blank" rel="noopener noreferrer"><i class="el-icon-link"></i> {{ meetingLinkText(selectedMeeting.meeting_link) }}</a><b v-else>{{ t("noMeetingLink") }}</b></div>
                    </div>
                  </div>
                  <div class="reference-attendance">
                    <div class="reference-block-head"><b>{{ t("attendance") }} ({{ participants(selectedMeeting).length }})</b><span>{{ t("detailMore") }} <i class="el-icon-arrow-right"></i></span></div>
                    <div class="reference-people" v-if="participants(selectedMeeting).length">
                      <span v-for="person in participants(selectedMeeting).slice(0, 6)" :key="person.user_id || person.display_name"><img :src="avatar(person.display_name)" /><b>{{ person.display_name }}</b><small>{{ t("confirmed") }}</small></span>
                    </div>
                    <p v-else class="reference-empty">{{ t("noParticipants") }}</p>
                  </div>
                </div>
                <div class="reference-bottom">
                  <div class="reference-block materials-block">
                    <div class="reference-block-head"><b>{{ t("meetingMaterials") }} ({{ materialItems.length }})</b><button v-if="materialItems.length" @click="downloadAllMaterials">{{ t("downloadAll") }}</button></div>
                    <div v-if="materialItems.length" class="material-list"><button v-for="item in materialItems.slice(0, 3)" :key="item.id || item.name" @click="downloadMaterial(item)"><i class="el-icon-document"></i>{{ item.name }}<em class="el-icon-download"></em></button></div>
                    <p v-else class="reference-empty">{{ t("noMaterials") }}</p>
                  </div>
                  <div class="reference-block records-block">
                    <div class="reference-block-head"><b>{{ t("minutesRecord") }}</b><button v-if="isMeetingManager" @click="openFollowup">维护会后内容</button><span v-else :class="{ pending: !selectedMeeting.minutes }">{{ selectedMeeting.minutes ? t("done") : t("notGenerated") }}</span></div>
                    <button class="record-line" :disabled="!selectedMeeting.minutes" @click="openMinutes"><b>{{ t("meetingMinutes") }} <i v-if="selectedMeeting.minutes" class="el-icon-view"></i></b><p>{{ selectedMeeting.minutes || t("minutesPending") }}</p></button>
                  </div>
                  <div class="reference-block action-block">
                    <div class="reference-block-head"><b>{{ t("linkedActions") }}（{{ selectedActions.length }}）</b><button v-if="selectedActions.length" @click="openAction(selectedActions[0])">{{ t("viewAll") }} <i class="el-icon-arrow-right"></i></button></div>
                    <div v-if="selectedActions.length" class="action-list"><button v-for="action in selectedActions.slice(0, 3)" :key="action.id" @click="openAction(action)"><i></i><b>{{ action.title }}</b><em>{{ actionState(action) }}</em></button></div>
                    <p v-else class="reference-empty">{{ t("noAction") }}</p>
                  </div>
                </div>
              </div>
              <div class="detail-grid">
                <div>
                  <i class="el-icon-time"></i><span>{{ t("time") }}</span
                  ><b
                    >{{ dateTime(selectedMeeting.start_time) }} -
                    {{ time(selectedMeeting.end_time) }}</b
                  >
                </div>
                <div>
                  <i class="el-icon-location-outline"></i
                  ><span>{{ t("place") }}</span
                  ><b>{{ selectedMeeting.location || t("online") }}</b>
                </div>
                <div class="detail-link">
                  <i class="el-icon-link"></i><span>{{ t("tencent") }}</span
                  ><a
                    v-if="selectedMeeting.meeting_link"
                    :href="selectedMeeting.meeting_link"
                    target="_blank"
                    >{{ t("enterMeeting") }}</a
                  ><b v-else>-</b>
                </div>
              </div>
              <div class="detail-lower">
                <div class="participant-block">
                  <b
                    >{{ t("attendance") }} ({{
                      participants(selectedMeeting).length
                    }})</b
                  >
                  <div class="participant-list">
                    <span
                      v-for="person in participants(selectedMeeting).slice(
                        0,
                        6
                      )"
                      :key="person.user_id || person.display_name"
                      ><img :src="avatar(person.display_name)" /><small>{{
                        person.display_name
                      }}</small
                      ><em>{{ t("confirmed") }}</em></span
                    >
                  </div>
                </div>
                <div class="detail-actions">
                  <b>{{ t("materialsMinutes") }}</b>
                  <p>{{ selectedMeeting.minutes || t("minutesPending") }}</p>
                  <small class="detail-note">当前面板已展开会议详情</small>
                </div>
                <div class="detail-actions">
                  <b>{{ t("linkedActions") }} ({{ selectedActions.length }})</b>
                  <p v-if="selectedActions.length">
                    {{ selectedActions.map((x) => x.title).join(" · ") }}
                  </p>
                  <p v-else>{{ t("noAction") }}</p>
                  <small class="detail-note">可在右侧任务待办中跟进</small>
                </div>
              </div>
            </template>
            <el-empty
              v-else
              :image-size="48"
              :description="t('selectMeeting')"
            />
          </section>
        </section>

        <section class="task-column panel">
          <div class="panel-head task-head">
            <div>
              <b>{{ t("taskTitle") }}</b
              ><span>{{ t("taskHint") }}</span>
            </div>
            <div class="task-filters">
              <el-select v-model="sourceFilter" size="mini" style="width: 104px"
                ><el-option value="" :label="t('allSources')" /><el-option
                  value="meeting"
                  :label="t('meetingAction')" /><el-option
                  value="cross"
                  :label="t('crossTask')" /><el-option
                  value="document"
                  :label="t('documentTask')" /><el-option
                  value="personal"
                  :label="t('personalTask')" /></el-select
              ><el-select v-model="stateFilter" size="mini" style="width: 92px"
                ><el-option value="" :label="t('allStates')" /><el-option
                  value="overdue"
                  :label="t('overdue')" /><el-option
                  value="pending"
                  :label="t('pending')" /><el-option
                  value="in_progress"
                  :label="t('inProgress')" /><el-option
                  value="done"
                  :label="t('done')"
              /></el-select>
            </div>
          </div>
          <div class="task-table-head">
            <span></span><span>{{ t("taskName") }}</span
            ><span>{{ t("source") }}</span
            ><span>{{ t("responsible") }}</span
            ><span>{{ t("deadline") }}</span
            ><span>{{ t("state") }}</span
            ><span>{{ t("relatedItem") }}</span>
          </div>
          <div
            v-for="task in filteredTasks"
            :key="task.id"
            class="task-row"
            :class="{ overdue: task.overdue }"
          >
            <el-checkbox
              :value="task.status === 'done'"
              @change="toggleTask(task)"
            />
            <div class="task-name">
              <b>{{ task.title }}</b>
            </div>
            <el-tag size="mini" :class="'source-' + task.source">{{
              sourceLabel(task.source)
            }}</el-tag>
            <div class="task-owner">
              <img :src="avatar(ownerName(task))" /><span>{{ ownerName(task) }}</span>
            </div>
            <span class="due" :class="{ late: task.overdue }">{{
              dateTime(task.start_time)
            }}</span>
            <el-tag
              size="mini"
              :type="
                task.status === 'done'
                  ? 'success'
                  : task.overdue
                  ? 'danger'
                  : task.status === 'pending'
                  ? 'warning'
                  : task.status === 'in_progress'
                  ? 'primary'
                  : 'info'
              "
              >{{ taskState(task) }}</el-tag
            >
            <div v-if="relatedMeeting(task) || relatedDocument(task)" class="task-relations"><a v-if="relatedMeeting(task)" class="task-relation" href="#" @click.prevent="selectMeeting(relatedMeeting(task))">{{ relatedMeeting(task).title }} <i class="el-icon-top-right"></i></a><a v-if="relatedDocument(task)" class="task-relation" href="#" @click.prevent="$router.push('/documents')">{{ relatedDocument(task).title }} <i class="el-icon-document"></i></a></div>
            <span v-else class="task-relation-empty">—</span>
          </div>
          <el-empty
            v-if="!filteredTasks.length"
            :image-size="72"
            :description="t('emptyTask')"
            ><el-button type="primary" size="mini" @click="openTask">{{
              t("newTask")
            }}</el-button></el-empty
          >
          <div class="task-foot">
            <span
              >{{ t("total") }} {{ filteredTasks.length }}
              {{ t("records") }}</span
            ><span>{{ t("sourceNote") }}</span>
          </div>
          <section class="reminder-panel">
            <div class="reminder-head"><b>待确认提醒</b><span><i></i> 3 项需处理</span></div>
            <div class="reminder-grid">
              <div class="reminder-item meeting-reminder">
                <div class="reminder-icon"><i class="el-icon-date"></i></div>
                <div><small>会议确认</small><b>确认明日线下评审会</b><p>产品上线评审会 · 10:00</p></div>
                <button @click="handleReminder('meeting')">查看会议</button>
              </div>
              <div class="reminder-item action-reminder">
                <div class="reminder-icon"><i class="el-icon-finished"></i></div>
                <div><small>行动项提醒</small><b>完善产品评审会议纪要</b><p>会议行动项 · 今日 16:00 截止</p></div>
                <button @click="handleReminder('task')">查看任务</button>
              </div>
              <div class="reminder-item meeting-reminder">
                <div class="reminder-icon"><i class="el-icon-alarm-clock"></i></div>
                <div><small>会前准备</small><b>上传评审会议材料</b><p>产品评审会 · 距开始还有 1 小时</p></div>
                <button @click="handleReminder('meeting')">查看会议</button>
              </div>
            </div>
          </section>
        </section>
      </section>
    </main>

    <el-dialog
      :title="t('newMeeting')"
      :visible.sync="meetingVisible"
      width="600px"
      @closed="resetMeetingForm"
    >
      <el-form :model="meetingForm" label-width="86px" size="small" class="dialog-form-card"
        ><section class="form-card"><div class="form-card-title"><i class="el-icon-edit-outline"></i>基本信息</div><el-form-item :label="t('subject')"
          ><el-input v-model="meetingForm.title" /></el-form-item
        ><el-form-item :label="t('time')"
          ><div class="meeting-time-fields"><el-date-picker v-model="meetingForm.date" type="date" value-format="yyyy-MM-dd" placeholder="会议日期" /><el-time-picker v-model="meetingForm.startTime" value-format="HH:mm:ss" placeholder="开始时间" /><el-time-picker v-model="meetingForm.endTime" value-format="HH:mm:ss" placeholder="结束时间" /></div></el-form-item></section
        ><section class="form-card"><div class="form-card-title"><i class="el-icon-user-solid"></i>参会成员</div><div class="department-selector" v-for="department in participantTree" :key="department.id"><div class="department-card"><el-checkbox :value="isGroupChecked(department)" :indeterminate="isGroupPartial(department)" @change="toggleGroup(department, $event)">{{ department.label }}</el-checkbox><small>勾选部门将自动邀请全部成员</small></div><el-collapse v-model="participantExpanded" class="participant-groups"><el-collapse-item v-for="group in department.children" :key="group.id" :name="group.id"><template slot="title"><el-checkbox :value="isGroupChecked(group)" :indeterminate="isGroupPartial(group)" @click.native.stop @change="toggleGroup(group, $event)">{{ group.label }}</el-checkbox><span class="group-count">{{ group.children.length }} 人</span></template><div class="member-card-list"><el-checkbox v-for="member in group.children" :key="member.id" v-model="meetingForm.participantIds" :label="member.user_id">{{ member.label }}</el-checkbox></div></el-collapse-item></el-collapse></div></section
        ><section class="form-card"><div class="form-card-title"><i class="el-icon-connection"></i>会议信息</div><el-form-item :label="t('place')"
         ><el-input
            v-model="meetingForm.location"
             :placeholder="t('online')" /></el-form-item
        ><el-form-item :label="t('tencent')"
          ><el-input
            v-model="meetingForm.meeting_link"
              :placeholder="t('tencentHint')" /></el-form-item
        ><el-form-item label="会议资料"><el-upload action="#" :auto-upload="false" :file-list="meetingFiles" :on-change="onMaterialChange" :on-remove="onMaterialRemove"><el-button size="mini" icon="el-icon-upload">上传资料</el-button></el-upload></el-form-item></section
       ></el-form>
      <span slot="footer"
        ><el-button @click="meetingVisible = false">{{ t("cancel") }}</el-button
        ><el-button type="primary" @click="createMeeting">{{
          t("createNotify")
        }}</el-button></span
      >
    </el-dialog>
    <el-dialog
      :title="t('newTask')"
      :visible.sync="taskVisible"
      width="540px"
      @closed="resetTaskForm"
    >
      <el-form :model="taskForm" label-width="86px" size="small" class="dialog-form-card"
        ><section class="form-card"><div class="form-card-title"><i class="el-icon-check"></i>任务内容</div><el-form-item :label="t('taskName')"
          ><el-input v-model="taskForm.title" /></el-form-item
        ><el-form-item :label="t('source')"
          ><el-select v-model="taskForm.source" style="width: 100%"
            ><el-option value="personal" :label="t('personalTask')" /><el-option
              value="cross"
              :label="t('crossTask')" /><el-option
              value="document"
              :label="t('documentTask')" /></el-select></el-form-item
        ><el-form-item :label="t('deadline')"
          ><el-date-picker
            v-model="taskForm.due"
            type="datetime"
            value-format="yyyy-MM-ddTHH:mm:ss"
            style="width: 100%" /></el-form-item
         ><el-form-item :label="t('description')"
          ><el-input
            v-model="taskForm.description"
            type="textarea"
              :rows="3" /></el-form-item></section
        ><section class="form-card"><div class="form-card-title"><i class="el-icon-paperclip"></i>关联事项</div><el-form-item label="关联会议"><el-select v-model="taskForm.meeting_id" clearable filterable style="width:100%"><el-option v-for="meeting in meetings" :key="meeting.id" :value="meeting.id" :label="meeting.title" /></el-select></el-form-item
        ><el-form-item label="关联公文"><el-select v-model="taskForm.document_id" clearable filterable style="width:100%"><el-option v-for="document in documents" :key="document.id" :value="document.id" :label="document.title" /></el-select></el-form-item></section
      ></el-form>
      <span slot="footer"
        ><el-button @click="taskVisible = false">{{ t("cancel") }}</el-button
        ><el-button type="primary" @click="createTask">{{
          t("save")
        }}</el-button></span
      >
    </el-dialog>
    <el-dialog title="会议纪要" :visible.sync="minutesVisible" width="520px">
      <p class="minutes-dialog-text">{{ (selectedMeeting && selectedMeeting.minutes) || t("minutesPending") }}</p>
    </el-dialog>
    <el-dialog title="会后维护" :visible.sync="followupVisible" width="600px">
      <el-form :model="followupForm" label-width="92px" size="small"><el-form-item label="会议纪要"><el-input v-model="followupForm.minutes" type="textarea" :rows="6" placeholder="填写会议结论、关键讨论与决议" /></el-form-item><el-form-item label="会议记录"><el-input v-model="followupForm.resolutions" type="textarea" :rows="3" placeholder="每行一条会议决议或记录" /></el-form-item><el-divider>新增行动项（可选）</el-divider><el-form-item label="行动项"><el-input v-model="followupForm.actionTitle" placeholder="例如：完成产品评审材料修订" /></el-form-item><el-form-item label="负责人"><el-select v-model="followupForm.assigneeId" clearable filterable style="width:100%"><el-option v-for="member in members" :key="member.user_id" :label="member.display_name" :value="member.user_id" /></el-select></el-form-item><el-form-item label="截止时间"><el-date-picker v-model="followupForm.dueDate" type="datetime" value-format="yyyy-MM-ddTHH:mm:ss" style="width:100%" /></el-form-item></el-form>
      <span slot="footer"><el-button @click="followupVisible=false">取消</el-button><el-button type="primary" @click="saveFollowup">保存会后维护</el-button></span>
    </el-dialog>
    <el-dialog title="关联行动项" :visible.sync="actionVisible" width="500px">
      <template v-if="activeAction">
        <div class="action-dialog-title">{{ activeAction.title }}</div>
        <p class="action-dialog-desc">{{ activeAction.description || '暂无补充说明' }}</p>
        <div class="action-dialog-meta"><span>负责人：{{ activeAction.assignee_name || '未指定' }}</span><span>截止：{{ dateTime(activeAction.due_date) }}</span></div>
      </template>
      <span slot="footer"><el-button @click="actionVisible = false">{{ t("cancel") }}</el-button><el-button v-if="activeAction && activeAction.status !== 'done'" type="primary" @click="completeAction">标记完成</el-button></span>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from "../components/Sidebar/index.vue";
import wang from "../assets/office-avatars/wang-manager.png";
import zhang from "../assets/office-avatars/zhang-lead.png";
import zhou from "../assets/office-avatars/zhou-lead.png";
import li from "../assets/office-avatars/li-lead.png";
import liu from "../assets/office-avatars/liu-member.png";
import zhao from "../assets/office-avatars/zhao-member.png";
import chen from "../assets/office-avatars/chen-member.png";
import wu from "../assets/office-avatars/wu-member.png";
import sun from "../assets/office-avatars/sun-member.png";
import yang from "../assets/office-avatars/yang-member.png";
import feng from "../assets/office-avatars/feng-member.png";
import qian from "../assets/office-avatars/qian-member.png";
const Z = {
  title: "\u4f1a\u8bae\u4efb\u52a1",
  subtitle:
    "\u4f1a\u8bae\u7ec4\u7ec7\u3001\u884c\u52a8\u9879\u4e0e\u534f\u4f5c\u5f85\u529e\u5728\u6b64\u7edf\u4e00\u7ba1\u7406",
  meeting: "\u4f1a\u8bae",
  todo: "\u5f85\u529e",
  newMeeting: "\u65b0\u5efa\u4f1a\u8bae",
  newTask: "\u65b0\u5efa\u4efb\u52a1",
  recentMeetings: "\u8fd1\u671f\u4f1a\u8bae",
  meetingSchedule: "\u4f1a\u8bae\u65e5\u7a0b",
  scheduleHint: "\u6309\u65e5\u67e5\u770b\u4f1a\u8bae\u5b89\u6392\u4e0e\u53c2\u4f1a\u60c5\u51b5",
  today: "\u4eca\u5929",
  emptyDayMeeting: "\u5f53\u65e5\u6682\u65e0\u4f1a\u8bae\u5b89\u6392",
  agendaHint:
    "\u70b9\u51fb\u4f1a\u8bae\u67e5\u770b\u4f1a\u524d\u51c6\u5907\u4e0e\u4f1a\u540e\u8f93\u51fa",
  refresh: "\u5237\u65b0",
  online: "\u7ebf\u4e0a\u4f1a\u8bae",
  attendees: "\u53c2\u4f1a\u6210\u5458",
  tencent: "\u817e\u8baf\u4f1a\u8bae",
  emptyMeeting: "\u6682\u65e0\u8fd1\u671f\u4f1a\u8bae",
  meetingDetail: "\u4f1a\u8bae\u8be6\u60c5",
  time: "\u65f6\u95f4",
  place: "\u5730\u70b9",
  enterMeeting: "\u8fdb\u5165\u4f1a\u8bae",
  attendance: "\u53c2\u4f1a\u786e\u8ba4",
  confirmed: "\u5df2\u786e\u8ba4",
  detailMore: "\u8be6\u60c5",
  noParticipants: "\u6682\u65e0\u53c2\u4f1a\u4eba",
  noMeetingLink: "\u6682\u672a\u586b\u5199",
  meetingMaterials: "\u4f1a\u8bae\u8d44\u6599",
  downloadAll: "\u5168\u90e8\u4e0b\u8f7d",
  noMaterials: "\u6682\u65e0\u4f1a\u8bae\u8d44\u6599",
  minutesRecord: "\u7eaa\u8981\u4e0e\u8bb0\u5f55",
  notGenerated: "\u672a\u751f\u6210",
  meetingMinutes: "\u4f1a\u8bae\u7eaa\u8981",
  recording: "\u5f55\u5236\u56de\u653e",
  noRecording: "\u6682\u65e0\u5f55\u5236",
  viewAll: "\u67e5\u770b\u5168\u90e8",
  materialsMinutes: "\u4f1a\u8bae\u6750\u6599 / \u7eaa\u8981",
  minutesPending:
    "\u6682\u65e0\u7eaa\u8981\uff0c\u4f1a\u540e\u53ef\u6574\u7406\u6216\u4f7f\u7528 AI \u751f\u6210\u8349\u7a3f",
  viewFullDetail: "\u67e5\u770b\u5b8c\u6574\u8be6\u60c5",
  linkedActions: "\u5173\u8054\u884c\u52a8\u9879",
  noAction: "\u6682\u65e0\u884c\u52a8\u9879",
  manageActions: "\u7ba1\u7406\u884c\u52a8\u9879",
  selectMeeting: "\u9009\u62e9\u4e00\u573a\u4f1a\u8bae\u67e5\u770b\u8be6\u60c5",
  taskTitle: "\u4efb\u52a1\u5f85\u529e",
  taskHint:
    "\u5305\u542b\u4f1a\u8bae\u3001\u8de8\u7ec4\u3001\u516c\u6587\u4e0e\u4e2a\u4eba\u4e8b\u9879",
  allSources: "\u5168\u90e8\u6765\u6e90",
  allStates: "\u5168\u90e8\u72b6\u6001",
  meetingAction: "\u4f1a\u8bae\u884c\u52a8\u9879",
  crossTask: "\u8de8\u7ec4\u534f\u4f5c",
  documentTask: "\u516c\u6587\u8ddf\u8fdb",
  personalTask: "\u4e2a\u4eba\u5f85\u529e",
  taskName: "\u4efb\u52a1",
  source: "\u6765\u6e90",
  responsible: "\u8d1f\u8d23\u4eba",
  deadline: "\u622a\u6b62\u65f6\u95f4",
  state: "\u72b6\u6001",
  relatedItem: "\u5173\u8054\u4f1a\u8bae/\u6587\u6863",
  emptyTask: "\u6682\u65e0\u7b26\u5408\u6761\u4ef6\u7684\u4efb\u52a1",
  total: "\u5171",
  records: "\u6761",
  sourceNote:
    "\u4efb\u52a1\u6765\u6e90\u4f1a\u4fdd\u7559\u5173\u8054\u4fe1\u606f",
  noDescription: "\u6682\u65e0\u5907\u6ce8",
  overdue: "\u5df2\u903e\u671f",
  pending: "\u5f85\u5904\u7406",
  inProgress: "\u8fdb\u884c\u4e2d",
  done: "\u5df2\u5b8c\u6210",
  subject: "\u4f1a\u8bae\u4e3b\u9898",
  start: "\u5f00\u59cb",
  end: "\u7ed3\u675f",
  tencentHint: "\u7c98\u8d34\u4f1a\u8bae\u94fe\u63a5\u6216\u4f1a\u8bae\u53f7",
  cancel: "\u53d6\u6d88",
  createNotify: "\u521b\u5efa\u5e76\u901a\u77e5",
  save: "\u4fdd\u5b58",
  description: "\u5907\u6ce8",
};
const avatarMap = {
  "\u738b\u7ecf\u7406": wang,
  "\u5f20\u7ec4\u957f": zhang,
  "\u5468\u7ec4\u957f": zhou,
  "\u674e\u7ec4\u957f": li,
  "\u5218\u7ec4\u5458": liu,
  "\u8d75\u7ec4\u5458": zhao,
  "\u9648\u7ec4\u5458": chen,
  "\u5434\u7ec4\u5458": wu,
  "\u5b59\u7ec4\u5458": sun,
  "\u6768\u7ec4\u5458": yang,
  "\u51af\u7ec4\u5458": feng,
  "\u94b1\u7ec4\u5458": qian,
};
export default {
  components: { AppSidebar },
  data: () => ({
    meetingVisible: false,
    taskVisible: false,
    minutesVisible: false,
    followupVisible: false,
    actionVisible: false,
    activeAction: null,
    selectedMeeting: null,
    selectedScheduleDate: "",
    scheduleAnchorDate: "",
    sourceFilter: "",
    stateFilter: "",
    meetingForm: { date: "", startTime: "", endTime: "", participantIds: [] },
    taskForm: { source: "personal" },
    meetingFiles: [],
    followupForm: {},
    participantExpanded: [],
  }),
  computed: {
    ws() {
      return this.$store.getters["workspace/activeWorkspace"] || {};
    },
    meetings() {
      return (this.$store.state.office.meetings || [])
        .slice()
        .sort((a, b) =>
          String(a.start_time).localeCompare(String(b.start_time))
        );
    },
    agendaMeetings() {
      return this.meetings.slice(0, 3);
    },
    scheduleDays() {
      const target = this.scheduleAnchorDate || this.selectedScheduleDate || (this.meetings[0] && this.dayKey(this.meetings[0].start_time)) || this.dayKey(new Date());
      const monday = this.startOfWeek(target);
      return Array.from({ length: 7 }, (_, index) => {
        const date = this.addDays(monday, index);
        return { key: this.dayKey(date), label: this.weekLabel(date), text: this.monthDay(date), weekend: date.getDay() === 0 || date.getDay() === 6 };
      });
    },
    scheduleMeetings() {
      return this.meetings.filter((meeting) => this.dayKey(meeting.start_time) === this.selectedScheduleDate);
    },
    members() {
      return (this.$store.state.office.organization || { members: [] }).members;
    },
    participantTree() {
      const organization = this.$store.state.office.organization || { groups: [], members: [] };
      const groups = organization.groups || [];
      const members = organization.members || [];
      const memberNode = (member) => ({ id: `member:${member.user_id}`, label: member.display_name, kind: "member", user_id: member.user_id });
      const direct = members.filter((member) => !member.group_id);
      const children = [];
      if (direct.length) children.push({ id: "department-direct", label: "部门直属成员", kind: "group", children: direct.map(memberNode) });
      groups.forEach((group) => {
        const groupMembers = members.filter((member) => member.group_id === group.id);
        children.push({ id: `group:${group.id}`, label: group.name, kind: "group", children: groupMembers.map(memberNode) });
      });
      return [{ id: "department:all", label: organization.department_name || "智慧办公演示部", kind: "department", children }];
    },
    documents() {
      return this.$store.state.office.documents || [];
    },
    currentUser() { return this.$store.getters["user/currentUser"] || {}; },
    isMeetingManager() { return !!(this.selectedMeeting && this.selectedMeeting.organizer_id === this.currentUser.id); },
    schedules() {
      return this.$store.state.office.schedules || [];
    },
    selectedActions() {
      return (this.selectedMeeting && this.selectedMeeting.action_items) || [];
    },
    materialItems() {
      const materials = this.selectedMeeting && this.selectedMeeting.materials;
      return Array.isArray(materials) ? materials : [];
    },
    taskItems() {
      return this.schedules
        .filter((x) => x.event_type === "task")
        .map((task) => ({
          ...task,
          description: this.cleanDescription(task.description),
          source: this.sourceOf(task),
          overdue: this.isOverdue(task),
        }));
    },
    openTasks() {
      return this.taskItems.filter((x) => x.status !== "done");
    },
    filteredTasks() {
      return this.taskItems.filter(
        (x) =>
          (!this.sourceFilter || x.source === this.sourceFilter) &&
          (!this.stateFilter ||
            (this.stateFilter === "overdue"
              ? x.overdue
              : x.status === this.stateFilter))
      );
    },
  },
  watch: {
    "ws.id": {
      immediate: true,
      handler() {
        this.load();
      },
    },
  },
  methods: {
    t(k) {
      return Z[k] || k;
    },
    async load() {
      if (!this.ws.id || this.ws.domain !== "office") return;
      await Promise.all(
        ["loadMeetings", "loadSchedules", "loadOrganization", "loadDocuments"].map((x) =>
          this.$store.dispatch("office/" + x, this.ws.id)
        )
      );
      if (!this.selectedMeeting && this.agendaMeetings.length)
        this.selectMeeting(this.agendaMeetings[0]);
      if (!this.selectedScheduleDate && this.meetings.length) {
        this.selectedScheduleDate = this.dayKey(this.meetings[0].start_time);
        this.scheduleAnchorDate = this.selectedScheduleDate;
      }
    },
    participants(meeting) {
      if (Array.isArray(meeting.participants)) return meeting.participants;
      try {
        return JSON.parse(meeting.participants || "[]");
      } catch (e) {
        return [];
      }
    },
    avatar(name) {
      return avatarMap[name] || wang;
    },
    asDate(value) {
      if (value instanceof Date) return new Date(value.getTime());
      const key = String(value || "").slice(0, 10);
      return key ? new Date(`${key}T00:00:00`) : new Date();
    },
    dayKey(value) {
      const date = this.asDate(value);
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${date.getFullYear()}-${month}-${day}`;
    },
    startOfWeek(value) {
      const date = this.asDate(value);
      const day = date.getDay() || 7;
      date.setDate(date.getDate() - day + 1);
      return date;
    },
    addDays(value, amount) {
      const date = this.asDate(value);
      date.setDate(date.getDate() + amount);
      return date;
    },
    monthDay(value) {
      const date = this.asDate(value);
      return `${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    },
    weekLabel(value) {
      return ["\u5468\u65e5", "\u5468\u4e00", "\u5468\u4e8c", "\u5468\u4e09", "\u5468\u56db", "\u5468\u4e94", "\u5468\u516d"][this.asDate(value).getDay()];
    },
    shiftWeek(amount) {
      const target = this.scheduleAnchorDate || this.selectedScheduleDate || this.dayKey(new Date());
      this.scheduleAnchorDate = this.dayKey(this.addDays(target, amount * 7));
      this.selectedScheduleDate = this.scheduleAnchorDate;
    },
    goToday() {
      const today = this.dayKey(new Date());
      this.scheduleAnchorDate = today;
      this.selectedScheduleDate = today;
    },
    openMeeting() {
      this.meetingVisible = true;
      this.participantExpanded = [];
    },
    openTask() {
      this.taskVisible = true;
    },
    resetMeetingForm() {
      this.meetingForm = { date: "", startTime: "", endTime: "", participantIds: [] };
      this.meetingFiles = [];
    },
    resetTaskForm() {
      this.taskForm = { source: "personal", meeting_id: "", document_id: "" };
    },
    groupMemberIds(group) {
      const children = group.children || [];
      return children.reduce((ids, child) => ids.concat(child.kind === "member" ? [child.user_id] : this.groupMemberIds(child)), []);
    },
    isGroupChecked(group) { const ids = this.groupMemberIds(group); return ids.length > 0 && ids.every((id) => this.meetingForm.participantIds.includes(id)); },
    isGroupPartial(group) { const ids = this.groupMemberIds(group); const selected = ids.filter((id) => this.meetingForm.participantIds.includes(id)).length; return selected > 0 && selected < ids.length; },
    toggleGroup(group, checked) {
      const ids = this.groupMemberIds(group);
      const current = this.meetingForm.participantIds.filter((id) => !ids.includes(id));
      this.meetingForm.participantIds = checked ? [...new Set([...current, ...ids])] : current;
    },
    onMaterialChange(file, fileList) { this.meetingFiles = fileList; },
    onMaterialRemove(_, fileList) { this.meetingFiles = fileList; },
    readMaterial(file) {
      return new Promise((resolve) => {
        if (!file || !file.raw) return resolve({ name: file && file.name });
        const reader = new FileReader();
        reader.onload = () => resolve({ id: `material-${Date.now()}-${file.name}`, name: file.name, size: file.size, content: reader.result });
        reader.onerror = () => resolve({ name: file.name, size: file.size });
        reader.readAsDataURL(file.raw);
      });
    },
    hasMeetingOn(day) { return this.meetings.some((meeting) => this.dayKey(meeting.start_time) === day); },
    async createMeeting() {
      if (!this.meetingForm.title || !this.meetingForm.date || !this.meetingForm.startTime || !this.meetingForm.endTime)
        return this.$message.warning(
          "\u8bf7\u5b8c\u6574\u586b\u5199\u4f1a\u8bae\u4e3b\u9898\u548c\u65f6\u95f4"
        );
      const participants = this.members
        .filter((m) => this.meetingForm.participantIds.includes(m.user_id))
        .map((m) => ({ user_id: m.user_id, display_name: m.display_name }));
      const materials = await Promise.all(this.meetingFiles.map((file) => this.readMaterial(file)));
      await this.$store.dispatch("office/createMeeting", {
        workspace_id: this.ws.id,
        title: this.meetingForm.title,
        start_time: `${this.meetingForm.date}T${this.meetingForm.startTime}`,
        end_time: `${this.meetingForm.date}T${this.meetingForm.endTime}`,
        participants,
        meeting_link: this.meetingForm.meeting_link,
        location: this.meetingForm.location,
        materials,
      });
      this.meetingVisible = false;
      await this.load();
      this.$message.success(
        "\u4f1a\u8bae\u5df2\u521b\u5efa\uff0c\u53c2\u4f1a\u6210\u5458\u5c06\u6536\u5230\u901a\u77e5"
      );
    },
    async createTask() {
      if (!this.taskForm.title || !this.taskForm.due)
        return this.$message.warning(
          "\u8bf7\u586b\u5199\u4efb\u52a1\u548c\u622a\u6b62\u65f6\u95f4"
        );
      const source = `[source:${this.taskForm.source}]`;
      await this.$store.dispatch("office/createSchedule", {
        workspace_id: this.ws.id,
        title: this.taskForm.title,
        description: `${source}${this.taskForm.description || ""}`,
        event_type: "task",
        start_time: this.taskForm.due,
        end_time: this.taskForm.due,
        priority: "medium",
        meeting_id: this.taskForm.meeting_id || null,
        document_id: this.taskForm.document_id || null,
      });
      this.taskVisible = false;
      await this.$store.dispatch("office/loadSchedules", this.ws.id);
      this.$message.success("\u4efb\u52a1\u5df2\u521b\u5efa");
    },
    async selectMeeting(meeting) {
      this.selectedMeeting = await this.$store.dispatch(
        "office/getMeeting",
        meeting.id
      );
    },
    openFollowup() {
      if (!this.isMeetingManager) return;
      this.followupForm = { minutes: this.selectedMeeting.minutes || "", resolutions: (this.selectedMeeting.resolutions || []).join("\n"), actionTitle: "", assigneeId: "", dueDate: "" };
      this.followupVisible = true;
    },
    async saveFollowup() {
      if (!this.followupForm.minutes.trim()) return this.$message.warning("请填写会议纪要");
      await this.$store.dispatch("office/updateMeeting", { id: this.selectedMeeting.id, data: { minutes: this.followupForm.minutes, resolutions: this.followupForm.resolutions.split("\n").map((item) => item.trim()).filter(Boolean) }, workspaceId: this.ws.id });
      if (this.followupForm.actionTitle.trim()) {
        const member = this.members.find((item) => item.user_id === this.followupForm.assigneeId) || {};
        await this.$store.dispatch("office/createActionItem", { meetingId: this.selectedMeeting.id, workspaceId: this.ws.id, data: { title: this.followupForm.actionTitle, assignee_id: member.user_id, assignee_name: member.display_name, due_date: this.followupForm.dueDate || this.selectedMeeting.end_time, create_schedule: true } });
      }
      await this.selectMeeting(this.selectedMeeting);
      await this.$store.dispatch("office/loadSchedules", this.ws.id);
      this.followupVisible = false;
      this.$message.success("会后内容已维护，关联提醒将自动更新");
    },
    async downloadMaterial(item) {
      if (item.content && String(item.content).startsWith("data:")) {
        const response = await fetch(item.content);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = item.name || "会议资料";
        link.click();
        URL.revokeObjectURL(url);
        return;
      }
      const meeting = this.selectedMeeting || {};
      const content = [
        "智慧办公会议资料（演示附件）",
        "会议：" + (meeting.title || "未命名会议"),
        "资料：" + (item.name || "未命名资料"),
        "说明：该文件为演示环境生成的可下载资料说明。",
      ].join("\n");
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "演示资料_" + (item.name || "会议资料") + ".txt";
      link.click();
      URL.revokeObjectURL(url);
    },
    downloadAllMaterials() {
      this.materialItems.forEach((item, index) => {
        window.setTimeout(() => this.downloadMaterial(item), index * 180);
      });
      this.$message.success("已开始下载全部会议资料");
    },
    openMinutes() {
      if (this.selectedMeeting && this.selectedMeeting.minutes) this.minutesVisible = true;
    },
    openAction(action) {
      this.activeAction = action;
      this.actionVisible = true;
    },
    async completeAction() {
      if (!this.activeAction) return;
      await this.$store.dispatch("office/updateActionItem", {
        id: this.activeAction.id,
        data: { status: "done" },
        workspaceId: this.ws.id,
      });
      await this.selectMeeting(this.selectedMeeting);
      this.activeAction = this.selectedActions.find((item) => item.id === this.activeAction.id) || this.activeAction;
      this.actionVisible = false;
      this.$message.success("行动项已标记完成");
    },
    handleReminder(type) {
      if (type === "meeting") {
        const meeting = this.meetings.find((item) => item.status === "scheduled");
        if (meeting) {
          this.selectedScheduleDate = this.dayKey(meeting.start_time);
          this.scheduleAnchorDate = this.selectedScheduleDate;
          this.selectMeeting(meeting);
          return;
        }
      }
      if (type === "task") {
        const action = this.filteredTasks.find((item) => item.status !== "done" && item.status !== "cancelled");
        if (action) this.openAction(action);
      }
    },
    sourceOf(task) {
      const d = task.description || "";
      if (task.meeting_id || task.action_item_id) return "meeting";
      const found = d.match(/^\[source:(cross|document|personal)\]/);
      return found ? found[1] : "personal";
    },
    cleanDescription(value) {
      return String(value || "").replace(
        /^\[source:(cross|document|personal)\]\s*/,
        ""
      );
    },
    sourceLabel(source) {
      return this.t(
        {
          meeting: "meetingAction",
          cross: "crossTask",
          document: "documentTask",
          personal: "personalTask",
        }[source]
      );
    },
    ownerName(task) {
      const member = this.members.find((item) => item.user_id === task.user_id);
      if (member) return member.display_name;
      const current = this.$store.getters["user/currentUser"] || {};
      return current.display_name || current.name || current.username || "—";
    },
    relatedMeeting(task) {
      return task.meeting_id
        ? this.meetings.find((meeting) => meeting.id === task.meeting_id)
        : null;
    },
    relatedDocument(task) { return task.document_id ? this.documents.find((document) => document.id === task.document_id) : null; },
    isOverdue(task) {
      return (
        task.status !== "done" &&
        task.start_time &&
        new Date(task.start_time) < new Date()
      );
    },
    async toggleTask(task) {
      await this.$store.dispatch("office/updateSchedule", {
        id: task.id,
        data: { status: task.status === "done" ? "pending" : "done" },
        workspaceId: this.ws.id,
      });
      this.$message.success(
        task.status === "done"
          ? "\u4efb\u52a1\u5df2\u91cd\u65b0\u6253\u5f00"
          : "\u4efb\u52a1\u5df2\u5b8c\u6210"
      );
    },
    meetingStatus(status) {
      return (
        {
          scheduled: "\u5f85\u53ec\u5f00",
          ongoing: "\u8fdb\u884c\u4e2d",
          completed: "\u5df2\u5b8c\u6210",
          cancelled: "\u5df2\u53d6\u6d88",
        }[status] || "\u5f85\u53ec\u5f00"
      );
    },
    meetingLinkText(link) {
      return link === "https://meeting.tencent.com/dm/Eu0CcrWlsjpX"
        ? "点击加入腾讯会议（663-983-429）"
        : "点击加入腾讯会议";
    },
    taskState(task) {
      return task.status === "done"
        ? this.t("done")
        : task.status === "in_progress"
        ? this.t("inProgress")
        : task.overdue
        ? this.t("overdue")
        : this.t("pending");
    },
    actionState(action) {
      return action.status === "done" ? this.t("done") : action.status === "in_progress" ? this.t("inProgress") : this.t("meetingAction");
    },
    dateTime(v) {
      return String(v || "-")
        .replace("T", " ")
        .slice(0, 16);
    },
    date(v) {
      return String(v || "").slice(5, 10);
    },
    time(v) {
      return String(v || "").slice(11, 16);
    },
  },
};
</script>

<style scoped>
.office-page {
  display: flex;
  min-height: 100vh;
  padding: 12px;
  gap: 12px;
  background: #f3f6fb;
}
.main {
  flex: 1;
  min-width: 0;
  padding: 18px;
  background: #fff;
  border-radius: 12px;
}
.head,
.panel-head,
.detail-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.head {
  padding-bottom: 13px;
  margin-bottom: 14px;
  border-bottom: 1px solid #edf0f5;
}
.head h2 {
  margin: 0 0 4px;
}
.head p,
.panel-head span {
  margin: 0;
  color: #8190a4;
  font-size: 13px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 7px;
}
.workbench {
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  gap: 14px;
  align-items: start;
}
.panel {
  border: 1px solid #e4ebf4;
  border-radius: 10px;
  background: #fbfcff;
  padding: 14px;
}
.panel-head > div:first-child {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.panel-head b,
.detail-title b {
  font-size: 17px;
}
.meeting-list {
  margin-top: 10px;
}
.meeting-card {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 11px;
  margin-bottom: 8px;
  padding: 10px 11px;
  border: 1px solid #e5ebf4;
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}
.meeting-card:hover,
.meeting-card.active {
  border-color: #7baaf0;
  background: #f7fbff;
  box-shadow: 0 2px 7px rgba(55, 110, 190, 0.08);
}
.meeting-time {
  width: 45px;
  padding-right: 9px;
  border-right: 1px solid #e8edf4;
  text-align: center;
}
.meeting-time b,
.meeting-time small,
.meeting-main b,
.meeting-main small {
  display: block;
}
.meeting-time b {
  font-size: 15px;
}
.meeting-time small,
.meeting-main small {
  margin-top: 3px;
  color: #7b899b;
  font-size: 11px;
}
.meeting-main {
  flex: 1;
  min-width: 0;
}
.meeting-main b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meeting-meta {
  margin-top: 5px;
  font-size: 11px;
}
.meeting-state {
  display: inline-block;
  padding: 2px 5px;
  border-radius: 3px;
  background: #ecf5ff;
  color: #3280df;
}
.meeting-state.ongoing {
  background: #fff4df;
  color: #df8a28;
}
.meeting-state.completed {
  background: #edf9f1;
  color: #35a56d;
}
.link-icon {
  margin-left: 6px;
  color: #347ee0;
}
.avatars {
  display: flex;
  align-items: center;
}
.avatars img {
  width: 25px;
  height: 25px;
  margin-left: -5px;
  border: 2px solid #fff;
  border-radius: 50%;
  object-fit: cover;
}
.avatars em {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 25px;
  height: 25px;
  margin-left: 3px;
  border-radius: 50%;
  background: #eef2f7;
  color: #68788c;
  font-size: 10px;
  font-style: normal;
}
.meeting-detail {
  margin-top: 13px;
  padding-top: 12px;
  border-top: 1px solid #e5ebf3;
}
.detail-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr 1fr;
  gap: 7px;
  margin: 10px 0;
}
.detail-grid > div {
  min-height: 52px;
  padding: 8px;
  border-radius: 6px;
  background: #fff;
}
.detail-grid i {
  margin-right: 4px;
  color: #6f9fea;
}
.detail-grid span,
.detail-grid b,
.detail-grid a {
  display: block;
  font-size: 11px;
}
.detail-grid span {
  margin: 4px 0;
  color: #8492a6;
}
.detail-grid b,
.detail-grid a {
  color: #4c5c71;
  word-break: break-all;
}
.detail-link a {
  color: #347ee0;
}
.detail-lower {
  display: grid;
  grid-template-columns: 1.25fr 1fr 1fr;
  gap: 7px;
}
.participant-block,
.detail-actions {
  min-height: 112px;
  padding: 9px;
  border: 1px solid #e7edf5;
  border-radius: 7px;
  background: #fff;
}
.participant-block > b,
.detail-actions > b {
  font-size: 12px;
}
.participant-list {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.participant-list span {
  width: 31px;
  text-align: center;
}
.participant-list img {
  width: 25px;
  height: 25px;
  border-radius: 50%;
  object-fit: cover;
}
.participant-list small,
.participant-list em {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
  font-style: normal;
}
.participant-list em {
  color: #31a873;
}
.detail-actions p {
  height: 40px;
  margin: 7px 0;
  color: #758398;
  font-size: 11px;
  line-height: 1.55;
  overflow: hidden;
}
.detail-note {
  display: block;
  color: #347ee0;
  font-size: 11px;
  line-height: 1.45;
}
.task-head {
  margin-bottom: 10px;
}
.task-filters {
  display: flex;
  gap: 6px;
}
.task-table-head,
.task-row {
  display: grid;
  grid-template-columns: 28px minmax(145px, 1.65fr) 102px 126px 70px;
  align-items: center;
  gap: 8px;
}
.task-table-head {
  padding: 7px 9px;
  color: #7a889a;
  font-size: 11px;
}
.task-row {
  min-height: 58px;
  padding: 7px 9px;
  border-top: 1px solid #e7edf4;
  background: #fff;
}
.task-row:first-of-type {
  border-top: 1px solid #e4ebf4;
}
.task-row.overdue {
  background: #fffafb;
}
.task-name {
  min-width: 0;
}
.task-name b,
.task-name small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-name b {
  font-size: 13px;
}
.task-name small {
  margin-top: 4px;
  color: #8693a4;
  font-size: 11px;
}
.due {
  color: #637187;
  font-size: 12px;
}
.due.late {
  color: #e85a55;
}
.source-meeting {
  color: #3485e7;
  border-color: #cfe2ff;
  background: #f1f7ff;
}
.source-cross {
  color: #8462d5;
  border-color: #e1d5ff;
  background: #f7f2ff;
}
.source-document {
  color: #3d9b71;
  border-color: #cfeedd;
  background: #f0faf5;
}
.source-personal {
  color: #bd7c36;
  border-color: #fae5c6;
  background: #fff8ed;
}
.task-foot {
  display: flex;
  justify-content: space-between;
  margin-top: 11px;
  color: #8491a1;
  font-size: 11px;
}
.task-column .el-empty {
  padding: 40px 0;
}
.head-actions .el-tag {
  height: 32px;
  line-height: 30px;
}
.head-actions .el-button {
  margin: 0;
}
@media (max-width: 1120px) {
  .workbench {
    grid-template-columns: 1fr;
  }
  .task-column {
    min-height: 0;
  }
}
@media (max-width: 760px) {
  .office-page {
    padding: 0;
  }
  .main {
    padding: 12px;
    border-radius: 0;
  }
  .head {
    align-items: flex-start;
    gap: 10px;
  }
  .head-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .detail-grid,
  .detail-lower {
    grid-template-columns: 1fr;
  }
  .task-table-head {
    display: none;
  }
  .task-row {
    grid-template-columns: 24px 1fr 86px;
  }
  .task-row .due {
    display: none;
  }
  .task-row .el-tag:last-child {
    display: none;
  }
  .task-filters {
    margin-top: 8px;
  }
  .panel-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }
}
/* Visual system: compact office workspace rather than default component panels. */
.office-page {
  --ink: #1f2f46;
  --muted: #7587a1;
  --line: #dfe8f5;
  --soft-blue: #edf5ff;
  --blue: #377ff0;
  padding: 14px;
  gap: 14px;
  background: #f3f6fb;
  font-family: "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}
.main {
  padding: 20px;
  border: 1px solid #edf1f7;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 8px 26px rgba(37, 67, 112, 0.045);
}
.head {
  min-height: 54px;
  padding: 0 2px 17px;
  margin-bottom: 17px;
  border-color: #e6edf6;
}
.head h2 {
  margin-bottom: 5px;
  color: var(--ink);
  font-size: 25px;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.2;
}
.head p,
.panel-head span {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}
.head-actions {
  gap: 8px;
}
.head-actions /deep/ .el-tag {
  height: 31px;
  padding: 0 11px;
  border: 1px solid #d6e5fb;
  border-radius: 7px;
  background: #f1f7ff;
  color: #3d84ed;
  font-weight: 500;
  line-height: 29px;
}
.head-actions /deep/ .el-tag--warning {
  border-color: #f8e4c7;
  background: #fff8ed;
  color: #df922f;
}
.head-actions /deep/ .el-button {
  height: 32px;
  padding: 0 13px;
  border-radius: 7px;
  border-color: #d9e3f0;
  color: #4a5d76;
  font-weight: 500;
}
.head-actions /deep/ .el-button--primary {
  border-color: #3e83ef;
  background: linear-gradient(135deg, #4d91f5, #347aec);
  box-shadow: 0 4px 10px rgba(52, 122, 236, 0.2);
  color: #fff;
}
.workbench {
  grid-template-columns: minmax(440px, 0.95fr) minmax(560px, 1.15fr);
  gap: 16px;
}
.panel {
  padding: 16px;
  border-color: var(--line);
  border-radius: 14px;
  background: linear-gradient(180deg, #fbfcff 0%, #f8fbff 100%);
  box-shadow: 0 5px 16px rgba(37, 67, 112, 0.025);
}
.panel-head {
  min-height: 25px;
}
.panel-head > div:first-child {
  gap: 9px;
}
.panel-head b,
.detail-title b {
  position: relative;
  color: var(--ink);
  font-size: 18px;
  font-weight: 700;
}
.panel-head b::before {
  display: inline-block;
  width: 4px;
  height: 17px;
  margin: 0 8px -3px 0;
  border-radius: 5px;
  background: #4c8ef3;
  content: "";
}
.panel-head /deep/ .el-button--text {
  color: #5a8fe3;
  font-weight: 500;
}
.meeting-list {
  margin-top: 13px;
}
.meeting-card {
  min-height: 76px;
  gap: 12px;
  margin-bottom: 9px;
  padding: 10px;
  border: 1px solid #e1eaf6;
  border-left: 4px solid #d1e2fb;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 2px 5px rgba(36, 71, 120, 0.018);
  transition: 0.2s ease;
}
.meeting-card:hover,
.meeting-card.active {
  transform: translateY(-1px);
  border-color: #91bbf7;
  border-left-color: #4288f2;
  background: linear-gradient(90deg, #f7fbff, #fff);
  box-shadow: 0 7px 15px rgba(49, 109, 202, 0.09);
}
.meeting-time {
  width: 51px;
  padding: 5px 8px;
  border: 0;
  border-radius: 8px;
  background: var(--soft-blue);
  text-align: center;
}
.meeting-time small,
.meeting-time em {
  margin: 0;
  color: #778aa5;
  font-size: 10px;
  font-style: normal;
  line-height: 1.2;
}
.meeting-time b {
  margin: 3px 0 2px;
  color: #2b4a70;
  font-size: 15px;
  line-height: 1;
}
.meeting-main b {
  color: #233852;
  font-size: 14px;
  font-weight: 650;
}
.meeting-main small {
  color: #7789a3;
  font-size: 11px;
}
.meeting-meta {
  margin-top: 6px;
}
.meeting-state {
  padding: 2px 6px;
  border-radius: 4px;
  background: #edf5ff;
  color: #4086ef;
  font-size: 10px;
}
.link-icon {
  color: #6d85a7;
  font-size: 10px;
}
.avatars img {
  width: 29px;
  height: 29px;
  box-shadow: 0 1px 3px rgba(42, 73, 118, 0.12);
}
.meeting-detail {
  margin-top: 16px;
  padding-top: 15px;
  border-top-color: #e1e9f4;
}
.detail-title /deep/ .el-tag {
  border-radius: 5px;
  background: #edf5ff;
  border-color: #d5e6ff;
  color: #4387ee;
}
.detail-grid {
  gap: 9px;
  margin: 11px 0;
}
.detail-grid > div {
  min-height: 63px;
  padding: 10px;
  border: 1px solid #e9eff7;
  border-radius: 9px;
  background: #fff;
}
.detail-grid i {
  display: inline-block;
  width: 21px;
  color: #528ee7;
  font-size: 15px;
}
.detail-grid span {
  margin: 5px 0 4px;
  color: #8797ac;
  font-size: 11px;
}
.detail-grid b,
.detail-grid a {
  color: #405671;
  font-size: 12px;
  font-weight: 600;
}
.detail-lower {
  gap: 9px;
}
.participant-block,
.detail-actions {
  min-height: 119px;
  padding: 11px;
  border-color: #e2eaf4;
  border-radius: 9px;
  box-shadow: 0 2px 5px rgba(38, 66, 106, 0.018);
}
.participant-block > b,
.detail-actions > b {
  color: #2c415b;
  font-size: 12px;
  font-weight: 650;
}
.detail-actions p {
  color: #7488a1;
}
.detail-note {
  color: #4a86e7;
  font-weight: 500;
}
.task-head {
  margin-bottom: 13px;
}
.task-filters /deep/ .el-input__inner {
  height: 30px;
  border-color: #dce6f3;
  border-radius: 7px;
  background: #fff;
  color: #62758e;
}
.task-table-head {
  padding: 9px 10px;
  border-radius: 7px;
  background: #f1f5fa;
  color: #7c8ea5;
  font-size: 11px;
  font-weight: 600;
}
.task-row {
  min-height: 65px;
  padding: 8px 10px;
  border-top: 1px solid #e5ecf5;
  background: rgba(255, 255, 255, 0.82);
  transition: background 0.15s ease;
}
.task-row:hover {
  background: #f5f9ff;
}
.task-name b {
  color: #2e435d;
  font-size: 13px;
  font-weight: 650;
}
.task-name small {
  color: #8393a8;
}
.task-row /deep/ .el-tag {
  width: fit-content;
  border-radius: 4px;
  font-weight: 500;
}
.task-foot {
  margin-top: 13px;
  padding-top: 10px;
  border-top: 1px dashed #dce5f0;
  color: #8293a8;
}
.task-column .el-empty {
  padding: 42px 0 34px;
}
.task-column /deep/ .el-empty__description p {
  color: #8191a5;
  font-size: 12px;
}
.task-column /deep/ .el-empty__image {
  opacity: 0.6;
}
@media (max-width: 1250px) {
  .workbench {
    grid-template-columns: minmax(400px, 0.92fr) minmax(500px, 1.08fr);
  }
}

/* Meeting detail follows the two-layer meeting record layout. */
.meeting-detail {
  padding: 14px;
  border: 1px solid #e3ebf5;
  border-radius: 12px;
  background: #fff;
}
.meeting-detail > .detail-title {
  padding-bottom: 10px;
  border-bottom: 1px solid #e9eff7;
}
.reference-detail {
  overflow: hidden;
  margin-top: 12px;
  border: 1px solid #e4ebf5;
  border-radius: 10px;
  background: #fff;
}
.reference-top {
  display: grid;
  grid-template-columns: minmax(228px, 0.9fr) minmax(270px, 1.1fr);
  min-height: 164px;
}
.reference-meta {
  padding: 12px 14px;
  border-right: 1px solid #e7edf5;
}
.reference-meta-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 9px;
}
.reference-meta-row:last-child {
  margin-bottom: 0;
}
.reference-meta-row > i {
  width: 14px;
  margin-top: 2px;
  color: #90a1b8;
  font-size: 14px;
}
.reference-meta-row small,
.reference-meta-row b,
.reference-meta-row a {
  display: block;
}
.reference-meta-row small {
  margin-bottom: 2px;
  color: #8797ab;
  font-size: 11px;
}
.reference-meta-row b,
.reference-meta-row a {
  max-width: 226px;
  overflow: hidden;
  color: #3b506b;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reference-meta-row a {
  color: #4389ed;
  text-decoration: none;
}
.reference-attendance {
  min-width: 0;
  padding: 12px 14px;
}
.reference-block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 7px;
  min-height: 18px;
}
.reference-block-head b {
  color: #2d415b;
  font-size: 12px;
  font-weight: 700;
}
.reference-block-head span {
  color: #8b9bb0;
  font-size: 10px;
  white-space: nowrap;
}
.reference-block-head span.pending {
  color: #e7a347;
}
.reference-people {
  display: flex;
  gap: 9px;
  margin-top: 11px;
}
.reference-people span {
  width: 35px;
  min-width: 0;
  text-align: center;
}
.reference-people img {
  width: 33px;
  height: 33px;
  border-radius: 50%;
  box-shadow: 0 2px 5px rgba(43, 71, 111, 0.13);
  object-fit: cover;
}
.reference-people b,
.reference-people small {
  display: block;
  overflow: hidden;
  margin-top: 3px;
  color: #546982;
  font-size: 10px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reference-people small {
  margin-top: 1px;
  color: #35af76;
  font-size: 9px;
}
.reference-bottom {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  padding: 9px;
  border-top: 1px solid #e7edf5;
  background: #fafcff;
}
.reference-block {
  min-width: 0;
  min-height: 118px;
  padding: 11px 12px;
  border: 1px solid #e3ebf5;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 5px rgba(43, 72, 114, 0.02);
}
.materials-block {
  background: linear-gradient(180deg, #ffffff, #fbfdff);
}
.records-block {
  background: linear-gradient(180deg, #ffffff, #fffcf8);
}
.action-block {
  background: linear-gradient(180deg, #ffffff, #fbfaff);
}
.reference-empty {
  margin: 23px 0 0;
  color: #98a6b7;
  font-size: 11px;
}
.material-list,
.action-list {
  margin-top: 8px;
}
.material-list button,
.action-list button {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 5px;
  min-width: 0;
  margin-bottom: 7px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #51677f;
  font-size: 11px;
  text-align: left;
  cursor: pointer;
}
.material-list button:hover,
.action-list button:hover { color: #3279dc; }
.reference-block-head button {
  padding: 0;
  border: 0;
  background: transparent;
  color: #7290b4;
  font-size: 10px;
  cursor: pointer;
}
.reference-block-head button:hover { color: #337ddf; }
.material-list i {
  color: #6d9be6;
}
.material-list em {
  margin-left: auto;
  color: #99a9ba;
  font-style: normal;
}
.record-line {
  margin-top: 9px;
}
button.record-line {
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
button.record-line:disabled { cursor: default; }
button.record-line:not(:disabled):hover b { color: #347edc; }
.record-line b,
.record-line p {
  display: block;
  margin: 0;
  color: #5d7189;
  font-size: 10px;
  line-height: 1.45;
}
.record-line p {
  overflow: hidden;
  margin-top: 2px;
  color: #9aa7b6;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.action-list button i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #4c91f2;
}
.action-list button b {
  overflow: hidden;
  color: #526880;
  font-size: 11px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.action-list button em {
  margin-left: auto;
  padding: 2px 4px;
  border-radius: 3px;
  background: #edf4ff;
  color: #5b8ee1;
  font-size: 9px;
  font-style: normal;
  white-space: nowrap;
}
.minutes-dialog-text { margin: 0; color: #4d627b; font-size: 14px; line-height: 1.9; white-space: pre-wrap; }
.action-dialog-title { color: #253e5c; font-size: 17px; font-weight: 700; }
.action-dialog-desc { min-height: 45px; margin: 12px 0; color: #65788f; font-size: 13px; line-height: 1.7; }
.action-dialog-meta { display: flex; gap: 22px; padding: 10px 12px; border-radius: 6px; background: #f6f9fd; color: #6b7f97; font-size: 12px; }
.meeting-detail .detail-grid,
.meeting-detail .detail-lower {
  display: none;
}
@media (max-width: 1120px) {
  .reference-top {
    grid-template-columns: 1fr;
  }
  .reference-meta {
    border-right: 0;
    border-bottom: 1px solid #e7edf5;
  }
}
@media (max-width: 760px) {
  .reference-bottom {
    grid-template-columns: 1fr;
  }
  .reference-block {
    min-height: 100px;
  }
}

/* Compact task ledger: task ownership and its true business relation stay visible. */
.task-column {
  min-width: 0;
  overflow-x: hidden;
}
.task-column .task-table-head,
.task-column .task-row {
  grid-template-columns: 20px minmax(95px, 1.35fr) 62px 62px 86px 54px minmax(70px, .75fr);
  min-width: 0;
  column-gap: 5px;
}
.task-column .task-table-head {
  margin-top: 2px;
  padding: 9px 8px;
  background: #f4f7fb;
  color: #8494a8;
  font-size: 10px;
}
.task-column .task-row {
  min-height: 50px;
  padding: 7px 8px;
}
.task-column .task-name b {
  color: #3e5169;
  font-size: 12px;
  font-weight: 600;
}
.task-owner {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  color: #5f738c;
  font-size: 11px;
}
.task-owner img {
  width: 23px;
  height: 23px;
  flex: 0 0 auto;
  border-radius: 50%;
  object-fit: cover;
}
.task-owner span,
.task-relation {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-relations { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
.task-relation {
  display: block;
  color: #4e89e5;
  font-size: 10px;
  text-decoration: none;
}
.task-relation:hover {
  color: #236ed0;
  text-decoration: underline;
}
.task-relation-empty {
  color: #a1adba;
  font-size: 12px;
}
.task-column .due {
  font-size: 10px;
}
.task-column .el-tag {
  padding: 0 5px;
  font-size: 10px;
}
.reminder-panel {
  min-width: 0;
  margin-top: 14px;
  padding: 12px 14px 14px;
  border: 1px solid #e2eaf4;
  border-radius: 9px;
  background: linear-gradient(105deg, #fbfdff, #f8fbff);
}
.reminder-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.reminder-head b { color: #324b68; font-size: 13px; }
.reminder-head span { color: #8597ad; font-size: 11px; }
.reminder-head span i { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #f39a3d; }
.reminder-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
.reminder-item {
  display: grid;
  grid-template-columns: 29px minmax(0, 1fr);
  column-gap: 7px;
  padding: 9px;
  border: 1px solid #e6edf7;
  border-radius: 7px;
  background: #fff;
}
.reminder-icon { grid-row: span 2; display: flex; align-items: flex-start; justify-content: center; padding-top: 2px; color: #508ce6; font-size: 16px; }
.reminder-item small { color: #8799ae; font-size: 10px; }
.reminder-item b { overflow: hidden; display: block; margin-top: 2px; color: #405874; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.reminder-item p { overflow: hidden; grid-column: 2; margin: 4px 0 6px; color: #90a0b2; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.reminder-item button { grid-column: 2; justify-self: start; padding: 0; border: 0; background: transparent; color: #3e83ea; font-size: 11px; cursor: pointer; }
.reminder-item button:hover { color: #126dde; text-decoration: underline; }
.action-reminder .reminder-icon { color: #ef9b43; }
@media (max-width: 760px) {
  .reminder-grid { grid-template-columns: 1fr; }
}

/* Weekly meeting agenda: the date strip drives the compact time-based list. */
.schedule-head-actions {
  display: flex;
  align-items: center;
  gap: 5px;
}
.schedule-head-actions /deep/ .el-button {
  height: 25px;
  padding: 0 8px;
  border-color: #dfe8f4;
  color: #647891;
  font-size: 11px;
}
.schedule-head-actions /deep/ .el-button.is-circle {
  width: 25px;
  padding: 0;
}
.schedule-week {
  display: grid;
  grid-template-columns: 28px repeat(7, minmax(0, 1fr)) 28px;
  align-items: stretch;
  margin-top: 11px;
  overflow: hidden;
  border: 1px solid #e2eaf5;
  border-radius: 8px;
  background: #fff;
}
.schedule-day,
.week-shift {
  min-width: 0;
  min-height: 44px;
  padding: 5px 2px;
  border: 0;
  border-right: 1px solid #edf1f6;
  background: #fff;
  color: #5f7088;
  cursor: pointer;
}
.schedule-day:last-of-type {
  border-right: 0;
}
.schedule-day small,
.schedule-day b {
  display: block;
  line-height: 1.35;
}
.schedule-day small {
  color: #74849a;
  font-size: 9px;
}
.schedule-day b {
  margin-top: 2px;
  color: #52667e;
  font-size: 10px;
  font-weight: 600;
}
.schedule-day.weekend small,
.schedule-day.weekend b {
  color: #df766d;
}
.schedule-day.active {
  background: linear-gradient(180deg, #3180ef, #216fe2);
  box-shadow: 0 3px 7px rgba(40, 116, 232, 0.2);
}
.schedule-day.active small,
.schedule-day.active b {
  color: #fff;
}
.schedule-day { position: relative; }
.schedule-dot { position: absolute; bottom: 4px; left: 50%; width: 4px; height: 4px; margin-left: -2px; border-radius: 50%; background: #ed5c5c; }
.schedule-day.active .schedule-dot { background: #ffe3e3; }
.dialog-form-card { max-height: 62vh; overflow-y: auto; padding-right: 4px; }
.form-card { margin-bottom: 12px; padding: 13px 14px 4px; border: 1px solid #e4ebf5; border-radius: 9px; background: linear-gradient(145deg, #fff, #fafcff); }
.form-card:last-child { margin-bottom: 0; }
.form-card-title { display: flex; align-items: center; gap: 6px; margin: 0 0 11px; color: #36516f; font-size: 13px; font-weight: 700; }
.form-card-title i { color: #4c8fea; font-size: 15px; }
.meeting-time-fields { display: grid; grid-template-columns: minmax(132px, 1.1fr) minmax(112px, .9fr) minmax(112px, .9fr); gap: 9px; }
.meeting-time-fields /deep/ .el-date-editor { width: 100%; }
.department-selector { border: 1px solid #e6edf6; border-radius: 8px; overflow: hidden; background: #fff; }
.department-card { display: flex; align-items: center; justify-content: space-between; padding: 10px 11px; background: #f4f8ff; }
.department-card /deep/ .el-checkbox__label { color: #34516f; font-weight: 700; }
.department-card small { color: #8b9caf; font-size: 10px; }
.participant-groups /deep/ .el-collapse-item__header { height: 38px; padding: 0 10px; border-bottom-color: #edf1f6; color: #4b647e; font-size: 12px; }
.participant-groups /deep/ .el-collapse-item__wrap { border-bottom: 0; }
.participant-groups /deep/ .el-collapse-item__content { padding: 0 10px 10px; }
.group-count { margin-left: auto; margin-right: 8px; color: #8b9caf; font-size: 10px; }
.member-card-list { display: flex; flex-wrap: wrap; gap: 7px 14px; padding: 9px; border-radius: 7px; background: #fbfcfe; }
.member-card-list /deep/ .el-checkbox { margin-right: 0; }
.member-card-list /deep/ .el-checkbox__label { color: #60758e; font-size: 12px; }
.week-shift {
  color: #4b91ed;
  font-size: 13px;
}
.week-shift:last-child {
  border-left: 1px solid #edf1f6;
  border-right: 0;
}
.schedule-list {
  overflow: hidden;
  margin-top: 9px;
  border: 1px solid #e2eaf5;
  border-radius: 8px;
  background: #fff;
}
.meeting-card.schedule-row {
  display: grid;
  grid-template-columns: 72px minmax(160px, 1fr) 126px;
  min-height: 94px;
  gap: 12px;
  margin: 0;
  padding: 10px 14px;
  border: 1px solid #d9e7fa;
  border-left: 3px solid #4b91f5;
  border-bottom: 1px solid #d9e7fa;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 7px rgba(53, 111, 194, 0.045);
  transform: none;
}
.meeting-card.schedule-row:last-child {
  border-bottom: 1px solid #d9e7fa;
}
.meeting-card.schedule-row:hover,
.meeting-card.schedule-row.active {
  border-color: #75a9f5;
  border-left-color: #3181ef;
  background: linear-gradient(90deg, #f3f8ff 0%, #fff 72%);
  box-shadow: 0 4px 12px rgba(43, 116, 222, 0.1);
  transform: none;
}
.meeting-card.schedule-row.active {
  box-shadow: 0 4px 12px rgba(43, 116, 222, 0.12);
}
.schedule-row .meeting-time {
  width: auto;
  padding: 4px 12px 4px 0;
  border-right: 1px solid #e9eef5;
  border-radius: 0;
  background: transparent;
}
.schedule-row .meeting-time b {
  margin: 0 0 5px;
  color: #26384f;
  font-size: 15px;
}
.schedule-row .meeting-time small {
  color: #8a99ac;
  font-size: 12px;
}
.schedule-row .meeting-main b {
  color: #2472dc;
  font-size: 14px;
}
.schedule-row .meeting-main b i {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin: 0 9px 1px 0;
  border-radius: 50%;
  background: #3986ef;
}
.schedule-row .meeting-main small {
  margin-top: 5px;
  color: #7e91aa;
  font-size: 12px;
}
.schedule-row .avatars {
  justify-self: start;
  margin-top: 7px;
}
.schedule-row .avatars img {
  width: 25px;
  height: 25px;
  margin-left: -6px;
  border: 2px solid #fff;
}
.schedule-row .avatars img:first-child { margin-left: 0; }
.schedule-row .avatars em {
  width: 25px;
  height: 25px;
  font-size: 10px;
}
.schedule-actions {
  display: flex;
  height: 100%;
  align-items: center;
  justify-content: flex-end;
  white-space: nowrap;
}
.schedule-link {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 102px;
  height: 30px;
  gap: 5px;
  border: 1px solid #d9e6f8;
  border-radius: 16px;
  color: #3980e8;
  background: #fff;
  font-size: 12px;
  text-decoration: none;
  white-space: nowrap;
}
.schedule-link:hover { border-color: #9fc4f8; background: #f5f9ff; color: #1d70df; }
.schedule-link i {
  color: #3b83ed;
  font-size: 13px;
}
.schedule-link.disabled { color: #a2afbf; border-color: #e8edf4; }
.schedule-link.disabled i { color: #aeb9c7; }
@media (max-width: 1120px) {
  .meeting-card.schedule-row {
    grid-template-columns: 65px minmax(145px, 1fr) 112px;
  }
}
@media (max-width: 760px) {
  .schedule-week {
    grid-template-columns: 23px repeat(7, minmax(37px, 1fr)) 23px;
  }
  .meeting-card.schedule-row {
    grid-template-columns: 54px minmax(120px, 1fr);
  }
  .schedule-row .schedule-actions {
    display: none;
  }
}
</style>
