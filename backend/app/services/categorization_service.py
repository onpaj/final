import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category, CategoryGroup, LlmClassification, Rule, Transaction
from app.services.parsers.base import TransactionRow
from app.services.rules_engine import RulesEngine
from app.services.anthropic_client import AnthropicClient, CONFIDENCE_THRESHOLD, AnthropicClassificationError


class CategorizationService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._llm = AnthropicClient()

    async def _load_rules(self) -> list[dict]:
        result = await self._db.execute(
            select(Rule).where(Rule.enabled == True).order_by(Rule.priority.desc())
        )
        rules = result.scalars().all()
        return [
            {
                "id": r.id,
                "match_type": r.match_type,
                "match_value": r.match_value,
                "category_id": r.category_id,
                "priority": r.priority,
                "enabled": r.enabled,
            }
            for r in rules
        ]

    async def _load_categories(self) -> list[tuple[str, str, str | None]]:
        result = await self._db.execute(
            select(CategoryGroup.name, Category.name, Category.hint)
            .join(CategoryGroup, Category.group_id == CategoryGroup.id)
            .order_by(CategoryGroup.sort_order, Category.sort_order)
        )
        return [(row[0], row[1], row[2]) for row in result.all()]

    async def _categorize_one(self, tx: Transaction, rules: list[dict], categories: list[tuple[str, str, str | None]]) -> None:
        row = TransactionRow(
            booking_date=tx.booking_date,
            value_date=tx.value_date,
            amount=tx.amount,
            currency=tx.currency,
            counterparty_name=tx.counterparty_name,
            counterparty_account=tx.counterparty_account,
            description=tx.description,
            raw_reference=tx.raw_reference,
        )

        match = RulesEngine.apply(row, rules)
        if match:
            tx.category_id = match.category_id
            tx.categorization_source = "rule"
            tx.confidence = Decimal("1.0")
            rule_obj = await self._db.get(Rule, match.rule_id)
            if rule_obj:
                rule_obj.hit_count += 1
                rule_obj.last_hit_at = datetime.now(timezone.utc)
            return

        await self._apply_llm(tx, categories)

    async def _apply_llm(self, tx: Transaction, categories: list[tuple[str, str, str | None]]) -> None:
        try:
            result = await asyncio.to_thread(
                self._llm.classify,
                counterparty=tx.counterparty_name,
                description=tx.description,
                amount=tx.amount,
                categories=categories,
            )
        except AnthropicClassificationError:
            # Log error so Review page can distinguish from "never tried"
            error_log = LlmClassification(
                transaction_id=tx.id,
                model="unknown",
                suggested_category_id=None,
                accepted=False,
                confidence=None,
                reasoning="error",
                prompt_tokens=None,
                completion_tokens=None,
            )
            self._db.add(error_log)
            return

        # LLM returns "GroupName__CategoryName" — look up by both group and category name
        raw = result.category_name
        if "__" in raw:
            group_name, cat_name = raw.split("__", 1)
            cat_result = await self._db.execute(
                select(Category)
                .join(CategoryGroup, Category.group_id == CategoryGroup.id)
                .where(CategoryGroup.name == group_name, Category.name == cat_name)
                .limit(1)
            )
        else:
            cat_result = await self._db.execute(
                select(Category).where(Category.name == raw).limit(1)
            )
        category = cat_result.scalars().first()

        accepted = result.confidence >= CONFIDENCE_THRESHOLD and category is not None
        log = LlmClassification(
            transaction_id=tx.id,
            model=result.model,
            suggested_category_id=category.id if category else None,
            accepted=accepted,
            confidence=result.confidence,
            reasoning=result.reasoning,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
        self._db.add(log)

        if accepted:
            tx.category_id = category.id
            tx.categorization_source = "llm"
            tx.confidence = result.confidence

    async def _categorize_one_rules_only(self, tx: Transaction, rules: list[dict]) -> None:
        row = TransactionRow(
            booking_date=tx.booking_date,
            value_date=tx.value_date,
            amount=tx.amount,
            currency=tx.currency,
            counterparty_name=tx.counterparty_name,
            counterparty_account=tx.counterparty_account,
            description=tx.description,
            raw_reference=tx.raw_reference,
        )
        match = RulesEngine.apply(row, rules)
        if match:
            tx.category_id = match.category_id
            tx.categorization_source = "rule"
            tx.confidence = Decimal("1.0")
            rule_obj = await self._db.get(Rule, match.rule_id)
            if rule_obj:
                rule_obj.hit_count += 1
                rule_obj.last_hit_at = datetime.now(timezone.utc)

    async def _categorize_one_llm_only(self, tx: Transaction, categories: list[tuple[str, str, str | None]]) -> None:
        await self._apply_llm(tx, categories)

    async def run_batch(self, transaction_ids: list) -> dict:
        result = await self._db.execute(
            select(Transaction).where(Transaction.id.in_(transaction_ids))
        )
        transactions = result.scalars().all()
        rules = await self._load_rules()
        categories = await self._load_categories()

        categorized = 0
        needs_review = 0
        for tx in transactions:
            if tx.category_id is not None:
                continue
            await self._categorize_one(tx, rules, categories)
            if tx.category_id is not None:
                categorized += 1
            else:
                needs_review += 1

        await self._db.commit()
        return {"categorized": categorized, "needs_review": needs_review}
