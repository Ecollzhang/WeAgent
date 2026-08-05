<template>
  <div class="page">
    <AppSidebar />
    <main>
      <header>
        <div>
          <h2>{{ t.title }}</h2>
          <p>{{ t.desc }}</p>
        </div>
        <div>
          <el-tag type="danger">{{ t.head }} 1</el-tag
          ><el-tag type="primary">{{ t.group }} {{ org.groups.length }}</el-tag
          ><el-tag type="success"
            >{{ t.member }} {{ org.members.length }}</el-tag
          >
        </div>
      </header>
      <div class="org-tabs">
        <button
          :class="['org-tab', { active: activeTab === 'members' }]"
          @click="switchTab('members')"
        >
          {{ t.tabOrg }}
        </button>
        <button
          :class="['org-tab', { active: activeTab === 'tasks' }]"
          @click="switchTab('tasks')"
        >
          {{ t.tasks }}
        </button>
      </div>
      <section v-show="activeTab === 'members'" class="top">
        <section class="card organization-tree">
          <div class="bar">
            <b>{{ t.relation }}</b
            ><button v-if="selectedGroup" class="show-all" @click="clearGroupFilter">
              <i class="el-icon-refresh-left"></i>{{ t.whole }}
            </button><span v-else>{{ t.whole }}</span>
          </div>
          <div class="boss">
            <img :src="photo(t.wang)" />
            <div>
              <b>{{ org.department ? org.department.name : t.dept }}</b>
              <small>{{ t.head }} · {{ t.wang }}</small>
            </div>
          </div>
          <div class="line"></div>
          <div class="groups">
            <article
              v-for="(g, i) in org.groups"
              :key="g.id"
              :class="['c' + i, 'org-group-card', { selected: selectedGroupId === g.id }]"
              role="button"
              tabindex="0"
              @click="selectGroup(g)"
              @keyup.enter="selectGroup(g)"
            >
              <div class="branch"></div>
              <div class="org-group-title">
                <b>{{ g.name }}</b>
                <span>{{ groupRoster(g).length }} {{ t.people }}</span>
              </div>
              <div class="org-leader">
                <img :src="photo(leader(g))" />
                <div>
                  <b>{{ leader(g) }}</b>
                  <small>{{ t.teamLead }}</small>
                </div>
              </div>
              <div class="org-member-tree">
                <div v-for="m in members(g.id)" :key="m.id" class="org-member">
                  <i></i>
                  <img :src="photo(m.display_name)" />
                  <div>
                    <b>{{ m.display_name }}</b>
                    <small>{{ t.normalMember }}</small>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </section>
        <section class="card member-list">
          <div class="member-list-head">
            <div>
              <b>{{ t.list }}</b
              ><span class="member-count"
                >&#128100; {{ selectedGroup ? selectedGroup.name + ' · ' : t.total }} {{ filteredMembers.length }}
                {{ t.people }}</span
              >
            </div>
            <div class="list-actions">
              <el-button v-if="selectedGroup" size="mini" plain icon="el-icon-close" @click="clearGroupFilter">{{ t.allMembers }}</el-button>
              <el-dropdown trigger="click" @command="filterRole"
                ><el-button size="mini" plain icon="el-icon-filter">{{
                  t.filterRoles
                }}</el-button
                ><el-dropdown-menu slot="dropdown"
                  ><el-dropdown-item command="">{{
                    t.allMembers
                  }}</el-dropdown-item
                  ><el-dropdown-item command="department_head">{{
                    t.head
                  }}</el-dropdown-item
                  ><el-dropdown-item command="team_lead">{{
                    t.teamLead
                  }}</el-dropdown-item
                  ><el-dropdown-item command="member">{{
                    t.normalMember
                  }}</el-dropdown-item></el-dropdown-menu
                ></el-dropdown
              ><el-button
                size="mini"
                plain
                icon="el-icon-download"
                @click="exportMembers"
                >{{ t.export }}</el-button
              >
            </div>
          </div>
          <el-table :data="pagedMembers" size="mini" stripe
            ><el-table-column :label="t.member" min-width="118"
              ><template slot-scope="{ row }"
                ><div class="member-name">
                  <img :src="photo(row.display_name)" /><span>{{
                    row.display_name
                  }}</span>
                </div></template
              ></el-table-column
            ><el-table-column :label="t.role" width="105"
              ><template slot-scope="{ row }"
                ><el-tag size="mini" :type="roleType(row.role)">{{
                  role(row.role)
                }}</el-tag></template
              ></el-table-column
            ><el-table-column :label="t.group" min-width="115"
              ><template slot-scope="{ row }">{{
                groupName(row.group_id) || t.direct
              }}</template></el-table-column
            ><el-table-column :label="t.manager" min-width="110"
              ><template slot-scope="{ row }">{{
                memberName(row.manager_user_id) || "-"
              }}</template></el-table-column
            ><el-table-column :label="t.status" width="74"
              ><template
                ><span class="member-online"
                  ><i></i>{{ t.employed }}</span
                ></template
              ></el-table-column
            ></el-table
          >
          <div class="member-pagination">
            <span
              >{{ t.total }} {{ filteredMembers.length }} {{ t.records }}</span
            ><el-pagination
              small
              background
              :current-page.sync="memberPage"
              :page-size="memberPageSize"
              :page-sizes="[10, 20, 50]"
              layout="sizes, prev, pager, next, jumper"
              :total="filteredMembers.length"
              @size-change="changeMemberPageSize"
              @current-change="changeMemberPage"
            />
          </div>
        </section>
      </section>
      <section v-show="activeTab === 'tasks'" class="card tasks">
        <div class="bar">
          <b>{{ t.tasks }}</b>
          <div class="legend">
            <i class="done"></i>{{ t.done }}<i class="doing"></i>{{ t.doing
            }}<i class="todo"></i>{{ t.todo }}
          </div>
        </div>
        <div class="overview-root">
          <div class="dept-summary">
            <div class="dept-person">
              <img :src="photo(t.wang)" />
              <div>
                <b>{{ t.wang }}</b
                ><small>{{
                  org.department ? org.department.name : t.dept
                }}</small>
              </div>
              <el-tag size="mini" type="warning">{{ t.head }}</el-tag
              ><button
                v-if="currentName === t.wang"
                class="robot overview-robot"
                :title="t.ai"
                @click="aiVisible = true"
              >
                &#129302;
              </button>
            </div>
            <div class="dept-metrics">
              <div>
                <b>{{ teamSummary.active }}</b
                ><span>进行中任务</span>
              </div>
              <div>
                <b>{{ teamSummary.meetings }}</b
                ><span>近期会议</span>
              </div>
              <div>
                <b>{{ teamSummary.approvals }}</b
                ><span>待审批</span>
              </div>
            </div>
          </div>
        </div>
        <div class="overview-line"></div>
        <div class="task-overview-groups">
          <article v-for="(g, i) in taskGroups" :key="g.id" :class="'c' + i">
            <div class="overview-branch"></div>
            <div class="group-title">
              <b>{{ g.name }}</b
              ><span>{{ g.items.length }} 人</span>
            </div>
            <div class="group-leader">
              <img :src="photo(g.leader)" />
              <div>
                <b>{{ g.leader }}</b
                ><small>直属领导</small>
              </div>
            </div>
            <div class="member-avatars">
              <img
                v-for="item in g.items"
                :key="item.name"
                :src="photo(item.name)"
                :title="item.name"
              />
            </div>
            <div class="group-metrics">
              <div class="metric-task">
                <b>{{ g.active }}</b
                ><span>进行中任务</span>
              </div>
              <div class="metric-meeting">
                <b>{{ g.meetings }}</b
                ><span>近期会议</span>
              </div>
              <div class="metric-approval">
                <b>{{ g.approvals }}</b
                ><span>待审批</span>
              </div>
            </div>
            <div class="group-focus">
              <span>当前重点</span><b>{{ g.focus }}</b>
            </div>
          </article>
        </div>
      </section>
    </main>
    <el-dialog :title="t.ai" :visible.sync="aiVisible" width="400px"
      ><div class="dialog">
        <span>&#129302;</span>
        <p>{{ t.aiHint }}</p>
      </div>
      <span slot="footer"
        ><el-button type="primary" @click="aiVisible = false">{{
          t.ok
        }}</el-button></span
      ></el-dialog
    >
  </div>
