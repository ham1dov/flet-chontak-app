import flet as ft

from data import CURRENCIES
from theme import palette_for


LANGUAGES = [("uz", "O‘zbekcha"), ("en", "English"), ("ru", "Русский")]


def build_settings(page, state, t, rate_message, on_settings_save, on_categories_changed, on_refresh_rates):
    settings = state["settings"]
    colors = palette_for(state)
    name_field = ft.TextField(label=t("name"), value=settings.get("name", ""))
    language_labels = {code: label for code, label in LANGUAGES}
    language_field = ft.Dropdown(
        label=t("language"),
        value=language_labels.get(settings.get("language", "uz"), "O‘zbekcha"),
        options=[ft.DropdownOption(text=label) for _, label in LANGUAGES],
    )
    language_codes = {label: code for code, label in LANGUAGES}
    currency_field = ft.Dropdown(
        label=t("display_currency"),
        value=settings.get("currency", "UZS"),
        options=[ft.DropdownOption(text=code) for code in CURRENCIES],
    )
    category_sections = ft.Column(spacing=12, controls=[])

    async def change_theme(event):
        await on_settings_save({"dark_mode": bool(event.control.value)})

    theme_switch = ft.Switch(
        label=t("dark_mode"),
        value=bool(settings.get("dark_mode", False)),
        active_color=colors["primary"],
        on_change=change_theme,
    )

    def category_card(kind):
        is_income = kind == "Income"
        title = t("income_categories" if is_income else "expense_categories")
        entries = state["categories"].get(kind, [])
        items = []
        for category in entries:
            def edit_category_click(name):
                return lambda: open_category_dialog(kind, name)

            def delete_category_click(name):
                return lambda: confirm_category_delete(kind, name)

            items.append(
                ft.Row(
                    controls=[
                        ft.Text(category, expand=True),
                        ft.IconButton(
                            ft.Icons.EDIT,
                            tooltip=t("edit"),
                            on_click=edit_category_click(category),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            tooltip=t("delete"),
                            on_click=delete_category_click(category),
                        ),
                    ],
                )
            )
        if not items:
            items.append(ft.Text(t("no_category"), color=colors["muted"]))
        return ft.Container(
            padding=14,
            bgcolor=colors["surface"],
            border=ft.Border.all(1, colors["border"]),
            border_radius=14,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(title, weight=ft.FontWeight.BOLD),
                            ft.IconButton(ft.Icons.ADD, tooltip=t("add_category"), on_click=lambda: open_category_dialog(kind)),
                        ],
                    ),
                    *items,
                ],
            ),
        )

    async def persist_categories(updated):
        await on_categories_changed(updated)

    def open_category_dialog(kind, current=None):
        category_field = ft.TextField(
            label=t("category_name"),
            value=current or "",
            autofocus=True,
        )
        error = ft.Text(color=colors["expense"], size=12, visible=False)

        async def save_category():
            name = (category_field.value or "").strip()
            if not name:
                category_field.error = t("name_required")
                category_field.update()
                return
            existing = state["categories"].get(kind, [])
            if any(value.casefold() == name.casefold() and value != current for value in existing):
                error.value = t("category_exists")
                error.visible = True
                error.update()
                return
            updated = {key: list(values) for key, values in state["categories"].items()}
            if current and current in updated.get(kind, []):
                index = updated[kind].index(current)
                updated[kind][index] = name
                for item in state["transactions"]:
                    if item["kind"] == kind and item["category"] == current:
                        item["category"] = name
            else:
                updated.setdefault(kind, []).append(name)
            page.pop_dialog()
            await persist_categories(updated)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("edit_category") if current else t("add_category")),
            content=ft.Column(tight=True, spacing=8, controls=[category_field, error]),
            actions=[
                ft.TextButton(content=t("cancel"), on_click=lambda: page.pop_dialog()),
                ft.Button(content=t("save"), bgcolor=colors["primary"], color=colors["on_primary"], on_click=save_category),
            ],
        )
        page.show_dialog(dialog)

    def confirm_category_delete(kind, category):
        async def delete_category():
            updated = {key: list(values) for key, values in state["categories"].items()}
            updated[kind] = [value for value in updated.get(kind, []) if value != category]
            page.pop_dialog()
            await persist_categories(updated)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(t("delete_category")),
                content=ft.Text(t("delete_category_confirm")),
                actions=[
                    ft.TextButton(content=t("cancel"), on_click=lambda: page.pop_dialog()),
                    ft.Button(content=t("delete"), bgcolor=colors["expense"], color=ft.Colors.WHITE, on_click=delete_category),
                ],
            )
        )

    async def save_profile():
        language = language_codes.get(language_field.value, language_field.value)
        await on_settings_save(
            {
                "name": (name_field.value or "").strip(),
                "language": language,
                "currency": currency_field.value or "UZS",
            }
        )

    category_sections.controls = [category_card("Expense"), category_card("Income")]
    updated_at = state.get("rates_updated_at") or t("rates_missing")
    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text(t("settings"), size=24, weight=ft.FontWeight.BOLD, color=colors["text"]),
            ft.Container(
                padding=16,
                bgcolor=colors["surface"],
                border=ft.Border.all(1, colors["border"]),
                border_radius=18,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Text(t("profile"), size=18, weight=ft.FontWeight.BOLD, color=colors["text"]),
                        name_field,
                        language_field,
                        currency_field,
                        ft.Text(t("appearance"), size=16, weight=ft.FontWeight.BOLD, color=colors["text"]),
                        theme_switch,
                        ft.Button(content=t("save"), icon=ft.Icons.DONE, bgcolor=colors["primary"], color=colors["on_primary"], on_click=save_profile),
                    ],
                ),
            ),
            ft.Text(t("manage_categories"), size=18, weight=ft.FontWeight.BOLD, color=colors["text"]),
            category_sections,
            ft.Container(
                padding=14,
                bgcolor=colors["surface"],
                border=ft.Border.all(1, colors["border"]),
                border_radius=14,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text(t("exchange_status"), weight=ft.FontWeight.BOLD),
                        ft.Text(f"{t('rate_display')} · {updated_at}", size=12, color=colors["muted"]),
                        ft.Text(rate_message or t("rates_cached" if state.get("rates") else "rates_missing"), size=12, color=colors["text"]),
                        ft.Button(content=t("refresh"), icon=ft.Icons.REFRESH, on_click=on_refresh_rates),
                    ],
                ),
            ),
        ],
    )
