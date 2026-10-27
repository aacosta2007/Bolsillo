"""Repositorios fake en memoria para probar los servicios sin base de datos."""
from __future__ import annotations

from copy import copy
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.domain.entities import (
    Account,
    Budget,
    Category,
    CategoryTotal,
    Contribution,
    Goal,
    Notification,
    PushSubscription,
    RecurringRule,
    Transaction,
    User,
)
from app.application.ports import PushResult, PushTarget


class _Repo:
    def __init__(self):
        self.items: dict[UUID, object] = {}

    async def get(self, user_id, id):
        item = self.items.get(id)
        return copy(item) if item is not None and item.user_id == user_id else None

    async def add(self, e):
        self.items[e.id] = copy(e)
        return e

    async def update(self, e):
        self.items[e.id] = copy(e)
        return e

    async def delete(self, user_id, id):
        self.items.pop(id, None)

    def _all(self, user_id):
        return [copy(i) for i in self.items.values() if i.user_id == user_id]


class FakeUsers:
    def __init__(self):
        self.items: dict[UUID, User] = {}

    async def get(self, id):
        return self.items.get(id)

    async def get_by_email(self, email):
        return next((u for u in self.items.values() if u.email == email), None)

    async def add(self, u):
        self.items[u.id] = u
        return u

    async def update(self, u):
        self.items[u.id] = u
        return u

    async def count(self):
        return len(self.items)

    async def list_all(self):
        return list(self.items.values())


class FakeAccounts(_Repo):
    async def list(self, user_id, include_archived):
        return [a for a in self._all(user_id) if include_archived or not a.archived]

    async def has_dependencies(self, user_id, id):
        return False


class FakeCategories(_Repo):
    async def list(self, user_id, kind):
        return [c for c in self._all(user_id) if kind is None or c.kind == kind]

    async def add_many(self, cats):
        for c in cats:
            await self.add(c)

    async def name_exists(self, user_id, kind, name, exclude_id=None):
        return any(
            c.kind == kind and c.name.lower() == name.lower() and c.id != exclude_id
            for c in self._all(user_id)
        )

    async def in_use(self, user_id, id):
        return False


class FakeTransactions(_Repo):
    categories: "FakeCategories"
    recurring: "FakeRecurring"

    async def spent_by_category(self, user_id, start: date, end: date):
        out: dict[UUID, Decimal] = {}
        for t in self._all(user_id):
            if t.type.value == "expense" and start <= t.date <= end:
                out[t.category_id] = out.get(t.category_id, Decimal("0.00")) + t.amount
        return out

    async def list(self, user_id, filters, page, page_size):
        out = [
            t for t in self._all(user_id)
            if (filters.date_from is None or t.date >= filters.date_from)
            and (filters.date_to is None or t.date <= filters.date_to)
        ]
        return out, len(out)

    def all(self) -> list[Transaction]:
        return list(self.items.values())

    # ---- agregaciones usadas por los reportes (misma semántica que el repositorio SQL) ----
    async def totals(self, user_id, start: date, end: date):
        inc = sum((t.amount for t in self._all(user_id) if t.type.value == "income" and start <= t.date <= end), Decimal(0))
        exp = sum((t.amount for t in self._all(user_id) if t.type.value == "expense" and start <= t.date <= end), Decimal(0))
        return inc, exp

    async def category_totals(self, user_id, start: date, end: date, type):
        out: dict[UUID, list] = {}
        for t in self._all(user_id):
            if t.type == type and start <= t.date <= end:
                out.setdefault(t.category_id, []).append(t.amount)
        cats = {c.id: c for c in await self.categories.list(user_id, None)}
        rows = [
            CategoryTotal(category_id=cid, name=cats[cid].name, color=cats[cid].color, icon=cats[cid].icon,
                          total=sum(v, Decimal(0)), count=len(v))
            for cid, v in out.items()
        ]
        return sorted(rows, key=lambda r: -r.total)

    def _is_salary(self, user_id, t) -> bool:
        if t.type.value != "income":
            return False
        rules = [r for r in self.recurring._all(user_id) if r.is_paycheck]
        return t.recurring_id in {r.id for r in rules} or t.category_id in {r.category_id for r in rules if r.active}

    async def salary_total(self, user_id, start: date, end: date):
        return sum((t.amount for t in self._all(user_id) if self._is_salary(user_id, t) and start <= t.date <= end), Decimal(0))

    async def salary_dates(self, user_id, until: date):
        return sorted({t.date for t in self._all(user_id) if self._is_salary(user_id, t) and t.date <= until})


class FakeBudgets(_Repo):
    async def list_for_month(self, user_id, month):
        return [b for b in self._all(user_id) if b.month == month]

    async def find(self, user_id, category_id, month):
        return next(
            (b for b in self._all(user_id) if b.category_id == category_id and b.month == month), None
        )


