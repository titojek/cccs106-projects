import asyncio
import flet as ft
from datetime import datetime
from weather_service import WeatherService, WeatherServiceError
from history_service import HistoryService
from watchlist_service import WatchlistService
from config import Config


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        return loop.create_task(coro)


def main(page: ft.Page):
    # ---------- PAGE SETUP ----------
    page.title = "Weather App"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window.width = 900
    page.window.height = 750
    page.window.resizable = True
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    weather_service = WeatherService()
    history_service = HistoryService()
    watchlist_service = WatchlistService()

    # ---------- STATE ----------
    current_city = {"name": None}
    is_loading = {"value": False}

    # ---------- ALERT SYSTEM ----------
    current_snackbar = None

    def show_alert(message: str, type_: str = "info"):
        nonlocal current_snackbar

        icons = {
            "error": ft.Icons.ERROR_OUTLINE,
            "warning": ft.Icons.WARNING_AMBER_ROUNDED,
            "success": ft.Icons.CHECK_CIRCLE_OUTLINE,
            "info": ft.Icons.INFO_OUTLINE,
            "alert": ft.Icons.WB_SUNNY,
        }
        colors = {
            "error": ft.Colors.RED_600,
            "warning": ft.Colors.AMBER_700,
            "success": ft.Colors.GREEN_600,
            "info": ft.Colors.BLUE_600,
            "alert": ft.Colors.DEEP_ORANGE_600,
        }

        if current_snackbar:
            page.close(current_snackbar)

        snackbar = ft.SnackBar(
            bgcolor=colors.get(type_, ft.Colors.BLUE_600),
            content=ft.Row(
                [
                    ft.Icon(icons.get(type_, ft.Icons.INFO_OUTLINE), color=ft.Colors.WHITE),
                    ft.Text(message, color=ft.Colors.WHITE, size=15, weight=ft.FontWeight.W_600),
                ],
                spacing=10,
            ),
            duration=4000,
        )
        current_snackbar = snackbar
        page.open(snackbar)
        page.update()

    # ---------- TOGGLES ----------
    def toggle_theme():
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            theme_icon.icon = ft.Icons.DARK_MODE
            show_alert("Dark mode enabled 🌙", "info")
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_icon.icon = ft.Icons.LIGHT_MODE
            show_alert("Light mode enabled ☀️", "info")
        page.update()
        update_card_styles()

    def toggle_units():
        if Config.UNITS == "metric":
            Config.UNITS = "imperial"
            unit_icon.content = ft.Text("°F", size=18, weight=ft.FontWeight.BOLD)
            show_alert("Switched to Fahrenheit (°F)", "info")
        else:
            Config.UNITS = "metric"
            unit_icon.content = ft.Text("°C", size=18, weight=ft.FontWeight.BOLD)
            show_alert("Switched to Celsius (°C)", "info")
        
        # Refresh current city if one is loaded
        if current_city["name"]:
            fetch_weather(current_city["name"])
        page.update()

    def toggle_auto_refresh():
        """Toggle auto-refresh feature"""
        if auto_refresh_enabled["value"]:
            auto_refresh_enabled["value"] = False
            auto_refresh_btn.icon = ft.Icons.SYNC_DISABLED
            auto_refresh_btn.tooltip = "Enable auto-refresh"
            show_alert("Auto-refresh disabled", "info")
        else:
            auto_refresh_enabled["value"] = True
            auto_refresh_btn.icon = ft.Icons.SYNC
            auto_refresh_btn.tooltip = "Disable auto-refresh"
            show_alert("Auto-refresh enabled (every 5 min)", "success")
            if current_city["name"]:
                run_async(auto_refresh_loop())
        page.update()

    # ---------- HEADER ----------
    title = ft.Text("🌤️ Weather App", size=32, weight=ft.FontWeight.BOLD)

    theme_icon = ft.IconButton(
        icon=ft.Icons.DARK_MODE,
        tooltip="Toggle theme",
        icon_size=28,
        on_click=lambda e: toggle_theme(),
    )

    unit_icon = ft.IconButton(
        content=ft.Text("°C", size=18, weight=ft.FontWeight.BOLD),
        tooltip="Switch units",
        on_click=lambda e: toggle_units(),
    )

    auto_refresh_enabled = {"value": False}
    auto_refresh_btn = ft.IconButton(
        icon=ft.Icons.SYNC_DISABLED,
        tooltip="Enable auto-refresh",
        icon_size=28,
        on_click=lambda e: toggle_auto_refresh(),
    )

    header = ft.Row(
        [title, ft.Row([unit_icon, auto_refresh_btn, theme_icon], spacing=10)],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        width=850,
    )

    # ---------- SEARCH + WATCHLIST ----------
    city_input = ft.TextField(
        label="Enter city name",
        width=550,
        height=60,
        on_focus=lambda e: show_recent_history(),
        on_submit=lambda e: fetch_weather(city_input.value),
        autofocus=True,
        hint_text="e.g., London, Tokyo, New York",
        border_color=ft.Colors.BLUE_400,
        prefix_icon=ft.Icons.LOCATION_CITY,
    )

    search_button = ft.ElevatedButton(
        "🔍 Search",
        on_click=lambda e: fetch_weather(city_input.value),
        height=50,
    )
    
    refresh_button = ft.IconButton(
        icon=ft.Icons.REFRESH,
        tooltip="Refresh weather",
        on_click=lambda e: fetch_weather(current_city["name"]) if current_city["name"] else show_alert("No city loaded", "warning"),
    )
    
    add_watchlist_btn = ft.IconButton(
        icon=ft.Icons.BOOKMARK_ADD_OUTLINED,
        tooltip="Add to watchlist",
        on_click=lambda e: add_to_watchlist(),
    )
    
    view_watchlist_btn = ft.IconButton(
        icon=ft.Icons.VIEW_LIST,
        tooltip="Compare watchlist cities",
        on_click=lambda e: run_async(view_watchlist()),
    )
    
    clear_history_btn = ft.IconButton(
        icon=ft.Icons.DELETE_SWEEP,
        tooltip="Clear search history",
        on_click=lambda e: clear_history(),
    )

    search_row = ft.Row(
        [city_input, search_button, refresh_button, add_watchlist_btn, view_watchlist_btn, clear_history_btn],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
    )

    # ---------- OUTPUT AREAS ----------
    weather_card = ft.Container(
        width=850,
        border_radius=16,
        padding=20,
        animate=300,
        content=ft.Column(
            [ft.Text("Search for a city to see weather information", size=16, color=ft.Colors.GREY_600)],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
    
    forecast_section = ft.Column(spacing=10)
    watchlist_section = ft.Column(spacing=10)
    stats_section = ft.Column(spacing=10)

    # Loading indicator
    loading_indicator = ft.ProgressRing(visible=False, width=40, height=40)

    def update_card_styles():
        """Apply theme-aware background colors."""
        bg_color = ft.Colors.BLUE_50 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_900
        weather_card.bgcolor = bg_color
        for section in [forecast_section, watchlist_section, stats_section]:
            for ctrl in section.controls:
                if isinstance(ctrl, ft.Container):
                    ctrl.bgcolor = bg_color
        page.update()

    # ---------- LAYOUT ----------
    layout = ft.Column(
        [
            header,
            ft.Divider(),
            search_row,
            ft.Row([loading_indicator], alignment=ft.MainAxisAlignment.CENTER),
            weather_card,
            stats_section,
            ft.Divider(),
            forecast_section,
            watchlist_section,
        ],
        spacing=15,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    page.add(layout)

    # ---------- EVENT HANDLERS ----------
    def show_recent_history():
        recent = history_service.get_history()
        if not recent:
            return
        city_input.suffix = ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(
                    text=c,
                    on_click=lambda e, city=c: fill_city(city)
                ) for c in recent
            ]
        )
        page.update()

    def fill_city(city):
        city_input.value = city
        page.update()
        fetch_weather(city)

    def clear_history():
        """Clear search history"""
        history_service.clear_history()
        show_alert("Search history cleared", "success")
        city_input.suffix = None
        page.update()

    def add_to_watchlist():
        city_name = (city_input.value or "").strip()
        if not city_name:
            show_alert("Enter a city before adding to watchlist.", "warning")
            return
        
        if watchlist_service.city_exists(city_name):
            show_alert(f"{city_name.title()} is already in your watchlist.", "info")
            return
        
        watchlist_service.add_city(city_name)
        show_alert(f"{city_name.title()} added to watchlist ✅", "success")

    async def view_watchlist():
        cities = watchlist_service.get_watchlist()
        if not cities:
            show_alert("Your watchlist is empty.", "info")
            watchlist_section.controls = []
            page.update()
            return

        watchlist_section.controls = [
            ft.Row(
                [
                    ft.Text("🌍 City Comparison", size=20, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.CLEAR_ALL,
                        tooltip="Clear all watchlist",
                        on_click=lambda e: clear_watchlist(),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        ]
        page.update()

        async def fetch_city(city):
            try:
                data = await weather_service.get_weather(city)
                name = data.get("name", city)
                main = data.get("main", {})
                weather = data.get("weather", [{}])[0]
                temp = main.get("temp", "N/A")
                feels_like = main.get("feels_like", "N/A")
                cond = weather.get("description", "N/A").capitalize()
                icon = weather.get("icon", "01d")
                icon_url = f"https://openweathermap.org/img/wn/{icon}@2x.png"
                
                color = ft.Colors.BLUE_100 if "clear" in cond.lower() else (
                    ft.Colors.GREY_300 if "cloud" in cond.lower() else ft.Colors.BLUE_200)

                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(name, size=16, weight=ft.FontWeight.BOLD),
                            ft.Image(src=icon_url, width=60, height=60),
                            ft.Text(f"{temp}°{('C' if Config.UNITS == 'metric' else 'F')}", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Feels like: {feels_like}°", size=12, color=ft.Colors.GREY_700),
                            ft.Text(cond, size=14),
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.OPEN_IN_NEW,
                                        tooltip="View details",
                                        on_click=lambda e, c=name: fetch_weather(c),
                                        icon_size=20,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        tooltip="Remove from watchlist",
                                        on_click=lambda e, c=name: remove_from_watchlist(c),
                                        icon_size=20,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    width=160,
                    height=240,
                    bgcolor=color if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_800,
                    border_radius=12,
                    padding=10,
                    animate=300,
                )
            except Exception as e:
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(f"{city}", size=14, weight=ft.FontWeight.BOLD),
                            ft.Icon(ft.Icons.ERROR_OUTLINE, size=40, color=ft.Colors.RED),
                            ft.Text("Error loading", size=12),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Remove",
                                on_click=lambda e, c=city: remove_from_watchlist(c),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    width=160,
                    height=240,
                    bgcolor=ft.Colors.RED_100 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.RED_900,
                    border_radius=12,
                    padding=10,
                )

        results = await asyncio.gather(*(fetch_city(c) for c in cities))
        watchlist_section.controls.extend([ft.Row(results, wrap=True, spacing=10)])
        page.update()

    def clear_watchlist():
        """Clear entire watchlist"""
        watchlist_service.clear_watchlist()
        watchlist_section.controls = []
        show_alert("Watchlist cleared", "success")
        page.update()

    def remove_from_watchlist(city):
        watchlist_service.remove_city(city)
        show_alert(f"{city} removed from watchlist 🗑️", "info")
        run_async(view_watchlist())

    async def auto_refresh_loop():
        """Auto-refresh weather data every 5 minutes"""
        while auto_refresh_enabled["value"] and current_city["name"]:
            await asyncio.sleep(300)  # 5 minutes
            if auto_refresh_enabled["value"] and current_city["name"]:
                await fetch_and_display(current_city["name"], silent=True)
                show_alert(f"Weather refreshed for {current_city['name']}", "info")

    def get_weather_emoji(condition: str) -> str:
        """Get emoji based on weather condition"""
        condition_lower = condition.lower()
        if "clear" in condition_lower:
            return "☀️"
        elif "cloud" in condition_lower:
            return "☁️"
        elif "rain" in condition_lower:
            return "🌧️"
        elif "snow" in condition_lower:
            return "❄️"
        elif "thunder" in condition_lower or "storm" in condition_lower:
            return "⛈️"
        elif "mist" in condition_lower or "fog" in condition_lower:
            return "🌫️"
        return "🌤️"

    async def fetch_and_display(city: str, silent: bool = False):
        if not silent:
            is_loading["value"] = True
            loading_indicator.visible = True
            weather_card.content.controls = [ft.Text(f"Fetching weather for {city}...", color=ft.Colors.AMBER)]
            page.update()

        try:
            data = await weather_service.get_weather(city)
        except WeatherServiceError as exc:
            show_alert(str(exc), "error")
            is_loading["value"] = False
            loading_indicator.visible = False
            page.update()
            return
        except Exception as exc:
            show_alert(f"Unexpected error: {exc}", "error")
            is_loading["value"] = False
            loading_indicator.visible = False
            page.update()
            return

        # Extract data
        name = data.get("name", city)
        sys = data.get("sys", {})
        country = sys.get("country", "")
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        coord = data.get("coord", {})

        temp = main.get("temp", "N/A")
        feels_like = main.get("feels_like", "N/A")
        temp_min = main.get("temp_min", "N/A")
        temp_max = main.get("temp_max", "N/A")
        humidity = main.get("humidity", "N/A")
        condition = weather.get("description", "N/A").capitalize()
        wind_speed = wind.get("speed", "N/A")
        wind_deg = wind.get("deg", "N/A")
        pressure = main.get("pressure", "N/A")
        clouds = data.get("clouds", {}).get("all", "N/A")
        visibility = data.get("visibility", "N/A")
        icon_code = weather.get("icon", "01d")
        lat = coord.get("lat", "N/A")
        lon = coord.get("lon", "N/A")
        
        # Get sunrise/sunset
        sunrise = sys.get("sunrise", None)
        sunset = sys.get("sunset", None)
        sunrise_time = datetime.fromtimestamp(sunrise).strftime("%H:%M") if sunrise else "N/A"
        sunset_time = datetime.fromtimestamp(sunset).strftime("%H:%M") if sunset else "N/A"

        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        weather_icon = ft.Image(src=icon_url, width=100, height=100)
        weather_emoji = get_weather_emoji(condition)

        # Store current city
        current_city["name"] = name

        # --- Weather alerts ---
        if isinstance(temp, (int, float)):
            if temp > 35:
                show_alert(f"🔥 Hot weather alert! {temp}°C", "alert")
            elif temp < 5:
                show_alert(f"❄️ Cold weather alert! {temp}°C", "alert")
        
        if "storm" in condition.lower() or "thunder" in condition.lower():
            show_alert("⛈️ Storm alert! Stay safe!", "alert")

        # --- Dynamic background gradient ---
        bg_gradient = ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=(
                [ft.Colors.LIGHT_BLUE_200, ft.Colors.BLUE_100]
                if "clear" in condition.lower()
                else [ft.Colors.GREY_400, ft.Colors.BLUE_GREY_200]
                if "cloud" in condition.lower()
                else [ft.Colors.BLUE_GREY_600, ft.Colors.BLUE_GREY_300]
                if "rain" in condition.lower()
                else [ft.Colors.INDIGO_200, ft.Colors.BLUE_300]
            ),
        )

        weather_card.bgcolor = None
        weather_card.gradient = bg_gradient

        # Unit symbol
        unit_symbol = 'C' if Config.UNITS == 'metric' else 'F'
        speed_unit = 'm/s' if Config.UNITS == 'metric' else 'mph'

        weather_card.content.controls = [
            ft.Text(f"{weather_emoji} {name}, {country}", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(f"📍 {lat}, {lon}", size=12, color=ft.Colors.GREY_700),
            weather_icon,
            ft.Text(condition, size=18, italic=True),
            ft.Text(
                f"{temp}°{unit_symbol}",
                size=48,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.BLUE_900,
            ),
            ft.Text(f"Feels like {feels_like}°{unit_symbol}", size=16, color=ft.Colors.GREY_800),
            ft.Text(f"Min: {temp_min}° | Max: {temp_max}°", size=14, color=ft.Colors.GREY_700),
            ft.Divider(height=20),
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.WATER_DROP, size=20),
                            ft.Text(f"{humidity}%", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text("Humidity", size=12),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.AIR, size=20),
                            ft.Text(f"{wind_speed}", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text(speed_unit, size=12),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.COMPRESS, size=20),
                            ft.Text(f"{pressure}", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text("hPa", size=12),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.CLOUD, size=20),
                            ft.Text(f"{clouds}%", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text("Clouds", size=12),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
        ]

        # --- Additional Stats Section ---
        stats_section.controls = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Icon(ft.Icons.VISIBILITY, size=30, color=ft.Colors.BLUE_700),
                                ft.Text("Visibility", size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{visibility/1000 if isinstance(visibility, (int, float)) else 'N/A'} km", size=16),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Icon(ft.Icons.EXPLORE, size=30, color=ft.Colors.ORANGE_700),
                                ft.Text("Wind Direction", size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{wind_deg}°", size=16),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Icon(ft.Icons.WB_SUNNY, size=30, color=ft.Colors.AMBER_700),
                                ft.Text("Sunrise", size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(sunrise_time, size=16),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Icon(ft.Icons.NIGHTS_STAY, size=30, color=ft.Colors.INDIGO_700),
                                ft.Text("Sunset", size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(sunset_time, size=16),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                bgcolor=ft.Colors.BLUE_50 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_900,
                border_radius=12,
                padding=15,
                width=850,
            )
        ]

        is_loading["value"] = False
        loading_indicator.visible = False
        page.update()

        history_service.add_city(name)
        run_async(fetch_and_display_forecast(city))

    async def fetch_and_display_forecast(city: str):
        try:
            data = await weather_service.get_forecast(city)
        except Exception:
            show_alert("Could not load forecast.", "warning")
            return

        forecast_list = data.get("list", [])
        if not forecast_list:
            return

        forecast_section.controls = [
            ft.Text("📅 5-Day Forecast", size=22, weight=ft.FontWeight.BOLD)
        ]
        displayed_dates = set()

        for item in forecast_list:
            dt_txt = item.get("dt_txt", "")
            date = dt_txt.split(" ")[0]
            if date in displayed_dates:
                continue
            displayed_dates.add(date)

            main = item.get("main", {})
            weather = item.get("weather", [{}])[0]
            temp = main.get("temp", "N/A")
            temp_min = main.get("temp_min", "N/A")
            temp_max = main.get("temp_max", "N/A")
            cond = weather.get("description", "N/A").capitalize()
            icon = weather.get("icon", "01d")
            icon_url = f"https://openweathermap.org/img/wn/{icon}@2x.png"

            # Parse date for better display
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                day_name = date_obj.strftime("%a")
                display_date = f"{day_name}, {date_obj.strftime('%b %d')}"
            except:
                display_date = date

            color = (
                ft.Colors.LIGHT_BLUE_100 if "clear" in cond.lower()
                else ft.Colors.GREY_300 if "cloud" in cond.lower()
                else ft.Colors.INDIGO_100
            )

            unit_symbol = 'C' if Config.UNITS == 'metric' else 'F'

            card = ft.Container(
                width=150,
                bgcolor=color if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_800,
                border_radius=12,
                padding=12,
                animate=300,
                content=ft.Column(
                    [
                        ft.Text(display_date, size=14, weight=ft.FontWeight.W_600),
                        ft.Image(src=icon_url, width=60, height=60),
                        ft.Text(f"{temp}°{unit_symbol}", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(f"↓{temp_min}° ↑{temp_max}°", size=12, color=ft.Colors.GREY_700),
                        ft.Text(cond, size=12, italic=True),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
            )
            forecast_section.controls.append(card)

        forecast_section.controls.append(
            ft.Row(
                forecast_section.controls[1:],
                scroll=ft.ScrollMode.AUTO,
                spacing=10,
            )
        )
        forecast_section.controls = forecast_section.controls[:1] + [forecast_section.controls[-1]]
        page.update()

    def fetch_weather(city=None):
        city_name = (city or city_input.value or "").strip()
        if not city_name:
            show_alert("Please enter a city name.", "warning")
            return
        run_async(fetch_and_display(city_name))

    page.update()


if __name__ == "__main__":
    ft.app(target=main)