</template>
<script>
import AppSidebar from "../components/Sidebar/index.vue";
import wang from "../assets/office-avatars/wang-manager.png";
import zhang from "../assets/office-avatars/zhang-lead.png";
import liu from "../assets/office-avatars/liu-member.png";
import li from "../assets/office-avatars/li-lead.png";
import chen from "../assets/office-avatars/chen-member.png";
import zhou from "../assets/office-avatars/zhou-lead.png";
import yang from "../assets/office-avatars/yang-member.png";
import zhao from "../assets/office-avatars/zhao-member.png";
import wu from "../assets/office-avatars/wu-member.png";
import sun from "../assets/office-avatars/sun-member.png";
import feng from "../assets/office-avatars/feng-member.png";
import qian from "../assets/office-avatars/qian-member.png";
const t = {
  title: "\u7ec4\u7ec7\u534f\u540c",
  desc: "\u90e8\u95e8\u5c42\u7ea7\u3001\u8de8\u7ec4\u534f\u4f5c\u4e0e\u76f4\u5c5e\u5173\u7cfb",
  head: "\u90e8\u95e8\u8d1f\u8d23\u4eba",
  group: "\u5c0f\u7ec4",
  member: "\u6210\u5458",
  relation: "\u7ec4\u7ec7\u5173\u7cfb",
  whole: "\u663e\u793a\u5168\u4f53\u6210\u5458",
  dept: "\u667a\u6167\u529e\u516c\u6f14\u793a\u90e8",
  wang: "\u738b\u7ecf\u7406",
  people: "\u4eba",
  list: "\u6210\u5458\u6e05\u5355",
  readOnly: "\u7ec4\u7ec7\u56fe\u53ea\u8bfb\u5c55\u793a",
  role: "\u89d2\u8272",
  manager: "\u76f4\u5c5e\u9886\u5bfc",
  direct: "\u90e8\u95e8\u76f4\u5c5e",
  tasks: "\u56e2\u961f\u4efb\u52a1\u603b\u89c8",
  tabOrg: "\u7ec4\u7ec7\u5173\u7cfb\u4e0e\u6210\u5458",
  taskDesc:
    "\u6309\u7ec4\u7ec7\u5c42\u7ea7\u5448\u73b0\u5f53\u524d\u4efb\u52a1",
  done: "\u5df2\u5b8c\u6210",
  doing: "\u8fdb\u884c\u4e2d",
  todo: "\u672a\u5b8c\u6210",
  ai: "AI \u52a9\u7406",
  aiHint:
    "\u540e\u7eed\u5c06\u63a5\u5165\u804a\u5929\uff0c\u5b8c\u6210\u4f1a\u8bae\u7eaa\u8981\u3001\u4efb\u52a1\u62c6\u89e3\u548c\u516c\u6587\u8349\u62df\u3002",
  ok: "\u77e5\u9053\u4e86",
  total: "\u5171",
  records: "\u6761",
  status: "\u72b6\u6001",
  employed: "\u5728\u804c",
  filterRoles: "\u6309\u89d2\u8272\u7b5b\u9009",
  allMembers: "\u5168\u90e8\u6210\u5458",
  teamLead: "\u76f4\u5c5e\u9886\u5bfc",
  normalMember: "\u666e\u901a\u6210\u5458",
  export: "\u5bfc\u51fa",
  activeTasks: "\u8fdb\u884c\u4e2d\u4efb\u52a1",
  recentMeetings: "\u8fd1\u671f\u4f1a\u8bae",
  pendingApprovals: "\u5f85\u5ba1\u6279",
  currentFocus: "\u5f53\u524d\u91cd\u70b9",
  directLead: "\u76f4\u5c5e\u9886\u5bfc",
};
const names = {
  wjl: "\u738b\u7ecf\u7406",
  zzz: "\u5f20\u7ec4\u957f",
  lzy: "\u5218\u7ec4\u5458",
  zzy: "\u8d75\u7ec4\u5458",
  lzz: "\u674e\u7ec4\u957f",
  czy: "\u9648\u7ec4\u5458",
  wzy: "\u5434\u7ec4\u5458",
  szy: "\u5b59\u7ec4\u5458",
  zzg: "\u5468\u7ec4\u957f",
  yzy: "\u6768\u7ec4\u5458",
  fzy: "\u51af\u7ec4\u5458",
  qzy: "\u94b1\u7ec4\u5458",
};
const photos = {
  "\u738b\u7ecf\u7406": wang,
  "\u5f20\u7ec4\u957f": zhang,
  "\u5218\u7ec4\u5458": liu,
  "\u8d75\u7ec4\u5458": zhao,
  "\u674e\u7ec4\u957f": li,
  "\u9648\u7ec4\u5458": chen,
  "\u5434\u7ec4\u5458": wu,
  "\u5b59\u7ec4\u5458": sun,
  "\u5468\u7ec4\u957f": zhou,
  "\u6768\u7ec4\u5458": yang,
  "\u51af\u7ec4\u5458": feng,
  "\u94b1\u7ec4\u5458": qian,
};
export default {
  components: { AppSidebar },
  data: () => ({
    t,
    activeTab: "members",
    aiVisible: false,
    memberRole: "",
    selectedGroupId: null,
    memberPage: 1,
    memberPageSize: 20,
  }),
  computed: {
    workspace() {
      return this.$store.getters["workspace/activeWorkspace"] || {};
    },
    org() {
      return (
        this.$store.state.office.organization || { groups: [], members: [] }
      );
    },
    meetings() {
      return this.$store.state.office.meetings || [];
    },
    approvals() {
      return this.$store.state.office.approvals || [];
    },
    schedules() {
      return this.$store.state.office.schedules || [];
    },
    currentName() {
      return names[(this.$store.state.user.user || {}).username] || "";
    },
    filteredMembers() {
      return this.org.members.filter(
        (member) =>
          (!this.memberRole || member.role === this.memberRole) &&
          (!this.selectedGroupId || this.isInSelectedGroup(member))
      );
    },
    selectedGroup() {
      return this.org.groups.find((group) => group.id === this.selectedGroupId) || null;
    },
    pagedMembers() {
      const start = (this.memberPage - 1) * this.memberPageSize;
      return this.filteredMembers.slice(start, start + this.memberPageSize);
    },
    taskGroups() {
      const jobs = [
        "\u9700\u6c42\u6e05\u5355\u786e\u8ba4",
        "\u8de8\u7ec4\u4efb\u52a1\u8ddf\u8fdb",
        "\u9a8c\u6536\u6750\u6599\u6574\u7406",
      ];
      return this.org.groups.map((g, index) => {
        const items = this.members(g.id).map((m, i) => ({
          name: m.display_name,
          task: jobs[i % jobs.length],
          state: ["doing", "todo", "done"][i % 3],
        }));
        const memberIds = this.members(g.id).map((m) => m.user_id);
        const taskRows = this.schedules.filter(
          (x) =>
            x.event_type === "task" && memberIds.includes(x.assignee_user_id)
        );
        const active =
          taskRows.filter((x) => !["done", "completed"].includes(x.status))
            .length || items.filter((x) => x.state === "doing").length;
        const meetings = this.meetings.filter((x) =>
          this.participants(x).some((p) => memberIds.includes(p.user_id))
        ).length;
        const approvals = this.approvals
          .filter(
            (x) =>
              memberIds.includes(x.submitter_id) ||
              memberIds.includes(x.creator_id)
          )
          .filter((x) => ["pending", "reviewing"].includes(x.status)).length;
        return {
          id: g.id,
          name: g.name,
          leader: this.leader(g),
          items,
          active,
          meetings,
          approvals,
          focus:
            (taskRows[0] && taskRows[0].title) ||
            (items[0] && items[0].task) ||
            "暂无待办",
        };
      });
    },
    teamSummary() {
      return {
        active: this.taskGroups.reduce((sum, g) => sum + g.active, 0),
        meetings: this.taskGroups.reduce((sum, g) => sum + g.meetings, 0),
        approvals: this.approvals.filter((x) =>
          ["pending", "reviewing"].includes(x.status)
        ).length,
      };
    },
  },
  watch: {
    "$route.query.tab": {
      immediate: true,
      handler(tab) {
        this.activeTab = tab === "tasks" ? "tasks" : "members";
      },
    },
    "workspace.id": {
      immediate: true,
      handler() {
        if (this.workspace.id && this.workspace.domain === "office")
          return Promise.all(
            [
              "loadOrganization",
              "loadMeetings",
              "loadSchedules",
              "loadApprovals",
            ].map((x) => this.$store.dispatch("office/" + x, this.workspace.id))
          );
      },
    },
  },
  methods: {
    switchTab(tab) {
      if (this.activeTab === tab && this.$route.query.tab === tab) return;
      this.activeTab = tab;
      this.$router
        .replace({ query: { ...this.$route.query, tab } })
        .catch(() => {});
    },
    photo(n) {
      return photos[n] || wang;
    },
    participants(meeting) {
      if (Array.isArray(meeting.participants)) return meeting.participants;
      try {
        return JSON.parse(meeting.participants || "[]");
      } catch (e) {
        return [];
      }
    },
    filterRole(role) {
      this.memberRole = role;
      this.memberPage = 1;
    },
    selectGroup(group) {
      this.selectedGroupId = group.id;
      this.memberPage = 1;
    },
    clearGroupFilter() {
      this.selectedGroupId = null;
      this.memberPage = 1;
    },
    changeMemberPageSize(size) {
      this.memberPageSize = size;
      this.memberPage = 1;
    },
    changeMemberPage(page) {
      this.memberPage = page;
    },
    exportMembers() {
      const rows = this.filteredMembers.map((member) => [
        member.display_name,
        this.role(member.role),
        this.groupName(member.group_id) || t.direct,
        this.memberName(member.manager_user_id) || "-",
        t.employed,
      ]);
      const csv = [
        "\u6210\u5458,\u89d2\u8272,\u6240\u5728\u5c0f\u7ec4,\u76f4\u5c5e\u9886\u5bfc,\u72b6\u6001",
      ]
        .concat(
          rows.map((row) =>
            row
              .map((value) => `"${String(value).replace(/"/g, '""')}"`)
              .join(",")
          )
        )
        .join("\n");
      const blob = new Blob(["\ufeff" + csv], {
        type: "text/csv;charset=utf-8;",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const suffix =
        {
          department_head: t.head,
          team_lead: t.teamLead,
          member: t.normalMember,
        }[this.memberRole] || t.allMembers;
      link.href = url;
      link.download = `\u667a\u6167\u529e\u516c\u6210\u5458\u6e05\u5355_${suffix}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    },
    memberName(id) {
      const m = this.org.members.find((x) => x.user_id === id);
      return m && m.display_name;
    },
    groupName(id) {
      const g = this.org.groups.find((x) => x.id === id);
      return g && g.name;
    },
    members(id) {
      return this.org.members.filter(
        (x) => x.group_id === id && x.role === "member"
      );
    },
    groupRoster(group) {
      if (!group) return [];
      return this.org.members.filter(
        (member) =>
          member.group_id === group.id || member.user_id === group.leader_user_id
      );
    },
    isInSelectedGroup(member) {
      return this.selectedGroup && this.groupRoster(this.selectedGroup).some(
        (item) => item.user_id === member.user_id
      );
    },
    leader(g) {
      return this.memberName(g.leader_user_id) || t.head;
    },
    role(r) {
      return (
        {
          member: "\u666e\u901a\u6210\u5458",
          team_lead: "\u76f4\u5c5e\u9886\u5bfc",
          department_head: t.head,
        }[r] || r
      );
    },
    roleType(r) {
      return {
        member: "info",
        team_lead: "warning",
        department_head: "danger",
      }[r];
    },
  },
};
</script>
<style scoped>
.page {
  display: flex;
  height: 100vh;
  box-sizing: border-box;
  overflow: hidden;
  padding: 12px;
  gap: 12px;
  background: #f3f6fb;
}
.page main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
}
header,
.bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
header {
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid #edf0f5;
}
.org-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  border-bottom: 1px solid #edf0f5;
}
.org-tab {
  padding: 8px 18px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  font-size: 14px;
  color: #606266;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}
.org-tab:hover {
  color: #409eff;
}
.org-tab.active {
  color: #409eff;
  border-bottom-color: #409eff;
  font-weight: 600;
}
h2 {
  margin: 0 0 3px;
}
p,
.bar span {
  margin: 0;
  color: #8492a6;
  font-size: 13px;
}
header .el-tag {
  margin-left: 6px;
}
.top {
  display: grid;
  grid-template-columns: 1.13fr 1fr;
  gap: 12px;
}
.member-list {
  min-height: 640px;
}
.card {
  border: 1px solid #e5ecf5;
  border-radius: 9px;
  background: #fbfcff;
  padding: 11px;
}
.bar {
  margin-bottom: 8px;
}
.boss {
  width: 210px;
  margin: auto;
  padding: 8px;
  text-align: center;
  border: 1px solid #efd16a;
  background: #fff4cc;
  border-radius: 7px;
}
.boss b,
.boss small,
.root-card b,
.root-card small,
.lead b,
.lead small,
.person b,
.person small {
  display: block;
}
.boss small,
.groups small,
.root-card small,
.lead small,
.person small {
  font-size: 11px;
  color: #77869a;
}
.line {
  height: 14px;
  width: 0;
  margin: auto;
  border-left: 2px solid #c8d4e4;
}
.groups,
.task-groups {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  position: relative;
}
.groups:before,
.task-groups:before {
  content: "";
  position: absolute;
  top: 0;
  left: 16%;
  right: 16%;
  border-top: 2px solid #c8d4e4;
}
.groups article,
.task-groups article {
  padding-top: 10px;
  position: relative;
}
.branch,
.task-branch {
  position: absolute;
  top: 0;
  left: 50%;
  height: 10px;
  border-left: 2px solid #c8d4e4;
}
.groups article {
  min-height: 88px;
  text-align: center;
  border: 1px solid #d9e5f4;
  border-top: 4px solid #4c91ee;
  border-radius: 7px;
  background: #fff;
  padding: 10px 6px;
}
.groups article.c1 {
  border-top-color: #9168d9;
}
.groups article.c2 {
  border-top-color: #f39747;
}
.pills {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
  padding-top: 7px;
  border-top: 1px dashed #dbe4ef;
}
.pills span {
  padding: 2px 6px;
  border-radius: 10px;
  background: #f3f7fb;
  color: #53667b;
  font-size: 11px;
}
.tasks {
  position: relative;
  margin-top: 12px;
  padding-bottom: 10px;
}
.legend {
  font-size: 11px;
  color: #66758a;
}
.legend i {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 2px;
  margin: 0 3px 0 8px;
}
.done {
  background: #4bbb80;
}
.doing {
  background: #4e91ee;
}
.todo {
  background: #a9b4c3;
}
.root {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
}
.root-card {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 6px 9px;
  border: 1px solid #efd16a;
  background: #fff4cc;
  border-radius: 7px;
}
.root-card img,
.lead img,
.person img {
  border-radius: 50%;
  object-fit: cover;
}
.root-card img {
  width: 32px;
  height: 32px;
}
.robot {
  position: relative;
  width: 31px;
  height: 31px;
  border: 1px solid #83afe5;
  border-radius: 50%;
  background: #eff7ff;
  cursor: pointer;
  font-size: 16px;
}
.robot:before {
  content: "";
  position: absolute;
  right: 30px;
  top: 14px;
  width: 22px;
  border-top: 2px dashed #83afe5;
}
.root-line {
  height: 15px;
  border-left: 2px solid #3f4b59;
  width: 0;
  margin: auto;
}
.task-groups:before {
  border-color: #3f4b59;
}
.task-branch {
  border-color: #3f4b59;
}
.lead {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px;
  border-left: 4px solid #4e91ee;
  border-radius: 6px;
  background: #dcecff;
}
.task-groups article.c1 .lead {
  border-color: #9168d9;
  background: #f0e5ff;
}
.task-groups article.c2 .lead {
  border-color: #f39747;
  background: #fff0df;
}
.lead img {
  width: 27px;
  height: 27px;
}
.people {
  margin: 7px 8%;
  padding-left: 7px;
  border-left: 2px solid #c9d5e4;
}
.person {
  display: flex;
  gap: 6px;
  padding: 5px 0;
  border-bottom: 1px dashed #e0e7f0;
}
.person img {
  width: 25px;
  height: 25px;
}
.person small {
  white-space: nowrap;
}
.person em {
  font-style: normal;
  padding: 1px 4px;
  border-radius: 3px;
  color: #fff;
  font-size: 10px;
}
.person em.done {
  background: #4bbb80;
}
.person em.doing {
  background: #4e91ee;
}
.person em.todo {
  background: #a9b4c3;
}
.dialog {
  text-align: center;
}
.dialog span {
  font-size: 32px;
}
.dialog p {
  margin-top: 10px;
  line-height: 1.7;
}
@media (max-width: 1080px) {
  .top {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 720px) {
  .groups,
  .task-groups {
    grid-template-columns: 1fr;
  }
  .groups:before,
  .task-groups:before {
    display: none;
  }
  .groups article,
  .task-groups article {
    padding-top: 7px;
  }
  .branch,
  .task-branch {
    height: 7px;
  }
}
</style>
<style scoped>
/* Keep cartoon faces readable in the compact task tree. */
.root-card img {
  width: 38px;
  height: 38px;
}
.lead img {
  width: 34px;
  height: 34px;
}
.person img {
  width: 32px;
  height: 32px;
}
.person {
  min-height: 38px;
  align-items: center;
}
.person small {
  line-height: 1.45;
}
.tasks {
  padding: 14px 16px 16px;
  background: linear-gradient(180deg, #fbfcff 0%, #fff 100%);
}
.tasks > .bar {
  margin-bottom: 12px;
}
.overview-root {
  display: flex;
  justify-content: center;
}
.dept-summary {
  position: relative;
  width: 310px;
  border: 1px solid #f0c65b;
  border-radius: 9px;
  background: #fffdf7;
  box-shadow: 0 5px 12px rgba(77, 100, 135, 0.06);
}
.dept-person {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px;
  border-bottom: 1px solid #f5ead0;
}
.dept-person img,
.group-leader img,
.member-avatars img {
  border-radius: 50%;
  object-fit: cover;
}
.dept-person img {
  width: 46px;
  height: 46px;
}
.dept-person b,
.group-leader b {
  display: block;
}
.dept-person small,
.group-leader small {
  display: block;
  margin-top: 2px;
  color: #77869a;
  font-size: 11px;
}
.dept-person .el-tag {
  margin-left: auto;
}
.overview-robot {
  position: absolute;
  top: 22px;
  right: -47px;
  width: 34px;
  height: 34px;
  border-color: #7aa8e6;
  background: #f4f8ff;
  box-shadow: 0 2px 7px rgba(65, 117, 183, 0.13);
  z-index: 1;
}
.overview-robot:before {
  right: 33px;
  top: 15px;
  width: 12px;
  border-top: 1px dashed #83afe5;
}
.dept-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  padding: 10px;
}
.dept-metrics div {
  text-align: center;
  border-right: 1px solid #eef1f5;
}
.dept-metrics div:last-child {
  border: 0;
}
.dept-metrics b,
.dept-metrics span {
  display: block;
}
.dept-metrics b {
  font-size: 19px;
  color: #334155;
}
.dept-metrics span {
  margin-top: 3px;
  color: #7c8999;
  font-size: 11px;
}
.overview-line {
  height: 24px;
  width: 0;
  margin: auto;
  border-left: 2px solid #aab9cc;
}
.task-overview-groups {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  position: relative;
}
.task-overview-groups:before {
  content: "";
  position: absolute;
  top: 0;
  left: 16.7%;
  right: 16.7%;
  border-top: 2px solid #aab9cc;
}
.task-overview-groups article {
  position: relative;
  margin-top: 10px;
  padding: 12px;
  border: 1px solid #e2eaf4;
  border-top: 4px solid #4095f4;
  border-radius: 9px;
  background: #fff;
}
.task-overview-groups article.c1 {
  border-top-color: #8a5de6;
}
.task-overview-groups article.c2 {
  border-top-color: #f18731;
}
.overview-branch {
  position: absolute;
  left: 50%;
  top: -12px;
  height: 12px;
  border-left: 2px solid #aab9cc;
}
.group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.group-title b {
  font-size: 16px;
}
.group-title span {
  font-size: 12px;
  color: #738298;
}
.group-leader {
  display: flex;
  align-items: center;
  gap: 8px;
}
.group-leader img {
  width: 44px;
  height: 44px;
}
.member-avatars {
  display: flex;
  gap: 6px;
  margin: 11px 0;
  padding-bottom: 10px;
  border-bottom: 1px dashed #dde5ef;
}
.member-avatars img {
  width: 31px;
  height: 31px;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(59, 83, 110, 0.13);
}
.group-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.group-metrics div {
  padding: 7px 3px;
  border-radius: 6px;
  text-align: center;
}
.group-metrics b,
.group-metrics span {
  display: block;
}
.group-metrics b {
  font-size: 18px;
}
.group-metrics span {
  margin-top: 2px;
  font-size: 10px;
  color: #748399;
  white-space: nowrap;
}
.metric-task {
  background: #eff6ff;
  color: #2778e8;
}
.metric-meeting {
  background: #effaf5;
  color: #22a06b;
}
.metric-approval {
  background: #fff7ed;
  color: #e87519;
}
.group-focus {
  display: flex;
  gap: 7px;
  align-items: center;
  margin-top: 11px;
  padding-top: 9px;
  border-top: 1px dashed #dde5ef;
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
}
.group-focus span {
  color: #8492a6;
  flex: 0 0 auto;
}
.group-focus b {
  overflow: hidden;
  text-overflow: ellipsis;
  color: #536277;
}
.member-list {
  display: flex;
  flex-direction: column;
  padding: 13px;
  background: #fbfcff;
}
.member-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.member-list-head b {
  font-size: 17px;
}
.member-count {
  margin-left: 10px;
  color: #718096;
  font-size: 12px;
}
.list-actions {
  display: flex;
  gap: 7px;
}
.list-actions .el-button {
  border-color: #dce5f0;
  color: #465a73;
  background: #fff;
}
.member-list .el-table {
  overflow: hidden;
  border: 1px solid #e8edf4;
  border-radius: 8px;
}
.member-list .el-table::before {
  display: none;
}
.member-list .el-table th,
.member-list .el-table td {
  border-bottom-color: #e9edf3;
}
.member-list .el-table th {
  background: #fbfcff;
  color: #68778a;
}
.member-list .el-table--mini td,
.member-list .el-table--mini th {
  padding: 7px 0;
}
.member-name {
  display: flex;
  align-items: center;
  gap: 8px;
}
.member-name img {
  width: 28px;
  height: 28px;
  border: 1px solid #e2eaf3;
  border-radius: 50%;
  object-fit: cover;
}
.member-online {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #5f7288;
  font-size: 12px;
}
.member-online i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2bbb7f;
}
.member-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  min-height: 47px;
  color: #68778a;
  font-size: 12px;
}
.member-pagination .el-pagination {
  padding-right: 0;
}
.organization-tree {
  display: flex;
  flex-direction: column;
}
.organization-tree .boss {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  width: 230px;
  min-height: 54px;
  text-align: left;
}
.organization-tree .boss img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
}
.organization-tree .boss b,
.organization-tree .boss small {
  display: block;
}
.organization-tree .groups {
  flex: 1;
  align-items: stretch;
}
.organization-tree .groups .org-group-card {
  display: flex;
  flex-direction: column;
  min-height: 250px;
  padding: 13px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}
.organization-tree .groups .org-group-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(54, 95, 144, 0.12);
}
.organization-tree .groups .org-group-card.selected {
  border-color: #3d8bfd;
  background: linear-gradient(180deg, #f4f9ff 0%, #fff 44%);
  box-shadow: 0 0 0 3px rgba(64, 149, 244, 0.12), 0 8px 18px rgba(54, 95, 144, 0.1);
}
.organization-tree .groups .org-group-card.c1.selected {
  border-color: #8a5de6;
  box-shadow: 0 0 0 3px rgba(138, 93, 230, 0.12), 0 8px 18px rgba(54, 95, 144, 0.1);
}
.organization-tree .groups .org-group-card.c2.selected {
  border-color: #f18731;
  box-shadow: 0 0 0 3px rgba(241, 135, 49, 0.12), 0 8px 18px rgba(54, 95, 144, 0.1);
}
.org-group-card:focus {
  outline: none;
}
.org-group-card:focus-visible {
  box-shadow: 0 0 0 3px rgba(64, 149, 244, 0.22);
}
.show-all {
  padding: 2px 0;
  border: 0;
  color: #5b7fae;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
}
.show-all:hover {
  color: #287fe8;
}
.org-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px dashed #dce5f0;
}
.org-group-title b {
  font-size: 16px;
}
.org-group-title span {
  color: #78879a;
  font-size: 12px;
}
.org-leader {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0 9px;
}
.org-leader img,
.org-member img {
  border-radius: 50%;
  object-fit: cover;
}
.org-leader img {
  width: 36px;
  height: 36px;
}
.org-leader b,
.org-leader small,
.org-member b,
.org-member small {
  display: block;
}
.org-leader small,
.org-member small {
  margin-top: 2px;
  color: #7c8b9d;
  font-size: 11px;
}
.org-member-tree {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: space-evenly;
  margin: 0 0 0 17px;
  padding: 1px 0 1px 15px;
  border-left: 1px solid #bdd0ea;
}
.org-member {
  position: relative;
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 39px;
}
.org-member > i {
  position: absolute;
  left: -16px;
  top: 50%;
  width: 13px;
  border-top: 1px solid #bdd0ea;
}
.org-member > i::after {
  content: "";
  position: absolute;
  right: -2px;
  top: -3px;
  width: 5px;
  height: 5px;
  border: 1px solid #8eb6e7;
  border-radius: 50%;
  background: #fff;
}
.org-member img {
  width: 27px;
  height: 27px;
}
@media (max-width: 900px) {
  .task-overview-groups {
    grid-template-columns: 1fr;
  }
  .task-overview-groups:before,
  .overview-branch {
    display: none;
  }
  .task-overview-groups article {
    margin-top: 0;
  }
  .overview-robot {
    right: -40px;
  }
}
</style>