class FakeRecurring(_Repo):
    async def list(self, user_id):
        return self._all(user_id)

    async def lock_due(self, user_id, today):
        return [r for r in self._all(user_id) if r.active and r.next_run_date <= today + timedelta(days=2)]


class FakeGoals(_Repo):
    def __init__(self):
        super().__init__()
        self.contribs: dict[UUID, Contribution] = {}

    def _saved(self, goal_id):
        return sum((c.amount for c in self.contribs.values() if c.goal_id == goal_id), Decimal("0.00"))

    async def get(self, user_id, id):
        g = await super().get(user_id, id)
        if g:
            g.saved = self._saved(id)
        return g

    async def list(self, user_id):
        out = self._all(user_id)
        for g in out:
            g.saved = self._saved(g.id)
        return out

    async def list_contributions(self, user_id, goal_id):
        return [c for c in self.contribs.values() if c.goal_id == goal_id]

    async def get_contribution(self, user_id, goal_id, id):
        c = self.contribs.get(id)
        return c if c and c.goal_id == goal_id else None

    async def add_contribution(self, c):
        self.contribs[c.id] = c
        return c

    async def delete_contribution(self, user_id, id):
        self.contribs.pop(id, None)


class FakeNotifications:
    def __init__(self):
        self.items: list[Notification] = []

    async def try_add(self, n):
        if any(i.user_id == n.user_id and i.dedupe_key == n.dedupe_key for i in self.items):
            return False
        self.items.append(copy(n))
        return True

    async def get(self, user_id, id):
        return next((i for i in self.items if i.id == id and i.user_id == user_id), None)

    async def list(self, user_id, unread_only, page, page_size):
        rows = [i for i in reversed(self.items) if i.user_id == user_id and (not unread_only or not i.read)]
        return rows[(page - 1) * page_size: page * page_size], len(rows)

    async def unread_count(self, user_id):
        return sum(1 for i in self.items if i.user_id == user_id and not i.read)

    async def mark_read(self, user_id, id):
        for i in self.items:
            if i.id == id and i.user_id == user_id:
                i.read = True

    async def mark_all_read(self, user_id):
        for i in self.items:
            if i.user_id == user_id:
                i.read = True


class FakePushSubscriptions:
    def __init__(self):
        self.items: dict[str, PushSubscription] = {}

    async def upsert(self, sub):
        old = self.items.get(sub.endpoint)
        if old:
            old.user_id, old.p256dh, old.auth, old.device = sub.user_id, sub.p256dh, sub.auth, sub.device
            return old
        self.items[sub.endpoint] = copy(sub)
        return sub

    async def list_for_user(self, user_id):
        return [copy(s) for s in self.items.values() if s.user_id == user_id]

    async def delete_by_endpoint(self, user_id, endpoint):
        s = self.items.get(endpoint)
        if s and s.user_id == user_id:
            del self.items[endpoint]

    async def delete(self, id):
        for k, v in list(self.items.items()):
            if v.id == id:
                del self.items[k]


class FakePushSender:
    """Registra los envíos; `results` define la respuesta por endpoint (por defecto OK)."""

    enabled = True

    def __init__(self, results: dict | None = None):
        self.sent: list[tuple[PushTarget, dict]] = []
        self.results = results or {}

    async def send(self, target, payload):
        self.sent.append((target, payload))
        return self.results.get(target.endpoint, PushResult.OK)


class FakeUoW:
    def __init__(self):
        self.users = FakeUsers()
        self.accounts = FakeAccounts()
        self.categories = FakeCategories()
        self.transactions = FakeTransactions()
        self.budgets = FakeBudgets()
        self.recurring = FakeRecurring()
        self.goals = FakeGoals()
        self.notifications = FakeNotifications()
        self.push_subscriptions = FakePushSubscriptions()
        self.commits = 0
        self.transactions.categories = self.categories
        self.transactions.recurring = self.recurring

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


async def seed(uow: FakeUoW):
    """Usuario + cuenta + categorías de gasto/ingreso."""
    from app.domain.enums import AccountType, CategoryKind

    user = User(email="a@b.co", password_hash="x")
    await uow.users.add(user)
    acc = Account(user_id=user.id, name="Banco", type=AccountType.BANK)
    acc2 = Account(user_id=user.id, name="Ahorros", type=AccountType.SAVINGS)
    await uow.accounts.add(acc)
    await uow.accounts.add(acc2)
    expense = Category(user_id=user.id, name="Comida", kind=CategoryKind.EXPENSE)
    income = Category(user_id=user.id, name="Salario", kind=CategoryKind.INCOME)
    await uow.categories.add(expense)
    await uow.categories.add(income)
    return user, acc, acc2, expense, income


__all__ = ["FakeUoW", "seed", "Budget", "Goal", "RecurringRule"]
