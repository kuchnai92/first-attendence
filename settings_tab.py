import flet as ft

def get_settings_view(page: ft.Page, db, show_snack):
    COLOR_PRIMARY = "#03a9f4"
    COLOR_GREY_300 = "#e0e0e0"
    
    settings_dynamic_content = ft.Column()

    def load_trash_ui():
        settings_dynamic_content.controls.clear()
        trash_items = db.get_trash_items()
        
        header_row = [
            ft.DataColumn(ft.Text("Name")), ft.DataColumn(ft.Text("Deleted Date")),
            ft.DataColumn(ft.Text("Salary")), ft.DataColumn(ft.Text("Actions")),
        ]
        
        rows = []
        for t in trash_items:
            trash_id = t[0]; name = t[1]; date_deleted = t[8]
            
            def restore_click(e, tid=trash_id):
                db.restore_worker(tid)
                load_trash_ui()
                show_snack(page, "Worker Restored Successfully", "green")

            def perm_delete_click(e, tid=trash_id):
                db.permanent_delete_trash(tid)
                load_trash_ui()
                show_snack(page, "Permanently Deleted", "red")

            cells = [
                ft.DataCell(ft.Text(name, weight="bold")), ft.DataCell(ft.Text(date_deleted)), ft.DataCell(ft.Text(str(t[7]))),
                ft.DataCell(ft.Row([
                    ft.IconButton(icon=ft.Icons.RESTORE, icon_color="green", tooltip="Restore", on_click=restore_click),
                    ft.IconButton(icon=ft.Icons.DELETE_FOREVER, icon_color="red", tooltip="Delete Forever", on_click=perm_delete_click)
                ]))
            ]
            rows.append(ft.DataRow(cells=cells))

        if not rows:
            settings_dynamic_content.controls.append(ft.Text("Recycle Bin is empty.", italic=True))
        else:
            settings_dynamic_content.controls.append(
                ft.Row([ft.DataTable(columns=header_row, rows=rows, border=ft.border.all(1, COLOR_GREY_300))], scroll=ft.ScrollMode.ALWAYS, expand=True)
            )
        
        def empty_all(e):
            db.empty_trash()
            load_trash_ui()
            show_snack(page, "Trash Emptied", "blue")

        if rows:
             settings_dynamic_content.controls.append(
                 ft.FilledButton("Empty Trash", icon=ft.Icons.DELETE_SWEEP, bgcolor="red", color="white", on_click=empty_all)
             )
        page.update()

    def load_general_settings():
        settings_dynamic_content.controls.clear()
        
        f_entry = ft.TextField(label="Factory Entry Time", value=db.get_setting("factory_entry_time", "08:00 AM"), width=250, border_radius=8, hint_text="08:00 AM", prefix_icon=ft.Icons.LOGIN)
        f_close = ft.TextField(label="Factory Closing Time", value=db.get_setting("factory_closing_time", "06:00 PM"), width=250, border_radius=8, hint_text="06:00 PM", prefix_icon=ft.Icons.LOGOUT)
        
        def save_settings(e):
            db.set_setting("factory_entry_time", f_entry.value)
            db.set_setting("factory_closing_time", f_close.value)
            show_snack(page, "Factory Settings Saved Successfully!", "green")

        save_btn = ft.ElevatedButton("Save Factory Times", icon=ft.Icons.SAVE, bgcolor="#10B981", color="white", on_click=save_settings)
        
        settings_dynamic_content.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.FACTORY, color="#2D5B7A"), ft.Text("Factory Time Settings", weight="bold", size=18, color="#2D5B7A")]),
                    ft.Text("Set the official factory shift timings. These are used globally to determine how many minutes a worker was late, or if they left early.", color="grey", size=13),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row([f_entry, f_close], spacing=20),
                    ft.Divider(height=10, color="transparent"),
                    save_btn
                ]), padding=20, border=ft.border.all(1, COLOR_GREY_300), border_radius=10, bgcolor="white"
            )
        )
        page.update()

    settings_view = ft.Container(
        content=ft.Column([
            ft.Text("Settings", size=20, weight="bold", color=COLOR_PRIMARY),
            ft.Row([
                ft.FilledButton("General", icon=ft.Icons.SETTINGS, on_click=lambda e: load_general_settings()),
                ft.FilledButton("Workers Trash", icon=ft.Icons.DELETE, on_click=lambda e: load_trash_ui(), bgcolor="orange", color="white")
            ]),
            ft.Divider(), ft.Column([settings_dynamic_content], scroll=ft.ScrollMode.ALWAYS, expand=True)
        ], expand=True), visible=False
    )

    return settings_view, load_general_settings