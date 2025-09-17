import flet as ft
from database import init_db
from app_logic import display_contacts, add_contact

def main(page: ft.Page):
    page.title = "Contact Book"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 420
    page.window_height = 650
    page.theme_mode = ft.ThemeMode.LIGHT

    db_conn = init_db()

    # Theme switch
    theme_switch = ft.Switch(label="Dark Mode", value=False)
    def toggle_theme(e):
        page.theme_mode = ft.ThemeMode.DARK if theme_switch.value else ft.ThemeMode.LIGHT
        page.update()

    theme_switch.on_change = toggle_theme

    # Inputs
    name_input = ft.TextField(label="Name", width=350)
    phone_input = ft.TextField(label="Phone", width=350)
    email_input = ft.TextField(label="Email", width=350)
    inputs = (name_input, phone_input, email_input)

    # Search
    search_input = ft.TextField(label="Search", width=350)

    contacts_list_view = ft.ListView(expand=1, spacing=10, auto_scroll=True)

    add_button = ft.ElevatedButton(
        text="Add Contact",
        on_click=lambda e: add_contact(page, inputs, contacts_list_view, db_conn),
    )

    search_input.on_change = lambda e: display_contacts(page, contacts_list_view, db_conn, e.control.value)

    page.add(
        ft.Column(
            [
                theme_switch,
                ft.Text("Enter Contact Details:", size=20, weight=ft.FontWeight.BOLD),
                name_input,
                phone_input,
                email_input,
                add_button,
                ft.Divider(),
                search_input,
                ft.Text("Contacts:", size=20, weight=ft.FontWeight.BOLD),
                contacts_list_view,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    )

    display_contacts(page, contacts_list_view, db_conn)

if __name__ == "__main__":
    ft.app(target=main)
