from datetime import date
import math

import flet as ft

from data import CURRENCIES
from theme import palette_for


KINDS = {"Expense": "expense", "Income": "income_kind"}
PAYMENTS = {"Cash": "cash", "Card": "card"}


def build_add_transaction(page, state, t, transaction, on_save, on_cancel):
    existing = transaction or {}
    categories = state["categories"]
    settings = state["settings"]
    colors = palette_for(state)
    labels_to_kind = {t(label): kind for kind, label in KINDS.items()}
    labels_to_payment = {t(label): value for value, label in PAYMENTS.items()}

    kind_field = ft.Dropdown(
        label=t("kind"),
        value=t(KINDS.get(existing.get("kind", "Expense"), "expense")),
        options=[ft.DropdownOption(text=t(label)) for label in KINDS.values()],
    )
    category_options = categories.get(existing.get("kind", "Expense"), [])
    category_field = ft.Dropdown(
        label=t("category"),
        value=existing.get("category") or (category_options[0] if category_options else None),
        hint_text=t("choose_category"),
        options=[ft.DropdownOption(text=name) for name in category_options],
    )
    payment_field = ft.Dropdown(
        label=t("payment"),
        value=t(PAYMENTS.get(existing.get("payment", "Cash"), "cash")),
        options=[ft.DropdownOption(text=t(label)) for label in PAYMENTS.values()],
    )
    currency_field = ft.Dropdown(
        label=t("currency"),
        value=existing.get("currency", settings["currency"]),
        options=[ft.DropdownOption(text=code) for code in CURRENCIES],
    )
    amount_field = ft.TextField(
        label=t("amount"),
        value=str(existing.get("amount", "")) if transaction else "",
        hint_text=t("amount_placeholder"),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    note_field = ft.TextField(
        label=t("note"),
        value=existing.get("note", ""),
        hint_text=t("enter_note"),
        multiline=True,
        min_lines=2,
        max_lines=4,
    )
    date_field = ft.TextField(
        label=t("date"),
        value=existing.get("date", date.today().isoformat()),
        hint_text="YYYY-MM-DD",
    )
    error_text = ft.Text(color=colors["expense"], size=13, visible=False)

    def update_category_options():
        kind = labels_to_kind.get(kind_field.value, "Expense")
        options = categories.get(kind, [])
        category_field.options = [ft.DropdownOption(text=name) for name in options]
        if category_field.value not in options:
            category_field.value = options[0] if options else None
        category_field.update()

    kind_field.on_select = update_category_options

    async def save():
        raw_amount = (amount_field.value or "").replace(" ", "").strip()
        if "," in raw_amount and "." not in raw_amount:
            raw_amount = raw_amount.replace(",", ".")
        else:
            raw_amount = raw_amount.replace(",", "")
        try:
            amount = float(raw_amount)
        except ValueError:
            amount = 0
        if not math.isfinite(amount) or amount <= 0:
            error_text.value = t("amount_invalid")
            error_text.visible = True
            error_text.update()
            return
        try:
            transaction_date = date.fromisoformat((date_field.value or "").strip()).isoformat()
        except ValueError:
            error_text.value = t("date_invalid")
            error_text.visible = True
            error_text.update()
            return
        kind = labels_to_kind.get(kind_field.value, "Expense")
        category = category_field.value
        if not category:
            error_text.value = t("choose_category")
            error_text.visible = True
            error_text.update()
            return
        payload = {
            "id": existing.get("id"),
            "kind": kind,
            "amount": round(amount, 2),
            "currency": currency_field.value or settings["currency"],
            "payment": labels_to_payment.get(payment_field.value, "Cash"),
            "category": category,
            "note": (note_field.value or "").strip(),
            "date": transaction_date,
        }
        await on_save(payload)

    header_key = "edit_transaction" if transaction else "add_transaction"
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=14,
        controls=[
            ft.Container(
                padding=18,
                bgcolor=colors["primary_dark"],
                border_radius=18,
                content=ft.Column(
                    spacing=5,
                    controls=[
                        ft.Text(t(header_key), size=23, weight=ft.FontWeight.BOLD, color=colors["on_primary"]),
                        ft.Text(t("overview"), color=colors["primary_soft"]),
                    ],
                ),
            ),
            kind_field,
            amount_field,
            currency_field,
            category_field,
            payment_field,
            note_field,
            date_field,
            error_text,
            ft.Row(
                controls=[
                    ft.OutlinedButton(content=t("cancel"), on_click=on_cancel),
                    ft.Button(content=t("save"), icon=ft.Icons.DONE, bgcolor=colors["primary"], color=colors["on_primary"], on_click=save),
                ],
            ),
        ],
    )
