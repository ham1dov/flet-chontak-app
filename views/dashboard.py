from datetime import date

import flet as ft
from flet_charts import (
    BarChart,
    BarChartGroup,
    BarChartRod,
    LineChart,
    LineChartData,
    LineChartDataPoint,
    PieChart,
    PieChartSection,
)

from finance import (
    category_totals,
    daily_totals,
    filtered_transactions,
    payment_totals,
    transaction_total,
)
from theme import palette_for


MONTH_NAMES = {
    "uz": ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "ru": ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
}


def money(value, currency):
    digits = 0 if currency in ("UZS", "KRW") else 2
    return f"{value:,.{digits}f} {currency}"


def build_dashboard(page, state, rates, t, on_edit, on_delete):
    transactions = state["transactions"]
    display_currency = state["settings"]["currency"]
    colors = palette_for(state)
    language = state["settings"].get("language", "uz")
    today = date.today()
    current_month = today.strftime("%Y-%m")
    categories = sorted(
        {item["category"] for item in transactions}
        | {name for group in state["categories"].values() for name in group}
    )
    category_labels = {t("all"): "All"}
    category_labels.update({name: name for name in categories})
    payment_labels = {t("all"): "All", t("cash"): "Cash", t("card"): "Card"}
    sort_labels = {t("date"): "Date", t("category"): "Category", t("amount"): "Amount"}
    pie_period_labels = {
        t("this_month"): "month",
        t("last_three_months"): "three_months",
        t("this_year"): "year",
        t("all_time"): "all",
    }

    search = ft.TextField(label=t("search"), prefix_icon=ft.Icons.SEARCH, expand=True)
    category_filter = ft.Dropdown(
        label=t("category"), value=t("all"),
        options=[ft.DropdownOption(text=label) for label in category_labels],
    )
    payment_filter = ft.Dropdown(
        label=t("payment"), value=t("all"),
        options=[ft.DropdownOption(text=label) for label in payment_labels],
    )
    sort_filter = ft.Dropdown(
        label=t("sort"), value=t("date"), expand=True,
        options=[ft.DropdownOption(text=label) for label in sort_labels],
    )
    pie_period = ft.Dropdown(
        label=t("pie_period"), value=t("this_month"),
        options=[ft.DropdownOption(text=label) for label in pie_period_labels],
    )
    rows = ft.Column(spacing=8, controls=[])
    charts = ft.Column(spacing=12, controls=[])
    income_value = ft.Text(size=19, weight=ft.FontWeight.BOLD, color=colors["income"])
    expense_value = ft.Text(size=19, weight=ft.FontWeight.BOLD, color=colors["expense"])
    balance_value = ft.Text(size=24, weight=ft.FontWeight.BOLD, color=colors["on_primary"])
    incomplete_note = ft.Text(size=12, color=colors["warning"], visible=False)

    def chart_card(title, content):
        return ft.Container(
            padding=16,
            bgcolor=colors["surface"],
            border=ft.Border.all(1, colors["border"]),
            border_radius=18,
            content=ft.Column(
                spacing=10,
                controls=[ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=colors["text"]), content],
            ),
        )

    def make_pie(values):
        sections = [
            PieChartSection(
                value=float(value), title=label, color=colors["chart"][index % len(colors["chart"])],
                radius=48,
            )
            for index, (label, value) in enumerate(values)
            if value > 0
        ]
        return PieChart(sections=sections, sections_space=4, center_space_radius=32, height=190)

    def in_selected_period(item, period):
        item_date = item.get("date", "")
        if period == "month":
            return item_date.startswith(current_month)
        if period == "three_months":
            month_index = today.year * 12 + today.month - 1 - 2
            start_year, start_month0 = divmod(month_index, 12)
            return item_date >= f"{start_year:04d}-{start_month0 + 1:02d}-01" and item_date <= today.isoformat()
        if period == "year":
            return item_date.startswith(str(today.year))
        return True

    def build_charts(items):
        daily, _ = daily_totals(items, display_currency, rates)
        points_income = [
            LineChartDataPoint(x=index, y=values["Income"], tooltip=day.strftime("%b %d"))
            for index, (day, values) in enumerate(daily)
        ]
        points_expense = [
            LineChartDataPoint(x=index, y=values["Expense"], tooltip=day.strftime("%b %d"))
            for index, (day, values) in enumerate(daily)
        ]
        chart_max = max([point.y for point in points_income + points_expense] or [0])
        line_chart = LineChart(
            height=210, min_x=0, max_x=6, min_y=0, max_y=max(chart_max * 1.15, 1), baseline_y=0,
            data_series=[
                LineChartData(points=points_income, color=colors["income"], curved=True, stroke_width=3),
                LineChartData(points=points_expense, color=colors["expense"], curved=True, stroke_width=3),
            ],
        )
        line_legend = ft.Row(
            spacing=16,
            controls=[
                ft.Row(tight=True, spacing=5, controls=[ft.Icon(ft.Icons.CIRCLE, color=colors["income"], size=10), ft.Text(t("income"), size=12, color=colors["muted"])]),
                ft.Row(tight=True, spacing=5, controls=[ft.Icon(ft.Icons.CIRCLE, color=colors["expense"], size=10), ft.Text(t("expenses"), size=12, color=colors["muted"])]),
            ],
        )
        results = [chart_card(t("trend"), ft.Column(controls=[line_chart, line_legend]))]

        for kind, title_key in (("Expense", "by_category"), ("Income", "income_by_category")):
            totals, _ = category_totals(items, kind, display_currency, rates)
            top = totals[:5]
            if not top:
                content = ft.Text(t("no_transactions"), color=colors["muted"])
            else:
                bars = BarChart(
                    height=190,
                    groups=[
                        BarChartGroup(
                            x=index,
                            rods=[BarChartRod(to_y=value, color=colors["chart"][index % len(colors["chart"])], width=20)],
                        )
                        for index, (label, value) in enumerate(top)
                    ],
                    max_y=max(top[0][1] * 1.15, 1),
                )
                legend = ft.Column(
                    spacing=5,
                    controls=[
                        ft.Text(f"{label}  ·  {money(value, display_currency)}", size=12, color=colors["muted"])
                        for label, value in top
                    ],
                )
                content = ft.Column(spacing=6, controls=[bars, legend])
            results.append(chart_card(t(title_key), content))

        pie_items = [item for item in items if in_selected_period(item, pie_period_labels.get(pie_period.value, "month"))]
        for kind, title_key in (("Expense", "expense"), ("Income", "income_kind")):
            payments, _ = payment_totals(pie_items, kind, display_currency, rates)
            payment_rows = [(t("cash"), payments.get("Cash", 0)), (t("card"), payments.get("Card", 0))]
            payment_rows = [(name, value) for name, value in payment_rows if value > 0]
            content = make_pie(payment_rows) if payment_rows else ft.Text(t("no_transactions"), color=colors["muted"])
            results.append(chart_card(f"{t('payment_mix')} · {t(title_key)}", content))
        return results

    def transaction_tile(item):
        is_income = item["kind"] == "Income"
        accent = colors["income"] if is_income else colors["expense"]
        payment_label = t("cash") if item["payment"] == "Cash" else t("card")
        sign = "+" if is_income else "−"
        return ft.Container(
            padding=12, bgcolor=colors["surface"], border=ft.Border.all(1, colors["border"]), border_radius=16,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(
                                padding=8, border_radius=12,
                                bgcolor=colors["income_soft"] if is_income else colors["expense_soft"],
                                content=ft.Icon(ft.Icons.PAYMENTS if item["payment"] == "Cash" else ft.Icons.CREDIT_CARD, color=accent),
                            ),
                            ft.Column(
                                expand=True, spacing=3,
                                controls=[
                                    ft.Text(item["note"] or item["category"], weight=ft.FontWeight.BOLD, color=colors["text"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(item["category"], size=12, color=colors["muted"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                            ),
                            ft.Text(f"{sign}{money(float(item['amount']), item['currency'])}", color=accent, weight=ft.FontWeight.BOLD, size=13),
                        ],
                    ),
                    ft.Row(
                        controls=[
                            ft.Text(f'{payment_label} · {item["date"]}', expand=True, size=12, color=colors["muted"]),
                            ft.IconButton(ft.Icons.EDIT, tooltip=t("edit"), on_click=lambda: on_edit(item)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip=t("delete"), on_click=lambda: on_delete(item["id"])),
                        ],
                    ),
                ],
            ),
        )

    def refresh_results():
        category = category_labels.get(category_filter.value, "All")
        payment = payment_labels.get(payment_filter.value, "All")
        sort = sort_labels.get(sort_filter.value, "Date")
        selected = filtered_transactions(transactions, search.value or "", category, payment, sort)
        month_items = [item for item in transactions if item.get("date", "").startswith(current_month)]
        income, income_complete = transaction_total(month_items, "Income", display_currency, rates)
        expenses, expense_complete = transaction_total(month_items, "Expense", display_currency, rates)
        income_value.value = money(income, display_currency)
        expense_value.value = money(expenses, display_currency)
        balance_value.value = money(income - expenses, display_currency)
        incomplete_note.visible = not (income_complete and expense_complete)
        rows.controls = [transaction_tile(item) for item in selected] or [ft.Text(t("no_transactions"), color=colors["muted"])]
        charts.controls = build_charts(selected)
        income_value.update()
        expense_value.update()
        balance_value.update()
        incomplete_note.update()
        rows.update()
        charts.update()

    search.on_change = refresh_results
    category_filter.on_select = refresh_results
    payment_filter.on_select = refresh_results
    sort_filter.on_select = refresh_results
    pie_period.on_select = refresh_results

    month_items = [item for item in transactions if item.get("date", "").startswith(current_month)]
    income, income_complete = transaction_total(month_items, "Income", display_currency, rates)
    expenses, expense_complete = transaction_total(month_items, "Expense", display_currency, rates)
    income_value.value = money(income, display_currency)
    expense_value.value = money(expenses, display_currency)
    balance_value.value = money(income - expenses, display_currency)
    incomplete_note.value = t("partial_totals")
    incomplete_note.visible = not (income_complete and expense_complete)
    rows.controls = [transaction_tile(item) for item in filtered_transactions(transactions)] or [ft.Text(t("no_transactions"), color=colors["muted"])]
    charts.controls = build_charts(transactions)
    month_name = MONTH_NAMES.get(language, MONTH_NAMES["uz"])[today.month - 1]

    return ft.Column(
        expand=True,
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Column(
                spacing=3,
                controls=[
                    ft.Text(f"{t('welcome')}{', ' + state['settings']['name'] if state['settings']['name'] else ''}", size=24, weight=ft.FontWeight.BOLD, color=colors["text"]),
                    ft.Text(t("overview"), color=colors["muted"]),
                ],
            ),
            ft.Text(t("monthly_summary").format(month=month_name), size=13, weight=ft.FontWeight.BOLD, color=colors["muted"]),
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(expand=True, padding=14, bgcolor=colors["surface"], border=ft.Border.all(1, colors["border"]), border_radius=16, content=ft.Column(spacing=7, controls=[ft.Row(spacing=6, controls=[ft.Icon(ft.Icons.ARROW_DOWNWARD, color=colors["income"], size=16), ft.Text(t("income"), size=12, color=colors["muted"])]), income_value])),
                    ft.Container(expand=True, padding=14, bgcolor=colors["surface"], border=ft.Border.all(1, colors["border"]), border_radius=16, content=ft.Column(spacing=7, controls=[ft.Row(spacing=6, controls=[ft.Icon(ft.Icons.ARROW_UPWARD, color=colors["expense"], size=16), ft.Text(t("expenses"), size=12, color=colors["muted"])]), expense_value])),
                ],
            ),
            ft.Container(expand=True, padding=18, bgcolor=colors["primary_dark"], border_radius=18, content=ft.Column(spacing=5, controls=[ft.Text(t("balance"), color=colors["primary_soft"]), balance_value])),
            incomplete_note,
            search,
            ft.Row(spacing=8, controls=[ft.Container(expand=True, content=category_filter), ft.Container(expand=True, content=payment_filter)]),
            sort_filter,
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(t("charts"), size=19, weight=ft.FontWeight.BOLD, color=colors["text"]), ft.Container(width=170, content=pie_period)]),
            charts,
            ft.Text(t("transactions"), size=19, weight=ft.FontWeight.BOLD, color=colors["text"]),
            rows,
        ],
    )
