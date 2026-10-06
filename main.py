import asyncio
import logging
import uuid

import flet as ft
import httpx2 as httpx

from currency_api import fetch_rates
from data import CURRENCIES, DEFAULT_CATEGORIES, TEXT, seed_transactions
from storage import create_storage
from theme import palette_for
from views.add_transaction import build_add_transaction
from views.dashboard import build_dashboard
from views.settings import build_settings


LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(LOG_LEVEL)
log = logging.getLogger(f"app.{__name__}")

GREEN = ft.Colors.GREEN_700


async def main(page: ft.Page):
    page.title = "Cho`ntak"
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.GREEN_700)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.GREEN_300)

    storage = await create_storage(page)
    state = await storage.load_state()
    if state is None:
        state = {
            "settings": {"name": "", "language": "uz", "currency": "UZS", "dark_mode": False},
            "categories": {key: list(values) for key, values in DEFAULT_CATEGORIES["uz"].items()},
            "transactions": seed_transactions(),
            "rates": {},
            "rates_updated_at": "",
        }
        await storage.save_state(state)
    state.setdefault("settings", {"name": "", "language": "uz", "currency": "UZS"})
    state["settings"].setdefault("currency", "UZS")
    state["settings"].setdefault("language", "uz")
    state["settings"].setdefault("name", "")
    state["settings"].setdefault("dark_mode", False)
    state.setdefault("categories", {key: list(values) for key, values in DEFAULT_CATEGORIES["uz"].items()})
    state.setdefault("transactions", [])
    state.setdefault("rates", {})
    state.setdefault("rates_updated_at", "")

    active_index = 0
    editing_id = None
    rate_message = ""

    def translate(key):
        language = state["settings"].get("language", "uz")
        return TEXT.get(language, TEXT["uz"]).get(key, TEXT["en"].get(key, key))

    async def refresh_rates(silent=False):
        nonlocal rate_message
        if not silent:
            rate_message = translate("rates_loading")
            render_screen()
        try:
            snapshot = await fetch_rates()
            state["rates"] = snapshot["rates"]
            state["rates_updated_at"] = snapshot["updated_at"]
            rate_message = translate("rates_live")
            await storage.save_state(state)
            log.info("Exchange rates refreshed")
        except (httpx.HTTPError, ValueError, KeyError) as error:
            rate_message = translate("rates_cached" if state.get("rates") else "rate_error")
            log.warning("Exchange rate refresh failed: %s", error)
        except Exception as error:
            rate_message = translate("rates_cached" if state.get("rates") else "rate_error")
            log.exception("Unexpected exchange rate error: %s", error)
        if not silent and active_index == 2:
            render_screen()
        elif active_index == 0:
            render_screen()

    def show_delete_dialog(transaction_id):
        async def confirm_delete():
            state["transactions"] = [
                item for item in state["transactions"] if item["id"] != transaction_id
            ]
            await storage.save_state(state)
            page.pop_dialog()
            render_screen()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(translate("delete")),
                content=ft.Text(translate("delete_confirm")),
                actions=[
                    ft.TextButton(content=translate("cancel"), on_click=lambda: page.pop_dialog()),
                    ft.Button(content=translate("delete"), bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE, on_click=confirm_delete),
                ],
            )
        )

    def open_edit(item):
        nonlocal active_index, editing_id
        editing_id = item["id"]
        active_index = 1
        render_screen()

    async def save_transaction(item):
        existing_index = next(
            (index for index, saved in enumerate(state["transactions"]) if saved["id"] == item.get("id")),
            None,
        )
        if existing_index is None:
            item["id"] = str(uuid.uuid4())
            state["transactions"].append(item)
        else:
            state["transactions"][existing_index] = item
        await storage.save_state(state)
        nonlocal active_index, editing_id
        active_index = 0
        editing_id = None
        render_screen()

    async def save_settings(values):
        state["settings"].update(values)
        await storage.save_state(state)
        render_screen()

    async def save_categories(categories):
        state["categories"] = categories
        await storage.save_state(state)
        render_screen()

    async def refresh_rates_from_settings():
        await refresh_rates()

    def on_navigation_change(event):
        nonlocal active_index, editing_id
        active_index = event.control.selected_index
        if active_index != 1:
            editing_id = None
        else:
            editing_id = None
        render_screen()

    def render_screen():
        palette = palette_for(state)
        page.theme_mode = ft.ThemeMode.DARK if state["settings"].get("dark_mode") else ft.ThemeMode.LIGHT
        page.bgcolor = palette["background"]
        language = state["settings"].get("language", "uz")
        nav = ft.NavigationBar(
            selected_index=active_index,
            bgcolor=palette["surface"],
            indicator_color=palette["primary_soft"],
            on_change=on_navigation_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME, label=translate("dashboard")),
                ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE_OUTLINE, label=translate("add")),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label=translate("settings")),
            ],
        )
        page.navigation_bar = nav

        if active_index == 0:
            screen = build_dashboard(
                page,
                state,
                state.get("rates", {}),
                translate,
                open_edit,
                show_delete_dialog,
            )
        elif active_index == 1:
            editing = next(
                (item for item in state["transactions"] if item["id"] == editing_id),
                None,
            )
            screen = build_add_transaction(
                page,
                state,
                translate,
                editing,
                save_transaction,
                lambda: go_to_dashboard(),
            )
        else:
            screen = build_settings(
                page,
                state,
                translate,
                rate_message,
                save_settings,
                save_categories,
                refresh_rates_from_settings,
            )

        page.clean()
        page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Container(expand=True, padding=18, content=screen),
            )
        )
        page.update()

    def go_to_dashboard():
        nonlocal active_index, editing_id
        active_index = 0
        editing_id = None
        render_screen()

    render_screen()
    asyncio.create_task(refresh_rates(silent=True))


ft.run(main)
