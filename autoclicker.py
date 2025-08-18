
import flet as ft
import threading
import time
import json
from pynput import mouse, keyboard

class AutoClickerLogic:
    def __init__(self, page: ft.Page):
        self.page = page
        self.clicking = False
        self.macro_running = False
        self.recording = False
        self.macro = []
        self.loop_macro = False
        self.click_thread = None
        self.hotkey_listener = None
        self.mouse_listener = None

        # UI elements
        self.delay_entry = None
        self.autoclick_button = None
        self.status_label = None
        self.record_button = None
        self.run_macro_button = None
        self.macro_list_column = None
        self.loop_macro_switch = None
        self.global_delay_entry = None
        self.mouse_pos_label = None  # New: Mouse position label
        self.file_picker = ft.FilePicker(on_result=self.on_file_picker_result)
        self.page.overlay.append(self.file_picker)
        self.page.update()

    def set_ui_elements(self, delay_entry, autoclick_button, status_label, record_button, run_macro_button, macro_list_column, loop_macro_switch, global_delay_entry, mouse_pos_label):
        self.delay_entry = delay_entry
        self.autoclick_button = autoclick_button
        self.status_label = status_label
        self.record_button = record_button
        self.run_macro_button = run_macro_button
        self.macro_list_column = macro_list_column
        self.loop_macro_switch = loop_macro_switch
        self.global_delay_entry = global_delay_entry
        self.mouse_pos_label = mouse_pos_label

    def update_status(self, text):
        self.status_label.value = f"Status: {text}"
        self.page.update()

    def update_mouse_position(self):
        mouse_controller = mouse.Controller()
        while True:
            try:
                x, y = mouse_controller.position
                self.mouse_pos_label.value = f"Mouse Position: ({x}, {y})"
                self.page.update()
                time.sleep(0.1)
            except Exception as e:
                print(f"Error updating mouse position: {e}")
                break

    def toggle_autoclick(self, e):
        if self.clicking:
            self.stop_autoclick()
        else:
            self.start_autoclick()

    def start_autoclick(self):
        self.clicking = True
        self.update_status("Auto-clicking")
        self.autoclick_button.text = "Stop Auto-Click (F6)"
        self.page.update()
        
        try:
            delay = float(self.delay_entry.value)
        except ValueError:
            delay = 0.1
        
        self.click_thread = threading.Thread(target=self.autoclick_worker, args=(delay,), daemon=True)
        self.click_thread.start()

    def stop_autoclick(self):
        self.clicking = False
        self.update_status("Stopped")
        self.autoclick_button.text = "Start Auto-Click (F6)"
        self.page.update()

    def autoclick_worker(self, delay):
        mouse_controller = mouse.Controller()
        while self.clicking:
            mouse_controller.click(mouse.Button.left, 1)
            time.sleep(delay)

    def toggle_macro(self, e):
        if self.macro_running:
            self.stop_macro()
        else:
            self.start_macro()

    def start_macro(self):
        self.save_macro_from_entries()
        self.macro_running = True
        self.update_status("Running Macro")
        self.run_macro_button.text = "Stop Macro (F8)"
        self.page.update()
        self.click_thread = threading.Thread(target=self.macro_worker, daemon=True)
        self.click_thread.start()

    def stop_macro(self):
        self.macro_running = False
        self.update_status("Stopped")
        self.run_macro_button.text = "Run Macro (F8)"
        self.page.update()

    def macro_worker(self):
        mouse_controller = mouse.Controller()
        while self.macro_running:
            for action in self.macro:
                if not self.macro_running:
                    break
                if action['type'] == 'click':
                    mouse_controller.position = (action['x'], action['y'])
                    mouse_controller.click(mouse.Button.left, 1)
                elif action['type'] == 'delay':
                    time.sleep(action['duration'])
            if not self.loop_macro:
                self.stop_macro()

    def toggle_recording(self, e):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.recording = True
        self.macro = []
        self.update_macro_view()
        self.update_status("Recording...")
        self.record_button.text = "Stop Recording (F7)"
        self.page.update()
        self.mouse_listener = mouse.Listener(on_click=self.on_record_click)
        self.mouse_listener.start()

    def stop_recording(self):
        self.recording = False
        self.update_status("Stopped")
        self.record_button.text = "Record Macro (F7)"
        self.page.update()
        if self.mouse_listener:
            self.mouse_listener.stop()

    def on_record_click(self, x, y, button, pressed):
        if self.recording and pressed:
            if self.macro and self.macro[-1]['type'] == 'click':
                delay = time.time() - self.macro[-1]['time']
                self.macro.append({'type': 'delay', 'duration': delay})
            
            self.macro.append({'type': 'click', 'x': x, 'y': y, 'button': str(button), 'time': time.time()})
            self.page.run_thread(self.update_macro_view)

    def clear_macro(self, e):
        self.macro = []
        self.update_macro_view()

    def duplicate_last_action(self, e):
        if self.macro:
            last_action = self.macro[-1]
            duplicated_action = last_action.copy()
            if duplicated_action['type'] == 'click':
                duplicated_action['time'] = time.time()
            self.macro.append(duplicated_action)
            self.update_macro_view()

    def add_click_action(self, e):
        self.macro.append({'type': 'click', 'x': 0, 'y': 0, 'button': 'Button.left', 'time': time.time()})
        self.update_macro_view()

    def add_delay_action(self, e):
        self.macro.append({'type': 'delay', 'duration': 0.1})
        self.update_macro_view()

    def apply_global_delay(self, e):
        try:
            global_delay = float(self.global_delay_entry.value)
            for action in self.macro:
                if action['type'] == 'delay':
                    action['duration'] = global_delay
            self.update_macro_view()
        except ValueError:
            pass

    def toggle_loop_macro(self, e):
        self.loop_macro = e.control.value

    def save_macro_from_entries(self):
        new_macro = []
        for action in self.macro:
            if action['type'] == 'click':
                try:
                    x = int(action['x_field'].value)
                    y = int(action['y_field'].value)
                    new_macro.append({'type': 'click', 'x': x, 'y': y, 'button': action['button'], 'time': action['time']})
                except (ValueError, AttributeError):
                    new_macro.append(action)
            elif action['type'] == 'delay':
                try:
                    duration = float(action['duration_field'].value)
                    new_macro.append({'type': 'delay', 'duration': duration})
                except (ValueError, AttributeError):
                    new_macro.append(action)
        self.macro = new_macro
        self.update_macro_view()

    def save_macro_to_file(self, e):
        self.save_macro_from_entries()
        self.file_picker.save_file(allowed_extensions=["json"])

    def load_macro_from_file(self, e):
        self.file_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if e.event_type == ft.FilePickerEventType.SAVE_FILE and e.path:
            with open(e.path, "w") as f:
                json.dump(self.macro, f, indent=4)
        elif e.event_type == ft.FilePickerEventType.PICK_FILES and e.files:
            with open(e.files[0].path, "r") as f:
                self.macro = json.load(f)
            self.update_macro_view()

    def delete_macro_action(self, index):
        if 0 <= index < len(self.macro):
            self.macro.pop(index)
            self.update_macro_view()

    def update_macro_view(self):
        self.macro_list_column.controls.clear()
        for i, action in enumerate(self.macro):
            if action['type'] == 'click':
                x_field = ft.TextField(value=str(action['x']), width=70, dense=True, content_padding=5, expand=True)
                y_field = ft.TextField(value=str(action['y']), width=70, dense=True, content_padding=5, expand=True)
                action['x_field'] = x_field
                action['y_field'] = y_field
                row = ft.Row(
                    [
                        ft.Text(f"{i+1}. Click:"), ft.Text("X:"), x_field, ft.Text("Y:"), y_field,
                        ft.IconButton(ft.Icons.DELETE, on_click=lambda _, index=i: self.delete_macro_action(index))
                    ], alignment=ft.MainAxisAlignment.START, expand=True
                )
            elif action['type'] == 'delay':
                duration_field = ft.TextField(value=f"{action.get('duration', 0.1):.2f}", width=70, dense=True, content_padding=5, expand=True)
                action['duration_field'] = duration_field
                row = ft.Row(
                    [
                        ft.Text(f"{i+1}. Delay:"), duration_field, ft.Text("s"),
                        ft.IconButton(ft.Icons.DELETE, on_click=lambda _, index=i: self.delete_macro_action(index))
                    ], alignment=ft.MainAxisAlignment.START, expand=True
                )
            self.macro_list_column.controls.append(row)
        self.page.update()

    def on_press(self, key):
        try:
            if key == keyboard.Key.f6: self.page.run_thread(lambda: self.toggle_autoclick(None))
            elif key == keyboard.Key.f7: self.page.run_thread(lambda: self.toggle_recording(None))
            elif key == keyboard.Key.f8: self.page.run_thread(lambda: self.toggle_macro(None))
        except AttributeError: pass

    def start_hotkey_listener(self):
        if not self.hotkey_listener or not self.hotkey_listener.is_alive():
            self.hotkey_listener = keyboard.Listener(on_press=self.on_press)
            self.hotkey_listener.start()

