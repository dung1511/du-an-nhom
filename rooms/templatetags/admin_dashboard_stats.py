from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django import template
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.db.models.functions import Coalesce
from rooms.models import Reservation

register = template.Library()


def _money_expr() -> Case:
    # Prefer final_total when available (checkout/damage adjustments), else fallback to total.
    return Case(
        When(final_total__gt=0, then=F("final_total")),
        default=F("total"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )


def _month_start(current: date) -> date:
    return current.replace(day=1)


def _next_month(current: date) -> date:
    if current.month == 12:
        return current.replace(year=current.year + 1, month=1, day=1)
    return current.replace(month=current.month + 1, day=1)


def _quarter_start(current: date) -> date:
    quarter_month = ((current.month - 1) // 3) * 3 + 1
    return current.replace(month=quarter_month, day=1)


def _format_currency(amount: Decimal) -> str:
    return f"{amount:,.0f}".replace(",", ".") + " VND"


def _resolve_period(context: dict) -> dict:
    request = context.get("request")
    today = date.today()

    period_key = "30d"
    if request:
        period_key = (request.GET.get("period") or "30d").lower().strip()

    if period_key == "7d":
        start_date = today - timedelta(days=6)
        label = "7 ngay gan day"
    elif period_key == "qtd":
        start_date = _quarter_start(today)
        label = "Quy nay"
    else:
        period_key = "30d"
        start_date = today - timedelta(days=29)
        label = "30 ngay gan day"

    return {
        "key": period_key,
        "start_date": start_date,
        "end_date": today,
        "label": label,
    }


def _sum_amount(qs):
    return qs.aggregate(
        total=Coalesce(Sum(_money_expr()), Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2)))
    )["total"]


@register.simple_tag(takes_context=True)
def admin_revenue_stats(context: dict) -> dict:
    period = _resolve_period(context)

    qs = Reservation.objects.all()
    period_qs = qs.filter(created_at__date__gte=period["start_date"], created_at__date__lte=period["end_date"])

    period_paid_qs = period_qs.filter(payment_status="paid")
    paid_total = _sum_amount(period_paid_qs)

    pending_balance = period_qs.filter(payment_status="pending").aggregate(
        total=Coalesce(
            Sum("balance_due"),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2)),
        )
    )["total"]

    reservation_count = period_qs.count()
    paid_count = period_paid_qs.count()

    avg_paid_ticket = Decimal("0.00")
    if paid_count:
        avg_paid_ticket = paid_total / Decimal(paid_count)

    return {
        "period_key": period["key"],
        "period_label": period["label"],
        "start_date": period["start_date"],
        "end_date": period["end_date"],
        "period_revenue": paid_total,
        "period_revenue_text": _format_currency(paid_total),
        "paid_total": paid_total,
        "paid_total_text": _format_currency(paid_total),
        "pending_balance": pending_balance,
        "pending_balance_text": _format_currency(pending_balance),
        "reservation_count": reservation_count,
        "paid_count": paid_count,
        "paid_period_count": paid_count,
        "avg_paid_ticket": avg_paid_ticket,
        "avg_paid_ticket_text": _format_currency(avg_paid_ticket),
    }


@register.simple_tag(takes_context=True)
def admin_revenue_series(context: dict) -> dict:
    period = _resolve_period(context)
    today = period["end_date"]
    qs = Reservation.objects.filter(payment_status="paid")
    items: list[dict] = []
    max_amount = Decimal("0.00")

    buckets: list[tuple[str, date, date]] = []

    if period["key"] == "7d":
        for i in range(6, -1, -1):
            start = today - timedelta(days=i)
            end = start + timedelta(days=1)
            buckets.append((start.strftime("%d/%m"), start, end))
    elif period["key"] == "qtd":
        cursor = _month_start(period["start_date"])
        last_month_start = _month_start(today)
        while cursor <= last_month_start:
            buckets.append((f"T{cursor.month:02d}", cursor, _next_month(cursor)))
            cursor = _next_month(cursor)
    else:
        start = period["start_date"]
        span = 5
        for i in range(6):
            bucket_start = start + timedelta(days=i * span)
            bucket_end = min(bucket_start + timedelta(days=span), today + timedelta(days=1))
            if bucket_start >= bucket_end:
                continue
            buckets.append((bucket_start.strftime("%d/%m"), bucket_start, bucket_end))

    for label, start, end in buckets:
        amount = _sum_amount(qs.filter(created_at__date__gte=start, created_at__date__lt=end))

        if amount > max_amount:
            max_amount = amount

        items.append(
            {
                "label": label,
                "amount": amount,
                "amount_text": _format_currency(amount),
            }
        )

    for item in items:
        if max_amount > 0:
            pct = int((item["amount"] / max_amount) * 100)
            item["height_pct"] = max(pct, 12)
        else:
            item["height_pct"] = 12

    return {
        "items": items,
        "max_amount_text": _format_currency(max_amount),
        "period_label": period["label"],
    }
