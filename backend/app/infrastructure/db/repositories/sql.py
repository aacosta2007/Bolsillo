"""Repositorios SQLAlchemy. Las agregaciones se resuelven en SQL."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, delete, func, literal, or_, select, union_all, update
from sqlalchemy.orm import aliased

from app.domain.entities import (
    Account,
    Budget,
    Category,
    CategoryTotal,
    Contribution,
    ExportRow,
    Goal,
    MonthlyTotal,
    RecurringRule,
    RefreshToken,
    Transaction,
    TransactionFilters,
    User,
)
from app.domain.enums import CategoryKind, TransactionType
from app.infrastructure.db.models import (
    AccountModel,
    BudgetModel,
    CategoryModel,
    GoalContributionModel,
    RecurringRuleModel,
    RefreshTokenModel,
    SavingsGoalModel,
    TransactionModel,
    UserModel,
)
from app.infrastructure.db.repositories.base import SqlRepo

T = TransactionModel
ZERO = Decimal("0.00")


def _dec(v) -> Decimal:
    return Decimal(v if v is not None else 0).quantize(Decimal("0.01"))


class SqlUserRepository(SqlRepo[User]):
    model = UserModel
    entity = User
    has_user_id = False

    async def get(self, id: UUID) -> User | None:  # type: ignore[override]
        orm = await self.session.get(UserModel, id)
        return self.to_entity(orm) if orm else None

    async def get_by_email(self, email: str) -> User | None:
        orm = await self.session.scalar(select(UserModel).where(UserModel.email == email))
        return self.to_entity(orm) if orm else None

    async def count(self) -> int:
        return int(await self.session.scalar(select(func.count()).select_from(UserModel)) or 0)

    async def list_all(self) -> list[User]:
        rows = await self.session.scalars(select(UserModel).order_by(UserModel.created_at))
        return [self.to_entity(r) for r in rows]


class SqlRefreshTokenRepository(SqlRepo[RefreshToken]):
    model = RefreshTokenModel
    entity = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        orm = await self.session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        return self.to_entity(orm) if orm else None

    async def revoke(self, id: UUID) -> None:
        await self.session.execute(
            update(RefreshTokenModel).where(RefreshTokenModel.id == id).values(revoked=True)
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self.session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked.is_(False))
            .values(revoked=True)
        )

    async def delete_expired(self, now: datetime) -> None:
        await self.session.execute(
            delete(RefreshTokenModel).where(RefreshTokenModel.expires_at < now.replace(tzinfo=None))
        )


class SqlAccountRepository(SqlRepo[Account]):
    model = AccountModel
    entity = Account

    @staticmethod
    def _balance_stmt(user_id: UUID):
        outgoing = select(
            T.account_id.label("acc"),
            case((T.type == "income", T.amount), else_=-T.amount).label("delta"),
        ).where(T.user_id == user_id)
        incoming = select(T.transfer_account_id.label("acc"), T.amount.label("delta")).where(
            T.user_id == user_id, T.type == "transfer"
        )
        u = union_all(outgoing, incoming).subquery()
        deltas = select(u.c.acc, func.sum(u.c.delta).label("d")).group_by(u.c.acc).subquery()
        return (
            select(
                AccountModel,
                (AccountModel.initial_balance + func.coalesce(deltas.c.d, 0)).label("balance"),
            )
            .outerjoin(deltas, deltas.c.acc == AccountModel.id)
            .where(AccountModel.user_id == user_id)
        )

    def _with_balance(self, orm, balance) -> Account:
        acc = self.to_entity(orm)
        acc.balance = _dec(balance)
        return acc

    async def list(self, user_id: UUID, include_archived: bool) -> list[Account]:
        stmt = self._balance_stmt(user_id)
        if not include_archived:
            stmt = stmt.where(AccountModel.archived.is_(False))
        stmt = stmt.order_by(AccountModel.archived, AccountModel.created_at, AccountModel.name)
        rows = (await self.session.execute(stmt)).all()
        return [self._with_balance(r[0], r[1]) for r in rows]

    async def get(self, user_id: UUID, id: UUID) -> Account | None:
        stmt = self._balance_stmt(user_id).where(AccountModel.id == id)
        row = (await self.session.execute(stmt)).first()
        return self._with_balance(row[0], row[1]) if row else None

    async def has_dependencies(self, user_id: UUID, id: UUID) -> bool:
        tx = await self.session.scalar(
            select(T.id)
            .where(T.user_id == user_id, or_(T.account_id == id, T.transfer_account_id == id))
            .limit(1)
        )
        if tx is not None:
            return True
        rule = await self.session.scalar(
            select(RecurringRuleModel.id)
            .where(RecurringRuleModel.user_id == user_id, RecurringRuleModel.account_id == id)
            .limit(1)
        )
        return rule is not None


class SqlCategoryRepository(SqlRepo[Category]):
    model = CategoryModel
    entity = Category

    async def list(self, user_id: UUID, kind: CategoryKind | None) -> list[Category]:
        stmt = select(CategoryModel).where(CategoryModel.user_id == user_id)
        if kind:
            stmt = stmt.where(CategoryModel.kind == kind.value)
        stmt = stmt.order_by(CategoryModel.kind.desc(), CategoryModel.created_at, CategoryModel.name)
        return [self.to_entity(r) for r in await self.session.scalars(stmt)]

    async def add_many(self, categories: list[Category]) -> None:
        self.session.add_all([CategoryModel(**self.values(c)) for c in categories])
        await self.session.flush()

    async def name_exists(
        self, user_id: UUID, kind: CategoryKind, name: str, exclude_id: UUID | None = None
    ) -> bool:
        stmt = select(CategoryModel.id).where(
            CategoryModel.user_id == user_id,
            CategoryModel.kind == kind.value,
            func.lower(CategoryModel.name) == name.lower(),
        )
        if exclude_id:
            stmt = stmt.where(CategoryModel.id != exclude_id)
        return (await self.session.scalar(stmt.limit(1))) is not None

    async def in_use(self, user_id: UUID, id: UUID) -> bool:
        for model in (T, BudgetModel, RecurringRuleModel):
            found = await self.session.scalar(
                select(model.id).where(model.user_id == user_id, model.category_id == id).limit(1)
            )
            if found is not None:
                return True
        return False


class SqlTransactionRepository(SqlRepo[Transaction]):
    model = TransactionModel
    entity = Transaction

    @staticmethod
    def _where(user_id: UUID, f: TransactionFilters) -> list:
        conds = [T.user_id == user_id]
        if f.date_from:
            conds.append(T.date >= f.date_from)
        if f.date_to:
            conds.append(T.date <= f.date_to)
        if f.account_id:
            conds.append(or_(T.account_id == f.account_id, T.transfer_account_id == f.account_id))
        if f.category_id:
            conds.append(T.category_id == f.category_id)
        if f.type:
            conds.append(T.type == f.type.value)
        if f.q:
            conds.append(T.note.icontains(f.q, autoescape=True))
        return conds

    async def list(
        self, user_id: UUID, filters: TransactionFilters, page: int, page_size: int
    ) -> tuple[list[Transaction], int]:
        conds = self._where(user_id, filters)
        total = int(await self.session.scalar(select(func.count()).select_from(T).where(*conds)) or 0)
        stmt = (
            select(T)
            .where(*conds)
            .order_by(T.date.desc(), T.created_at.desc(), T.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return [self.to_entity(r) for r in await self.session.scalars(stmt)], total

    async def totals(self, user_id: UUID, start: date, end: date) -> tuple[Decimal, Decimal]:
        stmt = select(
            func.coalesce(func.sum(case((T.type == "income", T.amount), else_=0)), 0),
            func.coalesce(func.sum(case((T.type == "expense", T.amount), else_=0)), 0),
        ).where(T.user_id == user_id, T.date >= start, T.date <= end)
        row = (await self.session.execute(stmt)).one()
        return _dec(row[0]), _dec(row[1])

    async def category_totals(
        self, user_id: UUID, start: date, end: date, type: TransactionType
    ) -> list[CategoryTotal]:
        total = func.sum(T.amount)
        stmt = (
            select(
                CategoryModel.id,
                CategoryModel.name,
                CategoryModel.color,
                CategoryModel.icon,
                total.label("total"),
                func.count(T.id).label("cnt"),
            )
            .join(CategoryModel, CategoryModel.id == T.category_id)
            .where(T.user_id == user_id, T.type == type.value, T.date >= start, T.date <= end)
            .group_by(CategoryModel.id, CategoryModel.name, CategoryModel.color, CategoryModel.icon)
            .order_by(total.desc(), CategoryModel.name)
        )
        return [
            CategoryTotal(
                category_id=r[0], name=r[1], color=r[2], icon=r[3], total=_dec(r[4]), count=int(r[5])
            )
            for r in (await self.session.execute(stmt)).all()
        ]

    async def spent_by_category(self, user_id: UUID, start: date, end: date) -> dict[UUID, Decimal]:
        stmt = (
            select(T.category_id, func.sum(T.amount))
            .where(T.user_id == user_id, T.type == "expense", T.date >= start, T.date <= end)
            .group_by(T.category_id)
        )
        return {r[0]: _dec(r[1]) for r in (await self.session.execute(stmt)).all()}

    async def monthly_totals(self, user_id: UUID, start: date, end: date) -> list[MonthlyTotal]:
        ym = func.date_format(T.date, "%Y-%m")
        stmt = (
            select(
                ym.label("ym"),
                func.sum(case((T.type == "income", T.amount), else_=0)),
                func.sum(case((T.type == "expense", T.amount), else_=0)),
            )
            .where(T.user_id == user_id, T.type != "transfer", T.date >= start, T.date <= end)
            .group_by(ym)
            .order_by(ym)
        )
        out = []
        for ym_v, inc, exp in (await self.session.execute(stmt)).all():
            y, m = ym_v.split("-")
            out.append(MonthlyTotal(month=date(int(y), int(m), 1), income=_dec(inc), expense=_dec(exp)))
        return out

    async def recent(self, user_id: UUID, limit: int) -> list[Transaction]:
        stmt = (
            select(T)
            .where(T.user_id == user_id)
            .order_by(T.date.desc(), T.created_at.desc(), T.id)
            .limit(limit)
        )
        return [self.to_entity(r) for r in await self.session.scalars(stmt)]

    async def export_rows(self, user_id: UUID, start: date, end: date) -> list[ExportRow]:
        src = aliased(AccountModel)
        dst = aliased(AccountModel)
        stmt = (
            select(T.date, T.type, T.amount, src.name, CategoryModel.name, dst.name, T.note)
            .join(src, src.id == T.account_id)
            .outerjoin(dst, dst.id == T.transfer_account_id)
            .outerjoin(CategoryModel, CategoryModel.id == T.category_id)
            .where(T.user_id == user_id, T.date >= start, T.date <= end)
            .order_by(T.date, T.created_at, T.id)
        )
        return [
            ExportRow(
                date=r[0], type=TransactionType(r[1]), amount=_dec(r[2]), account=r[3],
                category=r[4], transfer_account=r[5], note=r[6],
            )
            for r in (await self.session.execute(stmt)).all()
        ]


class SqlBudgetRepository(SqlRepo[Budget]):
    model = BudgetModel
    entity = Budget

    async def list_for_month(self, user_id: UUID, month: date) -> list[Budget]:
        stmt = (
            select(BudgetModel)
            .where(BudgetModel.user_id == user_id, BudgetModel.month == month)
            .order_by(BudgetModel.created_at, BudgetModel.id)
        )
        return [self.to_entity(r) for r in await self.session.scalars(stmt)]

    async def find(self, user_id: UUID, category_id: UUID, month: date) -> Budget | None:
        orm = await self.session.scalar(
            select(BudgetModel).where(
                BudgetModel.user_id == user_id,
                BudgetModel.category_id == category_id,
                BudgetModel.month == month,
            )
        )
        return self.to_entity(orm) if orm else None


class SqlRecurringRepository(SqlRepo[RecurringRule]):
    model = RecurringRuleModel
    entity = RecurringRule

    async def list(self, user_id: UUID) -> list[RecurringRule]:
        stmt = (
            select(RecurringRuleModel)
            .where(RecurringRuleModel.user_id == user_id)
            .order_by(RecurringRuleModel.next_run_date, RecurringRuleModel.created_at)
        )
        return [self.to_entity(r) for r in await self.session.scalars(stmt)]

    async def lock_due(self, user_id: UUID, today: date) -> list[RecurringRule]:
        # next_run_date es nominal: con ajuste de fin de semana la fecha efectiva puede ser hasta
        # 2 días anterior, así que se traen con holgura y el servicio decide con la fecha efectiva.
        stmt = (
            select(RecurringRuleModel)
            .where(
                RecurringRuleModel.user_id == user_id,
                RecurringRuleModel.active.is_(True),
                RecurringRuleModel.next_run_date <= today + timedelta(days=2),
            )
            .order_by(RecurringRuleModel.next_run_date, RecurringRuleModel.id)
            .with_for_update()
        )
        return [self.to_entity(r) for r in await self.session.scalars(stmt)]


class SqlGoalRepository(SqlRepo[Goal]):
    model = SavingsGoalModel
    entity = Goal

    @staticmethod
    def _stmt(user_id: UUID):
        saved = (
            select(
                GoalContributionModel.goal_id.label("gid"),
                func.sum(GoalContributionModel.amount).label("s"),
            )
            .where(GoalContributionModel.user_id == user_id)
            .group_by(GoalContributionModel.goal_id)
            .subquery()
        )
        return (
            select(SavingsGoalModel, func.coalesce(saved.c.s, 0))
            .outerjoin(saved, saved.c.gid == SavingsGoalModel.id)
            .where(SavingsGoalModel.user_id == user_id)
        )

    def _goal(self, orm, saved) -> Goal:
        g = self.to_entity(orm)
        g.saved = _dec(saved)
        return g

    async def list(self, user_id: UUID) -> list[Goal]:
        stmt = self._stmt(user_id).order_by(SavingsGoalModel.created_at, SavingsGoalModel.id)
        return [self._goal(r[0], r[1]) for r in (await self.session.execute(stmt)).all()]

    async def get(self, user_id: UUID, id: UUID) -> Goal | None:
        row = (await self.session.execute(self._stmt(user_id).where(SavingsGoalModel.id == id))).first()
        return self._goal(row[0], row[1]) if row else None

    async def list_contributions(self, user_id: UUID, goal_id: UUID) -> list[Contribution]:
        stmt = (
            select(GoalContributionModel)
            .where(GoalContributionModel.user_id == user_id, GoalContributionModel.goal_id == goal_id)
            .order_by(GoalContributionModel.date.desc(), GoalContributionModel.created_at.desc())
        )
        return [self._contribution(r) for r in await self.session.scalars(stmt)]

    def _contribution(self, orm) -> Contribution:
        return Contribution(
            id=orm.id, user_id=orm.user_id, goal_id=orm.goal_id, amount=_dec(orm.amount),
            date=orm.date, note=orm.note, created_at=orm.created_at, updated_at=orm.updated_at,
        )

    async def get_contribution(self, user_id: UUID, goal_id: UUID, id: UUID) -> Contribution | None:
        orm = await self.session.scalar(
            select(GoalContributionModel).where(
                GoalContributionModel.id == id,
                GoalContributionModel.user_id == user_id,
                GoalContributionModel.goal_id == goal_id,
            )
        )
        return self._contribution(orm) if orm else None

    async def add_contribution(self, c: Contribution) -> Contribution:
        self.session.add(
            GoalContributionModel(
                id=c.id, user_id=c.user_id, goal_id=c.goal_id, amount=c.amount, date=c.date,
                note=c.note, created_at=c.created_at, updated_at=c.updated_at,
            )
        )
        await self.session.flush()
        return c

    async def delete_contribution(self, user_id: UUID, id: UUID) -> None:
        await self.session.execute(
            delete(GoalContributionModel).where(
                GoalContributionModel.id == id, GoalContributionModel.user_id == user_id
            )
        )
        await self.session.flush()
