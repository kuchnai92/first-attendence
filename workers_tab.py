import flet as ft
import requests
from requests.auth import HTTPDigestAuth
import threading

def get_workers_view(page: ft.Page, db, show_snack, open_dialog_safe, reload_weekly_cb, reload_monthly_cb):
    COLOR_PRIMARY = "#2D5B7A"    
    COLOR_TEXT_MAIN = "#111827"  
    COLOR_TEXT_SUB = "#4B5563"   
    COLOR_BORDER = "#E5E7EB"
    COLOR_BG_LIGHT = "#F3F4F6"

    # --- DEVICE CONFIGURATION ---
    DEVICE_IP = "192.168.100.68" 
    USERNAME = "admin"
    PASSWORD = "YourExactPassword" # Replace with your actual password
    
    # Initialize Biometric Table safely
    try:
        db.cursor.execute("CREATE TABLE IF NOT EXISTS worker_creds (custom_id INTEGER PRIMARY KEY, face INTEGER, fp INTEGER, card INTEGER)")
        db.conn.commit()
    except Exception:
        pass

    workers_list = ft.ListView(spacing=0, expand=True)
    filter_state = {"mode": "All"}
    stats_container = ft.Container()
    current_edit_id = [None] 
    dialog_mode = ["Add"]
    is_syncing = [False]

    # --- HIKVISION BACKGROUND TASKS ---
    
    def sync_hikvision_in_background():
        if is_syncing[0]: return
        is_syncing[0] = True
        
        sync_btn.text = "Syncing..."
        sync_btn.icon = ft.Icons.HOURGLASS_TOP
        sync_btn.bgcolor = "grey"
        page.update()

        url = f"http://{DEVICE_IP}/ISAPI/AccessControl/UserInfo/Search?format=json"
        payload = {"UserInfoSearchCond": {"searchID": "1", "searchResultPosition": 0, "maxResults": 1000}}
        
        try:
            response = requests.post(url, auth=HTTPDigestAuth(USERNAME, PASSWORD), json=payload, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if "UserInfoSearch" in data and "UserInfo" in data["UserInfoSearch"]:
                    users = data["UserInfoSearch"]["UserInfo"]
                    
                    existing_workers = {w[1].lower() for w in db.get_workers()}
                    existing_cids = {str(w[8]) for w in db.get_workers() if w[8]}

                    added_count = 0
                    for u in users:
                        name = u.get("name", "Unknown")
                        emp_no = u.get("employeeNo", "")
                        
                        if emp_no.isdigit():
                            cid = int(emp_no)
                            
                            has_face = 1 if u.get('numOfFace', 0) > 0 else 0
                            has_fp = 1 if (u.get('numOfFP', 0) > 0 or u.get('numOfFingerPrint', 0) > 0) else 0
                            has_card = 1 if (u.get('ValidCardNum', 0) > 0 or u.get('numOfCard', 0) > 0) else 0
                            
                            db.cursor.execute("INSERT OR REPLACE INTO worker_creds (custom_id, face, fp, card) VALUES (?, ?, ?, ?)", (cid, has_face, has_fp, has_card))
                            db.conn.commit()

                            if name.lower() not in existing_workers and emp_no not in existing_cids:
                                db.add_worker(name, "", "", "", "Active", "Weekly", 0.0, cid, "Device Import")
                                added_count += 1
                    
                    show_snack(page, f"Sync Complete! Added {added_count} new workers.", "green")
            else:
                show_snack(page, f"Device Sync Failed (Error {response.status_code})", "red")
        except Exception:
            show_snack(page, "Sync Failed: Device not reachable or Auth Error.", "red")
            
        is_syncing[0] = False
        sync_btn.text = "Sync Device"
        sync_btn.icon = ft.Icons.SYNC
        sync_btn.bgcolor = "#F59E0B"
        load_workers_ui()

    def push_add_to_device(name, custom_id):
        try:
            url = f"http://{DEVICE_IP}/ISAPI/AccessControl/UserInfo/Record?format=json"
            payload = {
                "UserInfo": {
                    "employeeNo": str(custom_id),
                    "name": name,
                    "userType": "normal",
                    "Valid": {"enable": True, "beginTime": "2020-01-01T00:00:00", "endTime": "2035-12-31T23:59:59"}
                }
            }
            requests.post(url, auth=HTTPDigestAuth(USERNAME, PASSWORD), json=payload, timeout=3)
        except Exception:
            pass 

    def push_delete_to_device(custom_id):
        try:
            url = f"http://{DEVICE_IP}/ISAPI/AccessControl/UserInfo/Delete?format=json"
            payload = {
                "UserInfoDetail": {
                    "mode": "byEmployeeNo",
                    "EmployeeNoCond": {"EmployeeNoList": [{"employeeNo": str(custom_id)}]}
                }
            }
            requests.put(url, auth=HTTPDigestAuth(USERNAME, PASSWORD), json=payload, timeout=3)
        except Exception:
            pass

    # --- UI HELPER FUNCTIONS ---

    def with_opacity(opacity, hex_color):
        alpha = hex(int(opacity * 255))[2:].zfill(2).upper()
        base_color = hex_color.lstrip('#')
        if len(base_color) == 8: base_color = base_color[2:]
        return f"#{alpha}{base_color}"

    input_style = {
        "border_radius": 8, 
        "filled": True, 
        "fill_color": COLOR_BG_LIGHT, 
        "border_color": COLOR_PRIMARY, 
        "content_padding": 12 
    }

    search_input = ft.TextField(
        label="Search Name or ID...", width=250, border_radius=8, content_padding=12,
        border_color="#D1D5DB", bgcolor="#F9FAFB", height=40, prefix_icon=ft.Icons.SEARCH,
        on_change=lambda e: load_workers_ui()
    )

    name_input = ft.TextField(label="Full Name", width=250, prefix_icon=ft.Icons.PERSON, **input_style)
    age_input = ft.TextField(label="Age", width=100, **input_style)
    number_input = ft.TextField(label="Phone Number", width=250, prefix_icon=ft.Icons.PHONE, **input_style)
    address_input = ft.TextField(label="Address", width=360, prefix_icon=ft.Icons.LOCATION_ON, **input_style)
    
    custom_id_prefix = ft.Text("W-", weight="bold", size=16, color=COLOR_TEXT_SUB)
    custom_id_input = ft.TextField(label="ID Num", width=100, keyboard_type=ft.KeyboardType.NUMBER, **input_style)
    
    id_row = ft.Row([
        ft.Container(content=custom_id_prefix, padding=ft.padding.only(left=10, right=5)),
        custom_id_input
    ], spacing=0, alignment=ft.MainAxisAlignment.START)

    factory_menu = ft.PopupMenuButton(icon=ft.Icons.ARROW_DROP_DOWN, tooltip="Recent Factories")
    factory_input = ft.TextField(label="Factory / Location", width=180, suffix=factory_menu, prefix_icon=ft.Icons.FACTORY, **input_style)

    def on_factory_select(e):
        if hasattr(e.control, 'data'):
            factory_input.value = e.control.data
            page.update()

    def update_factory_menu():
        factories = db.get_distinct_factory()
        items = []
        for f in factories:
            items.append(ft.PopupMenuItem(content=ft.Text(f), data=f, on_click=on_factory_select))
        if not items:
            items.append(ft.PopupMenuItem(content=ft.Text("No history", color="grey")))
        factory_menu.items = items

    def on_role_select(e):
        if hasattr(e.control, 'data'):
            status_input.value = e.control.data
            page.update()

    status_menu = ft.PopupMenuButton(icon=ft.Icons.ARROW_DROP_DOWN, tooltip="Recent Roles")
    status_input = ft.TextField(label="Role / Work Status", width=195, suffix=status_menu, prefix_icon=ft.Icons.WORK, **input_style)

    def update_status_menu():
        roles = db.get_distinct_status()
        items = []
        for r in roles:
            items.append(ft.PopupMenuItem(content=ft.Text(r), data=r, on_click=on_role_select))
        if not items:
            items.append(ft.PopupMenuItem(content=ft.Text("No history", color="grey")))
        status_menu.items = items

    def auto_set_next_id():
        workers = db.get_workers(salary_type_dd.value)
        max_id = 0
        for w in workers:
            try:
                cid = int(w[8]) if w[8] else 0
                if cid > max_id: max_id = cid
            except Exception: pass
        custom_id_input.value = str(max_id + 1)

    def on_type_change(e):
        if e is not None and hasattr(e, "control"):
            salary_type_dd.value = e.control.value
            
        custom_id_prefix.value = "W-" if salary_type_dd.value == "Weekly" else "M-"
        
        if dialog_mode[0] == "Add":
            auto_set_next_id()
            
        if worker_dialog in page.overlay:
            page.update()

    salary_type_dd = ft.Dropdown(
        label="Salary Type", options=[ft.dropdown.Option("Weekly"), ft.dropdown.Option("Monthly")],
        value="Weekly", width=150, border_radius=8, filled=True, fill_color=COLOR_BG_LIGHT, border_color=COLOR_PRIMARY, content_padding=12
    )
    salary_type_dd.on_change = on_type_change

    salary_input = ft.TextField(label="Salary", keyboard_type=ft.KeyboardType.NUMBER, width=150, prefix_icon=ft.Icons.ATTACH_MONEY, **input_style)

    def close_dialog(e):
        worker_dialog.open = False
        page.update()

    def is_id_duplicate(target_cid, target_type, exclude_worker_id=None):
        workers = db.get_workers(target_type)
        for w in workers:
            if w[8] == target_cid: 
                if exclude_worker_id and w[0] == exclude_worker_id: continue 
                return True
        return False

    # --- ULTRA-FAST CRUD ACTIONS ---
    def add_worker_action(e):
        cid = int(custom_id_input.value) if custom_id_input.value else None
        if cid is not None and is_id_duplicate(cid, salary_type_dd.value):
            prefix = "W-" if salary_type_dd.value == "Weekly" else "M-"
            show_snack(page, f"Error: ID {prefix}{cid} is already assigned!", "red")
            return

        # 1. Instantly Close the Dialog
        close_dialog(None)
        show_snack(page, "Worker Added & Pushed to Device!", "green")

        # 2. Run Database & Network in Background
        def process_add():
            try:
                db.add_worker(
                    name_input.value, age_input.value, number_input.value, address_input.value, 
                    status_input.value, salary_type_dd.value, float(salary_input.value if salary_input.value else 0),
                    cid, factory_input.value
                )
                if cid is not None:
                    push_add_to_device(name_input.value, cid)
                
                # Refresh UI only after math is done
                load_workers_ui()
                reload_weekly_cb()
                reload_monthly_cb()
            except Exception as ex:
                pass
        
        page.run_thread(process_add)

    def update_worker_action(e):
        cid = int(custom_id_input.value) if custom_id_input.value else 0
        if is_id_duplicate(cid, salary_type_dd.value, exclude_worker_id=current_edit_id[0]):
            prefix = "W-" if salary_type_dd.value == "Weekly" else "M-"
            show_snack(page, f"Error: ID {prefix}{cid} is already assigned!", "red")
            return

        # 1. Instantly Close the Dialog
        close_dialog(None)
        show_snack(page, "Worker Updated Successfully!", "green")

        # 2. Run Database & Network in Background
        def process_edit():
            try:
                db.update_worker(
                    current_edit_id[0], name_input.value, age_input.value, number_input.value, 
                    address_input.value, status_input.value, salary_type_dd.value, float(salary_input.value if salary_input.value else 0),
                    cid, factory_input.value
                )
                if cid:
                    push_add_to_device(name_input.value, cid)
                
                load_workers_ui()
                reload_weekly_cb()
                reload_monthly_cb()
            except Exception as ex:
                pass
                
        page.run_thread(process_edit)

    def handle_dialog_submit(e):
        if dialog_mode[0] == "Add": add_worker_action(e)
        else: update_worker_action(e)

    name_input.on_submit = handle_dialog_submit
    age_input.on_submit = handle_dialog_submit
    number_input.on_submit = handle_dialog_submit
    address_input.on_submit = handle_dialog_submit
    status_input.on_submit = handle_dialog_submit
    salary_input.on_submit = handle_dialog_submit
    custom_id_input.on_submit = handle_dialog_submit
    factory_input.on_submit = handle_dialog_submit

    save_btn = ft.ElevatedButton("Save Worker", icon=ft.Icons.SAVE, bgcolor="#2E7D32", color="white")
    cancel_btn = ft.TextButton("Cancel", on_click=close_dialog)

    worker_dialog = ft.AlertDialog(
        title=ft.Row([ft.Icon(ft.Icons.PERSON, color=COLOR_PRIMARY), ft.Text("Add New Worker", color=COLOR_PRIMARY, weight="bold")]),
        content=ft.Container(
            content=ft.Column([
                ft.Row([id_row, salary_type_dd], spacing=10),
                ft.Row([name_input, age_input], spacing=10),
                ft.Row([number_input, factory_input], spacing=10),
                address_input,
                ft.Row([status_input, salary_input], spacing=10),
            ], tight=True, spacing=10),
            width=420, padding=ft.padding.only(top=5, bottom=5)
        ),
        actions=[cancel_btn, save_btn], actions_alignment=ft.MainAxisAlignment.END, shape=ft.RoundedRectangleBorder(radius=12),
    )

    if worker_dialog not in page.overlay: page.overlay.append(worker_dialog)

    def open_add_dialog(e):
        dialog_mode[0] = "Add"
        worker_dialog.title.controls[1].value = "Add New Worker"
        worker_dialog.title.controls[0].name = ft.Icons.PERSON_ADD
        
        name_input.value = ""; age_input.value = ""; number_input.value = ""
        address_input.value = ""; status_input.value = ""; salary_input.value = ""; factory_input.value = ""
        
        on_type_change(None) 
        save_btn.text = "Save Worker"
        save_btn.on_click = add_worker_action
        worker_dialog.open = True; page.update()

    def open_history_dialog(e, w_id, w_name, field_type):
        title_text = "Salary History" if field_type == "salary" else "Role/Status History" if field_type == "status" else "Salary Type History"
        table_container = ft.Column(scroll=ft.ScrollMode.AUTO)

        def load_history_table():
            history_data = db.get_worker_history(w_id, field_type)
            rows = []
            if not history_data:
                rows = [ft.DataRow([ft.DataCell(ft.Text("No changes recorded.", italic=True, color="grey")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text(""))])]
            else:
                for h_id, date_changed, old_v, new_v in history_data:
                    date_only = date_changed.split(" ")[0]
                    def delete_record(e, hist_id=h_id):
                        db.delete_worker_history(hist_id); load_history_table(); show_snack(page, "History record deleted", "orange")
                    del_btn = ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", icon_size=18, on_click=delete_record, tooltip="Delete Record")
                    display_old_v = f"{float(old_v):,.0f}" if field_type == 'salary' else str(old_v)
                    display_new_v = f"{float(new_v):,.0f}" if field_type == 'salary' else str(new_v)
                    rows.append(ft.DataRow([ft.DataCell(ft.Text(date_only, size=13)), ft.DataCell(ft.Text(display_old_v, color="red")), ft.DataCell(ft.Text(display_new_v, color="green", weight="bold")), ft.DataCell(del_btn)]))
                    
            table_container.controls.clear()
            table_container.controls.append(ft.DataTable(columns=[ft.DataColumn(ft.Text("Date", weight="bold")), ft.DataColumn(ft.Text("Previous", weight="bold")), ft.DataColumn(ft.Text("Changed To", weight="bold")), ft.DataColumn(ft.Text("Action", weight="bold"))], rows=rows, heading_row_height=40, border=ft.border.all(1, COLOR_BORDER)))
            page.update()

        load_history_table()
        dlg = ft.AlertDialog(title=ft.Text(f"{title_text}: {w_name}", weight="bold"), content=ft.Container(content=table_container, width=550, height=300), actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())])
        open_dialog_safe(page, dlg)

    def create_stat_card(title, value, icon, icon_color, on_click_action, is_active):
        bg_color = with_opacity(0.08, icon_color) if is_active else "white"
        border_color = icon_color if is_active else COLOR_BORDER
        return ft.Container(
            content=ft.Row([
                ft.Container(content=ft.Icon(icon, size=24, color=icon_color), bgcolor=with_opacity(0.15, icon_color), padding=10, border_radius=50),
                ft.Column([ft.Text(title, size=12, color="grey700", weight="w600"), ft.Text(str(value), size=18, weight="bold", color=COLOR_PRIMARY)], spacing=0)
            ]), expand=True, bgcolor=bg_color, padding=10, border_radius=8, border=ft.border.all(2 if is_active else 1, border_color),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0A000000", offset=ft.Offset(0, 1)), on_click=on_click_action 
        )

    def set_filter(mode):
        filter_state["mode"] = mode
        load_workers_ui()

    def load_workers_ui(e=None):
        new_list_controls = []
        
        all_workers_for_counts = db.get_workers()
        total_count = len(all_workers_for_counts)
        weekly_count = sum(1 for w in all_workers_for_counts if w[6] == "Weekly")
        monthly_count = sum(1 for w in all_workers_for_counts if w[6] == "Monthly")

        stats_container.content = ft.Row([
            create_stat_card("Total Workers", total_count, ft.Icons.PEOPLE_ALT, "#3B82F6", lambda e: set_filter("All"), filter_state["mode"] == "All"),
            create_stat_card("Weekly Workers", weekly_count, ft.Icons.CALENDAR_VIEW_WEEK, "#F59E0B", lambda e: set_filter("Weekly"), filter_state["mode"] == "Weekly"),
            create_stat_card("Monthly Workers", monthly_count, ft.Icons.CALENDAR_MONTH, "#10B981", lambda e: set_filter("Monthly"), filter_state["mode"] == "Monthly")
        ], spacing=10)

        filter_val = filter_state["mode"] if filter_state["mode"] != "All" else None
        
        filtered_workers = list(db.get_workers(filter_val))
        filtered_workers.sort(key=lambda w: int(w[8]) if w[8] not in (None, "") else 0)

        try:
            db.cursor.execute("SELECT custom_id, face, fp, card FROM worker_creds")
            creds = {row[0]: {'face': row[1], 'fp': row[2], 'card': row[3]} for row in db.cursor.fetchall()}
        except Exception:
            creds = {}

        query = search_input.value.lower() if search_input.value else ""
        update_status_menu()
        update_factory_menu()
        
        new_list_controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text("ID", width=60, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Name", width=180, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Type", width=90, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Factory", width=120, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Container(expand=True),
                    ft.Text("Salary", width=120, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Role/Status", width=160, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Action", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
                ]), bgcolor=COLOR_BG_LIGHT, padding=ft.padding.symmetric(vertical=8, horizontal=15), border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        )
        
        for index, w in enumerate(filtered_workers):
            w_id = w[0]; w_name = w[1]; w_type = w[6]; w_salary = w[7]; w_custom_id = w[8]; w_factory = w[9] or "N/A"
            display_id = f"W-{w_custom_id}" if w_type == "Weekly" else f"M-{w_custom_id}" 
            
            if query and query not in w_name.lower() and query not in display_id.lower() and query not in w_factory.lower():
                continue

            bio_icons = []
            if w_custom_id and int(w_custom_id) in creds:
                cred_info = creds[int(w_custom_id)]
                if cred_info['face']: bio_icons.append(ft.Icon(ft.Icons.FACE, size=14, color="#3B82F6", tooltip="Face Enrolled"))
                if cred_info['fp']: bio_icons.append(ft.Icon(ft.Icons.FINGERPRINT, size=14, color="#10B981", tooltip="Fingerprint Enrolled"))
                if cred_info['card']: bio_icons.append(ft.Icon(ft.Icons.CREDIT_CARD, size=14, color="#F59E0B", tooltip="Card Enrolled"))

            name_column = ft.Row([
                ft.Text(w_name, weight="bold", color=COLOR_TEXT_MAIN, size=15),
                ft.Row(bio_icons, spacing=2)
            ], width=180, spacing=6, alignment=ft.MainAxisAlignment.START)

            def edit_click(e, worker=w):
                dialog_mode[0] = "Edit"
                current_edit_id[0] = worker[0]
                worker_dialog.title.controls[1].value = "Edit Worker"
                worker_dialog.title.controls[0].name = ft.Icons.EDIT
                name_input.value = worker[1]; age_input.value = worker[2]; number_input.value = worker[3]; address_input.value = worker[4]
                status_input.value = worker[5]; salary_type_dd.value = worker[6]; salary_input.value = str(worker[7]); custom_id_input.value = str(worker[8]); factory_input.value = worker[9]
                on_type_change(None) 
                save_btn.text = "Update Worker"
                save_btn.on_click = update_worker_action
                worker_dialog.open = True; page.update()
            
            def delete_click(e, worker_id=w_id, cid=w_custom_id):
                def confirm_del(e):
                    # 1. Close dialog instantly
                    dlg.open = False
                    page.update()
                    show_snack(page, "Worker Moved to Trash & Deleted from Device", "orange")
                    
                    # 2. Process deletion in background
                    def process_del():
                        db.soft_delete_worker(worker_id)
                        if cid is not None:
                            push_delete_to_device(cid)
                        load_workers_ui()
                        reload_weekly_cb()
                        reload_monthly_cb()
                    
                    page.run_thread(process_del)

                def cancel_del(e):
                    dlg.open = False; page.update()
                
                dlg = ft.AlertDialog(
                    title=ft.Text("Move to Trash?", size=16, weight="bold"),
                    content=ft.Text("This deletes the worker from the app AND the physical attendance device.", size=13),
                    actions=[ft.TextButton("Yes, Delete", on_click=confirm_del, style=ft.ButtonStyle(color="red")), ft.TextButton("No", on_click=cancel_del)]
                )
                open_dialog_safe(page, dlg)

            type_btn = ft.Container(content=ft.Row([ft.Text(w_type, color=COLOR_TEXT_SUB, size=13), ft.Icon(ft.Icons.HISTORY, size=14, color=COLOR_TEXT_SUB)], spacing=4), on_click=lambda e, wid=w_id, wn=w_name: open_history_dialog(e, wid, wn, 'salary_type'), tooltip="View Type History", width=90, ink=True)
            salary_btn = ft.Container(content=ft.Row([ft.Text(f"{w_salary:,.0f}", color="#10B981", weight="bold", size=13), ft.Icon(ft.Icons.HISTORY, size=14, color="#10B981")], spacing=4), on_click=lambda e, wid=w_id, wn=w_name: open_history_dialog(e, wid, wn, 'salary'), tooltip="View Salary History", width=120, ink=True)
            status_btn = ft.Container(content=ft.Row([ft.Text(w[5], color=COLOR_TEXT_SUB, size=13), ft.Icon(ft.Icons.HISTORY, size=14, color=COLOR_TEXT_SUB)], spacing=4), on_click=lambda e, wid=w_id, wn=w_name: open_history_dialog(e, wid, wn, 'status'), tooltip="View Role History", width=160, ink=True)

            def make_hover(idx):
                def hover(e):
                    e.control.bgcolor = "#F1F5F9" if e.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                    e.control.update() 
                return hover

            new_list_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(display_id, width=60, weight="w600", color=COLOR_TEXT_MAIN, size=13),
                        name_column,
                        type_btn, ft.Text(w_factory, width=120, color=COLOR_TEXT_SUB, size=13),
                        ft.Container(expand=True), salary_btn, status_btn,
                        ft.Row([
                            ft.IconButton(icon=ft.Icons.EDIT, icon_color="#3B82F6", on_click=edit_click, tooltip="Edit", icon_size=18, width=32, height=32),
                            ft.IconButton(icon=ft.Icons.DELETE, icon_color="#EF4444", on_click=lambda e, wid=w_id, c=w_custom_id: delete_click(e, wid, c), tooltip="Delete", icon_size=18, width=32, height=32)
                        ], width=100, spacing=0, alignment=ft.MainAxisAlignment.CENTER)
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=6, horizontal=15), bgcolor="white" if index % 2 == 0 else "#FAFAFA", border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER)),
                    on_hover=make_hover(index)
                )
            )
        
        workers_list.controls = new_list_controls
        page.update()

    add_btn = ft.ElevatedButton("Add Worker", icon=ft.Icons.PERSON_ADD, on_click=open_add_dialog, bgcolor=COLOR_PRIMARY, color="white", height=40)
    sync_btn = ft.ElevatedButton("Sync Device", icon=ft.Icons.SYNC, on_click=lambda e: page.run_thread(sync_hikvision_in_background), bgcolor="#F59E0B", color="white", height=40)

    main_view = ft.Column([
        ft.Row([
            ft.Text("Manage Workers", size=22, weight="bold", color=COLOR_TEXT_MAIN), 
            ft.Row([search_input, sync_btn, add_btn], spacing=10)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(height=5, color="transparent"), stats_container, ft.Divider(height=5, color="transparent"), 
        ft.Container(content=workers_list, expand=True, bgcolor="white", border_radius=8, border=ft.border.all(1, COLOR_BORDER), shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0D000000", offset=ft.Offset(0, 1)), clip_behavior=ft.ClipBehavior.HARD_EDGE)
    ], expand=True, visible=True) 

    return main_view, load_workers_ui