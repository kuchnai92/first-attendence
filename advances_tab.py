import flet as ft
from datetime import datetime, timedelta

def get_advances_view(page: ft.Page, db, state, show_snack, reload_weekly_cb, reload_monthly_cb):
    COLOR_TEXT_MAIN = "#111827"
    COLOR_TEXT_SUB = "#4B5563"
    COLOR_BORDER = "#E5E7EB"
    COLOR_BG_LIGHT = "#F3F4F6"
    COLOR_PRIMARY = "#2D5B7A"

    if "adv_view_mode" not in state:
        state["adv_view_mode"] = "Month"
        state["adv_view_date"] = datetime.now()
        state["adv_start"] = datetime.now() - timedelta(days=7)
        state["adv_end"] = datetime.now()

    selected_worker = {"id": None, "name": None}
    worker_icon = ft.Icon(ft.Icons.SEARCH, color="#6B7280")
    worker_label = ft.Text("Click to Search & Select Worker...", color="#6B7280", size=15)

    def open_worker_picker(e=None):
        c = db.conn.cursor()
        c.execute("SELECT * FROM workers")
        workers = c.fetchall()
        
        def filter_list(e):
            q = search_input.value.lower() if search_input.value else ""
            list_view.controls.clear()
            for w in workers:
                w_id = w[0]
                w_name = w[1]
                w_type = w[6]
                w_custom_id = w[8] if len(w) > 8 else w_id
                display_id = f"W-{w_custom_id}" if w_type == "Weekly" else f"M-{w_custom_id}"
                
                if q in w_name.lower() or q in w_type.lower() or q in str(w_id) or q in display_id.lower():
                    row = ft.Container(
                        content=ft.Row([
                            ft.Text(f"{display_id}  •  {w_name}", weight="bold", size=16, color="#111827"),
                            ft.Container(
                                content=ft.Text(w_type.upper(), size=10, weight="bold", color="#0284C7"), 
                                bgcolor="#E0F2FE", 
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2), 
                                border_radius=4
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=15, 
                        bgcolor="white", 
                        border=ft.border.only(bottom=ft.border.BorderSide(1, "#E5E7EB")),
                        ink=True, 
                        on_click=lambda e, wid=w_id, wname=w_name: select_worker(wid, wname)
                    )
                    list_view.controls.append(row)
            page.update()

        def select_worker(wid, wname):
            selected_worker["id"] = wid
            selected_worker["name"] = wname
            worker_label.value = wname
            worker_label.color = "#065F46"
            worker_label.weight = "bold"
            worker_selector.bgcolor = "#D1FAE5"
            worker_selector.border = ft.border.all(1, "#10B981")
            worker_icon.name = ft.Icons.CHECK_CIRCLE
            worker_icon.color = "#10B981"
            picker_dlg.open = False
            page.update()

        search_input = ft.TextField(
            label="Type Worker Name or ID...", 
            autofocus=True, 
            on_change=filter_list, 
            border_radius=8, 
            height=50
        )
        list_view = ft.ListView(spacing=0, height=300)
        filter_list(None)

        picker_dlg = ft.AlertDialog(
            title=ft.Text("🔍 Search & Select Worker", weight="bold", size=18),
            content=ft.Container(
                content=ft.Column([
                    search_input, 
                    ft.Divider(height=10, color="transparent"), 
                    list_view
                ], tight=True), 
                width=400
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(picker_dlg, 'open', False) or page.update())
            ]
        )
        page.overlay.append(picker_dlg)
        picker_dlg.open = True
        page.update()

    worker_selector = ft.Container(
        content=ft.Row([worker_icon, worker_label]), 
        on_click=open_worker_picker, 
        bgcolor="#F9FAFB", 
        border=ft.border.all(1, "#D1D5DB"), 
        border_radius=8, 
        padding=ft.Padding.symmetric(horizontal=12, vertical=12), 
        height=50, 
        ink=True
    )

    date_input = ft.TextField(label="Date", value=datetime.now().strftime("%Y-%m-%d"), prefix_icon=ft.Icons.CALENDAR_TODAY, border_radius=8, border_color="#D1D5DB", bgcolor="#F9FAFB", content_padding=12)
    amount_input = ft.TextField(label="Amount Taken (PKR)", keyboard_type=ft.KeyboardType.NUMBER, prefix_icon=ft.Icons.ATTACH_MONEY, border_radius=8, border_color="#D1D5DB", bgcolor="#F9FAFB", content_padding=12)
    reason_input = ft.TextField(label="Reason/Note", prefix_icon=ft.Icons.NOTES, border_radius=8, border_color="#D1D5DB", bgcolor="#F9FAFB", content_padding=12)

    def close_dialog(e): 
        advance_dialog.open = False
        page.update()

    def save_advance(e):
        if not selected_worker["id"] or not amount_input.value: 
            show_snack(page, "Please select a valid worker and enter amount.", "red")
            return
        try:
            amt = float(amount_input.value)
            def process_save():
                # Get the exact time to append to the date string
                current_time = datetime.now().strftime("%I:%M %p")
                full_date_with_time = f"{date_input.value} {current_time}"
                
                db.add_advance(selected_worker["id"], amt, reason_input.value, full_date_with_time)
                load_advances_ui()
                reload_weekly_cb()
                reload_monthly_cb()
                
            page.run_thread(process_save)
            show_snack(page, "Advance Saved Successfully!", "green")
            close_dialog(None)
        except ValueError: 
            show_snack(page, "Invalid Amount format.", "red")

    date_input.on_submit = save_advance
    amount_input.on_submit = save_advance
    reason_input.on_submit = save_advance

    advance_dialog = ft.AlertDialog(
        title=ft.Row([ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=COLOR_PRIMARY), ft.Text("Record Advance / Loan", color=COLOR_PRIMARY, weight="bold")]),
        content=ft.Container(
            content=ft.Column([
                worker_selector, 
                date_input, 
                amount_input, 
                reason_input
            ], tight=True, spacing=10), 
            width=380, 
            padding=ft.Padding.only(top=5, bottom=5)
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog), 
            ft.ElevatedButton("Save Advance", icon=ft.Icons.SAVE, bgcolor="#2E7D32", color="white", on_click=save_advance)
        ], 
        actions_alignment=ft.MainAxisAlignment.END, 
        shape=ft.RoundedRectangleBorder(radius=12)
    )

    def open_add_dialog(e):
        selected_worker["id"] = None
        selected_worker["name"] = None
        worker_label.value = "Click to Search & Select Worker..."
        worker_label.color = "#6B7280"
        worker_label.weight = "normal"
        worker_selector.bgcolor = "#F9FAFB"
        worker_selector.border = ft.border.all(1, "#D1D5DB")
        worker_icon.name = ft.Icons.SEARCH
        worker_icon.color = "#6B7280"
        amount_input.value = ""
        reason_input.value = ""
        date_input.value = datetime.now().strftime("%Y-%m-%d")
        
        if advance_dialog not in page.overlay: 
            page.overlay.append(advance_dialog)
        advance_dialog.open = True
        page.update()

    # --- FILTER / DATE LOGIC ---
    advances_list = ft.ListView(spacing=0, expand=True)
    month_label = ft.Text("", size=16, weight="bold")

    spec_in = ft.TextField(read_only=True, width=150, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)
    start_in = ft.TextField(read_only=True, width=130, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)
    end_in = ft.TextField(read_only=True, width=130, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)

    safe_first = datetime(2000, 1, 1)
    safe_last = datetime(2035, 12, 31)

    def handle_spec_change(e):
        if e.control.value:
            spec_in.value = e.control.value.strftime('%Y-%m-%d')
            page.update()

    def handle_start_change(e):
        if e.control.value:
            start_in.value = e.control.value.strftime('%Y-%m-%d')
            page.update()

    def handle_end_change(e):
        if e.control.value:
            end_in.value = e.control.value.strftime('%Y-%m-%d')
            page.update()

    dp_spec = ft.DatePicker(first_date=safe_first, last_date=safe_last, on_change=handle_spec_change)
    dp_start = ft.DatePicker(first_date=safe_first, last_date=safe_last, on_change=handle_start_change)
    dp_end = ft.DatePicker(first_date=safe_first, last_date=safe_last, on_change=handle_end_change)

    def get_week_bounds(ref_date):
        days_to_subtract = (ref_date.weekday() - 5) % 7
        start = ref_date - timedelta(days=days_to_subtract)
        end = start + timedelta(days=5)
        return start, end

    def open_filter_dialog(e):
        if dp_spec not in page.overlay: 
            page.overlay.extend([dp_spec, dp_start, dp_end])
            
        current_mode = [state["adv_view_mode"]]
        chips_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        dynamic_content = ft.Container()

        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        month_dd = ft.Dropdown(options=[ft.dropdown.Option(m) for m in months], value=state["adv_view_date"].strftime("%B"), width=145, border_radius=8)
        year_dd = ft.Dropdown(options=[ft.dropdown.Option(str(y)) for y in range(2020, 2035)], value=state["adv_view_date"].strftime("%Y"), width=145, border_radius=8)
        month_row = ft.Row([month_dd, year_dd], alignment=ft.MainAxisAlignment.CENTER)

        spec_in.value = state["adv_view_date"].strftime("%Y-%m-%d")
        
        def open_dp_spec_dialog(e):
            dp_spec.value = datetime.strptime(spec_in.value, "%Y-%m-%d")
            dp_spec.open = True
            page.update()
            
        spec_row = ft.Row([
            spec_in, 
            ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=COLOR_PRIMARY, on_click=open_dp_spec_dialog)
        ], alignment=ft.MainAxisAlignment.CENTER)

        weeks_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=180)
        
        def render_week_items():
            weeks_col.controls.clear()
            sel_month_idx = months.index(month_dd_w.value) + 1
            sel_year = int(year_dd_w.value)
            first_day = datetime(sel_year, sel_month_idx, 1)
            
            days_to_subtract = (first_day.weekday() - 5) % 7
            curr_start = first_day - timedelta(days=days_to_subtract)
            active_start, _ = get_week_bounds(state["adv_view_date"])
            
            week_num = 1
            while True:
                curr_end = curr_start + timedelta(days=5)
                if curr_start.month != sel_month_idx and curr_start > first_day:
                    break
                
                is_active = (curr_start.date() == active_start.date() and current_mode[0] == "Week")
                
                def make_select_handler(st_date):
                    return lambda e: assign_week_and_close(st_date)

                weeks_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.DATE_RANGE, color="white" if is_active else COLOR_PRIMARY, size=18),
                            ft.Text(f"Week {week_num}: {curr_start.strftime('%d %b')} to {curr_end.strftime('%d %b %Y')}", weight="bold", color="white" if is_active else COLOR_TEXT_MAIN, size=13)
                        ]),
                        padding=ft.Padding.symmetric(vertical=10, horizontal=12),
                        bgcolor=COLOR_PRIMARY if is_active else COLOR_BG_LIGHT,
                        border_radius=8, ink=True, on_click=make_select_handler(curr_start)
                    )
                )
                curr_start += timedelta(days=7)
                week_num += 1
            page.update()

        def assign_week_and_close(st_date):
            state["adv_view_mode"] = "Week"
            state["adv_view_date"] = st_date
            filter_dialog.open = False
            page.update()
            page.run_thread(load_advances_ui)

        def trigger_week_rebuild(e):
            render_week_items()

        month_dd_w = ft.Dropdown(options=[ft.dropdown.Option(m) for m in months], value=state["adv_view_date"].strftime("%B"), width=145, border_radius=8)
        year_dd_w = ft.Dropdown(options=[ft.dropdown.Option(str(y)) for y in range(2020, 2035)], value=state["adv_view_date"].strftime("%Y"), width=105, border_radius=8)
        
        month_dd_w.on_change = trigger_week_rebuild
        year_dd_w.on_change = trigger_week_rebuild
        
        week_picker_row = ft.Column([
            ft.Row([month_dd_w, year_dd_w], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=5, color="transparent"),
            weeks_col
        ], tight=True)

        start_in.value = state["adv_start"].strftime("%Y-%m-%d")
        end_in.value = state["adv_end"].strftime("%Y-%m-%d")
        
        def open_dp_start_dialog(e):
            dp_start.value = datetime.strptime(start_in.value, "%Y-%m-%d")
            dp_start.open = True
            page.update()
            
        def open_dp_end_dialog(e):
            dp_end.value = datetime.strptime(end_in.value, "%Y-%m-%d")
            dp_end.open = True
            page.update()
            
        range_row = ft.Column([
            ft.Row([ft.Text("Start:", width=40, weight="bold", color=COLOR_TEXT_SUB), start_in, ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=COLOR_PRIMARY, on_click=open_dp_start_dialog)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ft.Text("End:", width=40, weight="bold", color=COLOR_TEXT_SUB), end_in, ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=COLOR_PRIMARY, on_click=open_dp_end_dialog)], alignment=ft.MainAxisAlignment.CENTER)
        ], spacing=5)

        def update_dialog_ui():
            chips_row.controls.clear()
            modes = ["Specific Date", "Week", "Month", "Date Range"]
            for m in modes:
                is_active = (current_mode[0] == m)
                
                def set_mode(e, selected=m):
                    current_mode[0] = selected
                    update_dialog_ui()
                    page.update()

                chip = ft.Container(
                    content=ft.Text(m, color="white" if is_active else COLOR_TEXT_SUB, weight="bold", size=11),
                    bgcolor=COLOR_PRIMARY if is_active else COLOR_BG_LIGHT,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                    border_radius=8,
                    ink=True,
                    on_click=set_mode
                )
                chips_row.controls.append(chip)
            
            month_row.visible = (current_mode[0] == "Month")
            spec_row.visible = (current_mode[0] == "Specific Date")
            week_picker_row.visible = (current_mode[0] == "Week")
            range_row.visible = (current_mode[0] == "Date Range")
            
            dynamic_content.content = ft.Column([month_row, spec_row, week_picker_row, range_row], tight=True, alignment=ft.MainAxisAlignment.CENTER)
            if current_mode[0] == "Week":
                render_week_items()

        update_dialog_ui()

        def apply_filter(e):
            state["adv_view_mode"] = current_mode[0]
            if current_mode[0] == "Month": 
                state["adv_view_date"] = datetime(int(year_dd.value), months.index(month_dd.value) + 1, 1)
            elif current_mode[0] == "Specific Date": 
                state["adv_view_date"] = datetime.strptime(spec_in.value, "%Y-%m-%d")
            elif current_mode[0] == "Date Range":
                state["adv_start"] = datetime.strptime(start_in.value, "%Y-%m-%d")
                state["adv_end"] = datetime.strptime(end_in.value, "%Y-%m-%d")
            
            filter_dialog.open = False
            page.update()
            page.run_thread(load_advances_ui)

        filter_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.FILTER_ALT, color=COLOR_PRIMARY), 
                ft.Text("Filter Records", weight="bold", size=18)
            ]),
            content=ft.Container(
                content=ft.Column([
                    chips_row, 
                    ft.Divider(height=10, color="transparent"), 
                    dynamic_content
                ], tight=True), 
                width=450, 
                padding=10
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(filter_dialog, 'open', False) or page.update()), 
                ft.ElevatedButton("Apply Filter", bgcolor=COLOR_PRIMARY, color="white", on_click=apply_filter)
            ], 
            shape=ft.RoundedRectangleBorder(radius=12)
        )
        page.overlay.append(filter_dialog)
        filter_dialog.open = True
        page.update()

    month_clickable = ft.Container(
        content=month_label, 
        on_click=open_filter_dialog, 
        ink=True, 
        padding=ft.Padding.symmetric(horizontal=10, vertical=5), 
        border_radius=5, 
        tooltip="Click to Change View Filter"
    )

    search_input = ft.TextField(
        label="Search history by name, reason...", 
        width=250, border_radius=8, content_padding=12, border_color="#D1D5DB", bgcolor="#F9FAFB", 
        height=40, prefix_icon=ft.Icons.SEARCH, on_change=lambda e: page.run_thread(load_advances_ui)
    )
    
    add_btn = ft.ElevatedButton(
        "Add Advance", icon=ft.Icons.ADD, on_click=open_add_dialog, 
        bgcolor=COLOR_PRIMARY, color="white", height=40
    )

    def change_period(direction=0):
        mode = state["adv_view_mode"]
        if mode == "Specific Date":
            state["adv_view_date"] += timedelta(days=direction)
        elif mode == "Week":
            state["adv_view_date"] += timedelta(weeks=direction)
        elif mode == "Month":
            curr = state["adv_view_date"]
            new_m = curr.month + direction
            y_adj = 0
            if new_m > 12: 
                new_m = 1
                y_adj = 1
            elif new_m < 1: 
                new_m = 12
                y_adj = -1
            state["adv_view_date"] = curr.replace(month=new_m, year=curr.year + y_adj)
        elif mode == "Date Range":
            delta = (state["adv_end"] - state["adv_start"]).days + 1
            state["adv_start"] += timedelta(days=direction * delta)
            state["adv_end"] += timedelta(days=direction * delta)
        page.run_thread(load_advances_ui)

    def reset_to_today(e):
        state["adv_view_mode"] = "Specific Date"
        state["adv_view_date"] = datetime.now()
        page.run_thread(load_advances_ui)

    def delete_adv_background(adv_id):
        db.delete_advance(adv_id)
        load_advances_ui()
        reload_weekly_cb()
        reload_monthly_cb()
        show_snack(page, "Advance Deleted", "red")

    def load_advances_ui(e=None):
        new_list_controls = []
        mode = state["adv_view_mode"]
        
        c = db.conn.cursor()
        filter_str = ""
        
        if mode == "Month":
            filter_str = state["adv_view_date"].strftime("%Y-%m")
            month_label.value = state["adv_view_date"].strftime("%B %Y")
        elif mode == "Specific Date":
            filter_str = state["adv_view_date"].strftime("%Y-%m-%d")
            month_label.value = state["adv_view_date"].strftime("%d %b %Y")
        elif mode == "Week":
            st, en = get_week_bounds(state["adv_view_date"])
            month_label.value = f"{st.strftime('%d %b')} - {en.strftime('%d %b %Y')} (Week)"
        elif mode == "Date Range":
            month_label.value = f"{state['adv_start'].strftime('%d %b %Y')} - {state['adv_end'].strftime('%d %b %Y')}"

        sql = "SELECT a.date, w.name, w.salary_type, a.amount, a.reason, a.id FROM advances a JOIN workers w ON a.worker_id = w.id WHERE 1=1"
        params = []
        if filter_str:
            sql += " AND a.date LIKE ?"
            params.append(f"{filter_str}%")
        sql += " ORDER BY a.date DESC"
        
        c.execute(sql, tuple(params))
        all_adv = c.fetchall()

        if mode == "Week":
            adv_data = [a for a in all_adv if st.strftime("%Y-%m-%d") <= a[0] <= en.strftime("%Y-%m-%d")]
        elif mode == "Date Range":
            adv_data = [a for a in all_adv if state["adv_start"].strftime("%Y-%m-%d") <= a[0] <= state["adv_end"].strftime("%Y-%m-%d")]
        else:
            adv_data = all_adv

        query = search_input.value.lower() if search_input.value else ""
        
        new_list_controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text("Date & Time", width=140, weight="bold", color=COLOR_TEXT_SUB, size=13), 
                    ft.Text("Name", width=180, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Type", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13), 
                    ft.Text("Amount", width=120, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Container(expand=True), 
                    ft.Text("Reason", width=250, weight="bold", color=COLOR_TEXT_SUB, size=13), 
                    ft.Text("Action", width=80, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
                ]), 
                bgcolor=COLOR_BG_LIGHT, padding=ft.Padding.symmetric(vertical=10, horizontal=15), border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        )

        def make_hover(idx):
            def hover(ev):
                ev.control.bgcolor = "#F1F5F9" if ev.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                ev.control.update() 
            return hover

        visible_idx = 0
        for d, w_name, w_type, amt, rsn, a_id in adv_data:
            if query and query not in w_name.lower() and query not in (rsn or "").lower() and query not in str(amt): 
                continue
                
            del_btn = ft.IconButton(
                icon=ft.Icons.DELETE, icon_color="#EF4444", icon_size=18, width=35, height=35, tooltip="Delete", 
                on_click=lambda e, adv_id=a_id: page.run_thread(delete_adv_background, adv_id)
            )
            
            new_list_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(d, width=140, color=COLOR_TEXT_MAIN, size=13), 
                        ft.Text(w_name, width=180, weight="bold", color=COLOR_TEXT_MAIN, size=15),
                        ft.Text(w_type, width=100, color=COLOR_TEXT_SUB, size=13), 
                        ft.Text(f"{int(amt):,} PKR", width=120, weight="bold", color="#EF4444", size=14),
                        ft.Container(expand=True), 
                        ft.Text(rsn if rsn else "N/A", width=250, color=COLOR_TEXT_SUB, size=13), 
                        ft.Container(content=ft.Row([del_btn], alignment=ft.MainAxisAlignment.CENTER), width=80) 
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER), 
                    padding=ft.Padding.symmetric(vertical=8, horizontal=15), bgcolor="white" if visible_idx % 2 == 0 else "#FAFAFA", border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER)),
                    on_hover=make_hover(visible_idx)
                )
            )
            visible_idx += 1

        if visible_idx == 0: 
            new_list_controls.append(ft.Container(content=ft.Text("No advances found for this period.", italic=True, color="grey"), padding=20))
            
        advances_list.controls = new_list_controls
        page.update()

    main_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Advances / Loans", size=22, weight="bold", color=COLOR_TEXT_MAIN),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: change_period(-1)),
                    month_clickable,
                    ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=lambda e: change_period(1)),
                    ft.TextButton("Today", icon=ft.Icons.TODAY, on_click=reset_to_today, style=ft.ButtonStyle(color=COLOR_PRIMARY))
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([search_input, add_btn], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=5, color="transparent"),
            ft.Container(
                content=advances_list, expand=True, bgcolor="white", border_radius=8, border=ft.border.all(1, COLOR_BORDER), shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0D000000", offset=ft.Offset(0, 1)), clip_behavior=ft.ClipBehavior.HARD_EDGE
            )
        ], expand=True), 
        visible=False
    )

    return main_view, load_advances_ui