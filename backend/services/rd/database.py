"""数据库实例引用 — 打破循环导入.

main.py 调用 init_db() 注入实例，其他模块从本文件导入 db。
"""
db = None


def init_db(database):
    global db
    db = database
