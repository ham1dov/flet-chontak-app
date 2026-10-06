from collections import defaultdict
from datetime import date, timedelta



def convert_amount(amount, source, target, rates):
    amount = float(amount)
    if source == target:
        return amount
    source_rate = rates.get(source)
    target_rate = rates.get(target)
    if not source_rate or not target_rate:
        return None
    return amount / float(source_rate) * float(target_rate)


def transaction_total(transactions, kind, currency, rates):
    total = 0.0
    complete = True
    for item in transactions:
        if item["kind"] != kind:
            continue
        converted = convert_amount(item["amount"], item["currency"], currency, rates)
        if converted is None:
            complete = False
        else:
            total += converted
    return total, complete


def filtered_transactions(transactions, query="", category="All", payment="All", sort="Date"):
    query = query.strip().casefold()
    results = []
    for item in transactions:
        searchable = " ".join(
            str(item.get(key, ""))
            for key in ("note", "category", "payment", "kind", "currency", "amount")
        ).casefold()
        if query and query not in searchable:
            continue
        if category != "All" and item["category"] != category:
            continue
        if payment != "All" and item["payment"] != payment:
            continue
        results.append(item)

    if sort == "Category":
        results.sort(key=lambda item: (item["category"].casefold(), item["date"]), reverse=True)
    elif sort == "Amount":
        results.sort(key=lambda item: float(item["amount"]), reverse=True)
    else:
        results.sort(key=lambda item: (item["date"], item["id"]), reverse=True)
    return results


def daily_totals(transactions, currency, rates, days=7):
    today = date.today()
    labels = [(today - timedelta(days=days - index - 1)) for index in range(days)]
    totals = {day.isoformat(): {"Income": 0.0, "Expense": 0.0} for day in labels}
    complete = True
    for item in transactions:
        bucket = totals.get(item["date"])
        if bucket is None:
            continue
        converted = convert_amount(item["amount"], item["currency"], currency, rates)
        if converted is None:
            complete = False
        else:
            bucket[item["kind"]] += converted
    return [(day, totals[day.isoformat()]) for day in labels], complete


def category_totals(transactions, kind, currency, rates):
    totals = defaultdict(float)
    complete = True
    for item in transactions:
        if item["kind"] != kind:
            continue
        converted = convert_amount(item["amount"], item["currency"], currency, rates)
        if converted is None:
            complete = False
        else:
            totals[item["category"]] += converted
    return sorted(totals.items(), key=lambda pair: pair[1], reverse=True), complete


def payment_totals(transactions, kind, currency, rates):
    totals = defaultdict(float)
    complete = True
    for item in transactions:
        if item["kind"] != kind:
            continue
        converted = convert_amount(item["amount"], item["currency"], currency, rates)
        if converted is None:
            complete = False
        else:
            totals[item["payment"]] += converted
    return dict(totals), complete
