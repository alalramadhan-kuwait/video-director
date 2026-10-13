"""Ledger: budgets, approvals, spend and an append-only audit log in one SQLite file (kept outside git)."""
from __future__ import annotations
import json, secrets, sqlite3, time

SCHEMA = '''
create table if not exists audit(id integer primary key, at real, actor text, action text, project text, detail text);
create table if not exists budgets(project text, provider text, limit_units integer, unit text, primary key(project, provider));
create table if not exists approvals(id text primary key, plan_hash text, project text, provider text, max_units integer,
                                     by text, created real, expires real, used real);
create table if not exists spend(id integer primary key, at real, project text, provider text, units integer, unit text,
                                 plan_hash text, take text, note text);
'''


class Ledger:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path))
        self.db.executescript(SCHEMA)

    def audit(self, actor, action, project='', **detail):
        self.db.execute('insert into audit(at, actor, action, project, detail) values (?,?,?,?,?)',
                        (time.time(), actor, action, project, json.dumps(detail, ensure_ascii=False)))
        self.db.commit()

    def set_budget(self, project, provider, limit_units, unit='characters', by='owner'):
        self.db.execute('insert or replace into budgets values (?,?,?,?)', (project, provider, limit_units, unit))
        self.db.commit(); self.audit(by, 'set_budget', project, provider=provider, limit=limit_units, unit=unit)

    def spent(self, project, provider):
        return self.db.execute('select coalesce(sum(units),0) from spend where project=? and provider=?',
                               (project, provider)).fetchone()[0]

    def remaining(self, project, provider):
        row = self.db.execute('select limit_units from budgets where project=? and provider=?', (project, provider)).fetchone()
        return None if row is None else row[0] - self.spent(project, provider)

    def create_approval(self, plan_hash, project, provider, max_units, by, ttl_s=24 * 3600):
        aid = 'ap_' + secrets.token_hex(8)
        now = time.time()
        self.db.execute('insert into approvals values (?,?,?,?,?,?,?,?,?)',
                        (aid, plan_hash, project, provider, max_units, by, now, now + ttl_s, None))
        self.db.commit(); self.audit(by, 'approve_plan', project, approval=aid, plan_hash=plan_hash, max_units=max_units)
        return aid

    def approval(self, aid):
        r = self.db.execute('select id, plan_hash, project, provider, max_units, by, created, expires, used from approvals where id=?',
                            (aid,)).fetchone()
        return None if r is None else dict(zip(('id', 'plan_hash', 'project', 'provider', 'max_units', 'by', 'created', 'expires', 'used'), r))

    def consume_approval(self, aid):
        """Atomically mark an approval used; returns False if it was already used."""
        cur = self.db.execute('update approvals set used=? where id=? and used is null', (time.time(), aid))
        self.db.commit()
        return cur.rowcount == 1

    def record_spend(self, project, provider, units, unit, plan_hash, take, note=''):
        self.db.execute('insert into spend(at, project, provider, units, unit, plan_hash, take, note) values (?,?,?,?,?,?,?,?)',
                        (time.time(), project, provider, units, unit, plan_hash, take, note))
        self.db.commit()

    def audit_rows(self, action=None):
        q = 'select actor, action, project, detail from audit' + (' where action=?' if action else '') + ' order by id'
        return [dict(zip(('actor', 'action', 'project', 'detail'), r)) for r in self.db.execute(q, (action,) if action else ())]
