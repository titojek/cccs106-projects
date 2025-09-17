import flet as ft
from db_connection import connect_db


def main(page: ft.Page):
    page.window.title = "User Login"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.AMBER_ACCENT
    page.window.frameless = True
    page.window.height = 350
    page.window.width = 400
    page.window.resizable = False
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.always_on_top = True
    page.window.center()

    title = ft.Text("User Login", weight=ft.FontWeight.BOLD, size=20, font_family="Arial", color=ft.Colors.BLACK)
    usernameTF = ft.TextField(disabled=False, label="User name", hint_text="Enter your user name", helper_text="This is your unique identifier", autofocus=True, icon=ft.Icons.PERSON, width=300, fill_color=ft.Colors.LIGHT_BLUE_ACCENT, color=ft.Colors.BLACK)
    passwordTF = ft.TextField(disabled=False, label="Password", hint_text="Enter your password", helper_text="This is your secret key", autofocus=True, icon=ft.Icons.PASSWORD, width=300, fill_color=ft.Colors.LIGHT_BLUE_ACCENT, can_reveal_password=True, password=True)

    def show_dialog(icon, title, content):
        dialog = ft.AlertDialog(icon=icon, title=ft.Text(title, text_align=ft.TextAlign.CENTER), content=ft.Text(content, text_align=ft.TextAlign.CENTER), actions=[ft.TextButton("Ok", on_click=lambda e: close_dialog(dialog))])
        page.dialog = dialog
        dialog.open = True
        page.open(dialog)
        page.update()
    
    def close_dialog(dialog):
        dialog.open = False
        page.update()

    async def login_click(e):
        if usernameTF.value == "" or passwordTF.value == "":
            show_dialog(ft.Icon(ft.Icons.INFO_ROUNDED, color=ft.Colors.BLUE), "Input Error", "Please enter username and password")
            return
        try:
            connection = connect_db()
            cursor = connection.cursor()

            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (usernameTF.value, passwordTF.value))
            res = cursor.fetchone() 

            if res: show_dialog(ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=ft.Colors.GREEN), "Login Successful", f"Welcome, {usernameTF.value}!")
            else: show_dialog(ft.Icon(ft.Icons.ERROR_ROUNDED, ft.Colors.RED), "Login Failed", "Invalid username or password")

        except: show_dialog(None, "Database Error", "An error occurred while connecting to the database")
    
    login_button = ft.ElevatedButton("Login", icon=ft.Icons.EXIT_TO_APP, on_click=login_click, width=100)

    page.add(
        title,
        ft.Container(
            ft.Column(
            [
                usernameTF,
                passwordTF
            ],
                spacing=20
            )
        ),
        ft.Container(
            login_button,
            alignment=ft.alignment.top_right,
            margin=ft.margin.only(0, 20, 40, 0)
        )
    )


ft.app(main)