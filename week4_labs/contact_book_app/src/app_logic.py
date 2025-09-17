import flet as ft
from database import get_all_contacts_db, add_contact_db, delete_contact_db

def display_contacts(page, contacts_list_view, db_conn, search_term=""):
    """Displays all contacts (filtered if search_term provided)."""
    contacts_list_view.controls.clear()
    contacts = get_all_contacts_db(db_conn, search_term)

    for contact_id, name, phone, email in contacts:
        def handle_delete(e, cid=contact_id):
            confirm_delete(page, cid, db_conn, contacts_list_view)

        contacts_list_view.controls.append(
            ft.Card(
                elevation=2,
                content=ft.Container(
                    padding=10,
                    content=ft.Column(
                        [
                            ft.Text(name, size=18, weight=ft.FontWeight.BOLD),
                            ft.Row([ft.Icon(ft.Icons.PHONE), ft.Text(phone or "—")]),
                            ft.Row([ft.Icon(ft.Icons.EMAIL), ft.Text(email or "—")]),
                            ft.TextButton(
                                "Delete",
                                on_click=handle_delete,
                                style=ft.ButtonStyle(
                                    foreground_color="red"  # ✅ Use string color instead of ft.colors.RED
                                ),
                            ),
                        ]
                    ),
                ),
            )
        )
    page.update()

def add_contact(page, inputs, contacts_list_view, db_conn):
    """Adds a new contact with validation."""
    name_input, phone_input, email_input = inputs

    if not name_input.value.strip():
        name_input.error_text = "Name cannot be empty"
        page.update()
        return
    else:
        name_input.error_text = None

    add_contact_db(
        db_conn,
        name_input.value.strip(),
        phone_input.value.strip(),
        email_input.value.strip(),
    )
    for field in inputs:
        field.value = ""

    display_contacts(page, contacts_list_view, db_conn)
    page.update()

def confirm_delete(page, contact_id, db_conn, contacts_list_view):
    """Show confirmation dialog before deletion."""
    def confirm(e):
        delete_contact_db(db_conn, contact_id)
        dlg.open = False
        display_contacts(page, contacts_list_view, db_conn)
        page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirm Delete"),
        content=ft.Text("Are you sure you want to delete this contact?"),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: close_dialog(page, dlg)),
            ft.TextButton("Yes", on_click=confirm),
        ],
    )
    page.dialog = dlg
    dlg.open = True
    page.update()

def close_dialog(page, dlg):
    dlg.open = False
    page.update()
