import flet as ft


def palette_for(state):
    dark = bool(state.get("settings", {}).get("dark_mode", False))
    if dark:
        return {
            "background": ft.Colors.GREY_900,
            "surface": ft.Colors.GREY_800,
            "surface_alt": ft.Colors.GREY_700,
            "text": ft.Colors.GREY_100,
            "muted": ft.Colors.GREY_300,
            "border": ft.Colors.GREY_700,
            "primary": ft.Colors.GREEN_300,
            "primary_dark": ft.Colors.GREEN_400,
            "primary_soft": ft.Colors.GREEN_900,
            "on_primary": ft.Colors.GREY_900,
            "income": ft.Colors.GREEN_300,
            "expense": ft.Colors.RED_300,
            "warning": ft.Colors.ORANGE_300,
            "income_soft": ft.Colors.GREEN_900,
            "expense_soft": ft.Colors.RED_900,
            "chart": [ft.Colors.GREEN_300, ft.Colors.BLUE_300, ft.Colors.ORANGE_300, ft.Colors.PURPLE_300, ft.Colors.TEAL_300, ft.Colors.PINK_300],
        }
    return {
        "background": ft.Colors.GREY_50,
        "surface": ft.Colors.WHITE,
        "surface_alt": ft.Colors.GREY_100,
        "text": ft.Colors.GREY_900,
        "muted": ft.Colors.GREY_600,
        "border": ft.Colors.GREY_200,
        "primary": ft.Colors.GREEN_700,
        "primary_dark": ft.Colors.GREEN_800,
        "primary_soft": ft.Colors.GREEN_50,
        "on_primary": ft.Colors.WHITE,
        "income": ft.Colors.GREEN_700,
        "expense": ft.Colors.RED_700,
        "warning": ft.Colors.ORANGE_800,
        "income_soft": ft.Colors.GREEN_50,
        "expense_soft": ft.Colors.RED_50,
        "chart": [ft.Colors.GREEN_700, ft.Colors.BLUE_600, ft.Colors.ORANGE_700, ft.Colors.PURPLE_600, ft.Colors.TEAL_700, ft.Colors.PINK_600],
    }
