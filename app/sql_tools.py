"""Read-only SQL with parsed statements plus an SQLite authorizer and limits."""
from __future__ import annotations
import sqlite3
import math
import time
from pathlib import Path
import sqlglot
from sqlglot import exp

FORBIDDEN_FUNCTIONS = {'load_extension', 'readfile', 'writefile', 'fts3_tokenizer'}

def query_readonly(db_path: Path, sql: str, max_rows: int = 200, timeout: float = 2.0) -> dict:
    if len(sql)>6000: raise ValueError('查询超过长度限制。')
    try:
        statements=sqlglot.parse(sql, read='sqlite')
    except sqlglot.errors.ParseError as exc:
        raise ValueError('SQL 语法无法解析，请检查字段和 SQLite 方言。') from exc
    if len(statements)!=1 or not isinstance(statements[0],exp.Query):
        raise ValueError('只允许一条 SELECT 查询（可包含 CTE）。')
    tree=statements[0]
    if any(isinstance(x,(exp.Insert,exp.Update,exp.Delete,exp.Create,exp.Drop,exp.Command,exp.Into)) for x in tree.walk()):
        raise ValueError('查询包含不允许的写入或管理操作。')
    if any(x.name.lower() in FORBIDDEN_FUNCTIONS for x in tree.find_all(exp.Func)):
        raise ValueError('不允许文件、扩展或外部访问函数。')
    con=sqlite3.connect(f'file:{db_path.resolve()}?mode=ro',uri=True)
    con.row_factory=sqlite3.Row
    con.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,1_000_000)
    con.setlimit(sqlite3.SQLITE_LIMIT_COLUMN,100)
    con.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH,100)
    con.setlimit(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT,20)
    names={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'")}
    names={n for n in names if 'metadata' not in n and 'runs' not in n}
    ctes={c.alias_or_name for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        if t.name not in names|ctes or t.db or t.catalog:
            con.close(); raise ValueError('查询引用了未开放的数据表。')
    def authorize(action,a,b,c,d):
        if action==sqlite3.SQLITE_READ:
            return sqlite3.SQLITE_OK if a in names else sqlite3.SQLITE_DENY
        if action==sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_DENY if (b or '').lower() in FORBIDDEN_FUNCTIONS else sqlite3.SQLITE_OK
        allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_RECURSIVE}
        return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY
    con.set_authorizer(authorize)
    began=time.monotonic()
    con.set_progress_handler(lambda: int(time.monotonic()-began>timeout),1000)
    try:
        cur=con.execute(sql)
        rows=cur.fetchmany(max_rows+1)
        truncated=len(rows)>max_rows
        for row in rows[:max_rows]:
            for value in row:
                if isinstance(value,bytes) or isinstance(value,float) and not math.isfinite(value):
                    raise ValueError('查询结果包含二进制或非有限数字，无法作为分析指标；请转换为文本或有限数值。')
        return {'sql':sql,'columns':[x[0] for x in cur.description or []], 'rows':[dict(r) for r in rows[:max_rows]],'row_count':min(len(rows),max_rows),'truncated':truncated,'duration_ms':round((time.monotonic()-began)*1000,2),'source':'固定种子合成演示数据库','read_only':True}
    except sqlite3.Error as exc:
        message='查询超时或被只读策略拒绝。' if 'interrupted' in str(exc) or 'authorized' in str(exc) else 'SQL 执行失败，请核对列名、函数和分组。'
        raise ValueError(message) from exc
    finally: con.close()