def main(page: ft.Page):
    page.title = "Smart AutoClicker"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window.width = 500
    page.window.height = 800

    app_logic = AutoClickerLogic(page)

    # --- UI Elements ---
    button_color = ft.Colors.BLUE_700
    text_color = ft.Colors.WHITE
    
    delay_entry = ft.TextField(value="0.1", width=80, dense=True, content_padding=5)
    autoclick_button = ft.ElevatedButton("Start Auto-Click (F6)", on_click=app_logic.toggle_autoclick, bgcolor=button_color, color=text_color)
    status_label = ft.Text("Status: Stopped")
    mouse_pos_label = ft.Text("Mouse Position: (0, 0)")
    
    record_button = ft.ElevatedButton("Record Macro (F7)", on_click=app_logic.toggle_recording, expand=True, bgcolor=button_color, color=text_color)
    run_macro_button = ft.ElevatedButton("Run Macro (F8)", on_click=app_logic.toggle_macro, expand=True, bgcolor=button_color, color=text_color)
    save_macro_button = ft.ElevatedButton("Save Macro", on_click=app_logic.save_macro_to_file, expand=True, bgcolor=button_color, color=text_color)
    load_macro_button = ft.ElevatedButton("Load Macro", on_click=app_logic.load_macro_from_file, expand=True, bgcolor=button_color, color=text_color)
    clear_macro_button = ft.ElevatedButton("Clear Macro", on_click=app_logic.clear_macro, expand=True, bgcolor=button_color, color=text_color)
    duplicate_last_button = ft.ElevatedButton("Duplicate Last", on_click=app_logic.duplicate_last_action, expand=True, bgcolor=button_color, color=text_color)
    add_click_button = ft.ElevatedButton("Add Click", on_click=app_logic.add_click_action, expand=True, bgcolor=button_color, color=text_color)
    add_delay_button = ft.ElevatedButton("Add Delay", on_click=app_logic.add_delay_action, expand=True, bgcolor=button_color, color=text_color)
    
    global_delay_entry = ft.TextField(value="0.1", dense=True, content_padding=5, expand=True)
    apply_global_delay_button = ft.ElevatedButton("Apply to All Delays", on_click=app_logic.apply_global_delay, bgcolor=button_color, color=text_color, expand=True)
    loop_macro_switch = ft.Switch(label="Loop Macro", value=False, on_change=app_logic.toggle_loop_macro)
    macro_list_column = ft.Column(controls=[], expand=True, scroll=ft.ScrollMode.ALWAYS)

    app_logic.set_ui_elements(delay_entry, autoclick_button, status_label, record_button, run_macro_button, macro_list_column, loop_macro_switch, global_delay_entry, mouse_pos_label)

    # --- Layout ---
    page.add(
        ft.Column(
            [
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Auto-Clicker Controls", weight=ft.FontWeight.BOLD),
                                ft.Row([ft.Text("Click Delay (s):"), delay_entry, autoclick_button], alignment=ft.MainAxisAlignment.CENTER),
                                status_label,
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5
                        ), padding=5
                    ), elevation=2, margin=ft.margin.only(bottom=5)
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Macro Controls", weight=ft.FontWeight.BOLD),
                                ft.Row([record_button, run_macro_button, loop_macro_switch], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5
                        ), padding=5
                    ), elevation=2, margin=ft.margin.only(bottom=5)
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("File Operations", weight=ft.FontWeight.BOLD),
                                ft.Row([save_macro_button, load_macro_button], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5
                        ), padding=5
                    ), elevation=2, margin=ft.margin.only(bottom=5)
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Macro Editing", weight=ft.FontWeight.BOLD),
                                ft.Row([clear_macro_button, duplicate_last_button], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                                ft.Row([add_click_button, add_delay_button], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                                ft.Row([ft.Text("Global Delay (s):"), global_delay_entry], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                                ft.Row([apply_global_delay_button], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5
                        ), padding=5
                    ), elevation=2, margin=ft.margin.only(bottom=5)
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text("Macro Actions:", weight=ft.FontWeight.BOLD),
                                        mouse_pos_label,
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                macro_list_column,
                            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=5
                        ), expand=True, padding=5
                    ), elevation=2, expand=True
                )
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=0
        )
    )

    mouse_thread = threading.Thread(target=app_logic.update_mouse_position, daemon=True)
    mouse_thread.start()
    app_logic.start_hotkey_listener()

if __name__ == "__main__":
    ft.app(target=main)
