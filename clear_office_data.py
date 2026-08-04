# -*- coding: utf-8 -*-
"""清空智慧办公的会议与公文测试数据（保留组织成员与公文模板）。

清理范围：
  - office_meetings / office_action_items            会议与行动项
  - office_documents / office_document_receipts      公文与收文回执
  - office_approvals                                 审批单
  - office_schedules                                 仅删关联会议/公文/行动项的日程，保留个人日程
  - office_notifications                             仅删会议/行动项/审批/公文类通知，保留组织类通知

用法：backend/.venv 的 python 运行，如
  backend/.venv/Scripts/python.exe clear_office_data.py [all|meetings|docs]
    all      会议 + 公文（默认）
    meetings 仅会议与行动项
    docs     仅公文与审批
"""
import os
import sys
from urllib.parse import urlparse

import pymysql
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, 'backend', '.env'))


def conn_params():
    base = dict(host=os.getenv('MYSQL_HOST', 'localhost'),
                port=int(os.getenv('MYSQL_PORT', '3306')),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database='weagent_office')
    url = os.getenv('OFFICE_DATABASE_URL')
    if url:
        u = urlparse(url.replace('mysql+pymysql://', 'mysql://'))
        # 以 MYSQL_* 为兜底，只覆盖 URL 中明确提供的字段
        if u.hostname:
            base['host'] = u.hostname
        if u.port:
            base['port'] = u.port
        if u.username:
            base['user'] = u.username
        if u.password:
            base['password'] = u.password
        if u.path and u.path != '/':
            base['database'] = u.path.lstrip('/')
    return base


MEETING_TABLES = [
    'office_action_items',
    'office_meetings',
]

DOC_TABLES = [
    'office_document_receipts',
    'office_approvals',
    'office_documents',
]

MEETING_NOTIFY_TYPES = ('meeting_invitation', 'meeting_updated', 'action_item')

DOC_NOTIFY_TYPES = ('approval', 'approval_result', 'document_delivery')


def main():
    scope = (sys.argv[1] if len(sys.argv) > 1 else 'all').strip().lower()
    if scope not in ('all', 'meetings', 'docs'):
        print('用法: clear_office_data.py [all|meetings|docs]')
        return 2
    tables = {'all': MEETING_TABLES + DOC_TABLES,
              'meetings': MEETING_TABLES,
              'docs': DOC_TABLES}[scope]
    notify_types = {'all': MEETING_NOTIFY_TYPES + DOC_NOTIFY_TYPES,
                    'meetings': MEETING_NOTIFY_TYPES,
                    'docs': DOC_NOTIFY_TYPES}[scope]
    schedule_col = {'all': 'meeting_id IS NOT NULL OR document_id IS NOT NULL OR action_item_id IS NOT NULL',
                    'meetings': 'meeting_id IS NOT NULL OR action_item_id IS NOT NULL',
                    'docs': 'document_id IS NOT NULL'}[scope]

    params = conn_params()
    print('connect: %s@%s:%s/%s  scope=%s' % (params['user'], params['host'], params['port'], params['database'], scope))
    conn = pymysql.connect(charset='utf8mb4', **params)
    try:
        with conn.cursor() as cur:
            def count(table):
                cur.execute('SELECT COUNT(*) FROM %s' % table)
                return cur.fetchone()[0]

            watched = tables + ['office_schedules', 'office_notifications']
            before = {t: count(t) for t in watched}

            cur.execute('SET FOREIGN_KEY_CHECKS=0')
            for t in tables:
                cur.execute('DELETE FROM %s' % t)
            cur.execute('DELETE FROM office_schedules WHERE ' + schedule_col)
            cur.execute(
                'DELETE FROM office_notifications WHERE notification_type IN (%s)'
                % ','.join("'%s'" % t for t in notify_types)
            )
            cur.execute('SET FOREIGN_KEY_CHECKS=1')
        conn.commit()

        with conn.cursor() as cur:
            def count(table):
                cur.execute('SELECT COUNT(*) FROM %s' % table)
                return cur.fetchone()[0]
            print('\n表清理结果：')
            for t in watched:
                print('  %-28s %d -> %d' % (t, before[t], count(t)))
        print('\n完成：%s数据已清空，组织成员与公文模板保留。' % {'all': '会议与公文', 'meetings': '会议', 'docs': '公文'}[scope])
    finally:
        conn.close()


if __name__ == '__main__':
    main()
