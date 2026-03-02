import flet as ft
import threading
import time
import json
from pynput import mouse, keyboard

# Define default hold durations
DEFAULT_KEYPRESS_HOLD_DURATION = 0.05  # seconds (50 milliseconds)
DEFAULT_CLICK_HOLD_DURATION = 0.05     # seconds (50 milliseconds)

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
        self.keyboard_listener = None

        # Configurable hold durations (can be changed via Settings panel)
        self.keypress_hold_duration = DEFAULT_KEYPRESS_HOLD_DURATION
        self.click_hold_duration = DEFAULT_CLICK_HOLD_DURATION

        # Settings UI elements
        self.settings_keypress_entry = None
        self.settings_click_entry = None

        # UI elements
        self.delay_entry = None
        self.autoclick_button = None
        self.status_label = None
        self.record_button = None
        self.run_macro_button = None
        self.macro_list_column = None
        self.loop_macro_switch = None
        self.global_delay_entry = None
        self.mouse_pos_label = None

        self.file_picker = ft.FilePicker(on_result=self.on_file_picker_result)
        self.page.overlay.append(self.file_picker)
        self.page.update()

    def set_settings_elements(self, settings_keypress_entry, settings_click_entry):
        self.settings_keypress_entry = settings_keypress_entry
        self.settings_click_entry = settings_click_entry

    def apply_settings(self, e):
        try:
            kp = float(self.settings_keypress_entry.value)
            if kp >= 0:
                self.keypress_hold_duration = kp
        except ValueError:
            pass
        try:
            ch = float(self.settings_click_entry.value)
            if ch >= 0:
                self.click_hold_duration = ch
        except ValueError:
            pass
        self.update_status(f"Settings applied (key hold: {self.keypress_hold_duration:.3f}s, click hold: {self.click_hold_duration:.3f}s)")

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
            mouse_controller.press(mouse.Button.left)
            time.sleep(self.click_hold_duration)
            mouse_controller.release(mouse.Button.left)
            time.sleep(delay)

    def toggle_macro(self, e):
        if self.macro_running:
            self.stop_macro()
        else:
            self.start_macro()

    def start_macro(self):
        self.save_macro_from_entries() # Save current UI edits to macro list
        if not self.macro:
            self.update_status("Macro is empty. Record or add actions.")
            return

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

    def _parse_key_from_string(self, key_str):
        # Converts a string representation of a key back into a pynput key object
        if key_str.startswith("'") and key_str.endswith("'"):
            return key_str.strip("'")
        elif key_str.startswith("<Key.") and key_str.endswith(">"):
            key_name = key_str[5:-1] # Extract 'f6' from '<Key.f6>'
            try:
                return getattr(keyboard.Key, key_name)
            except AttributeError:
                print(f"Warning: Could not find pynput.keyboard.Key.{key_name}")
                return None
        return None

    def macro_worker(self):
        mouse_controller = mouse.Controller()
        keyboard_controller = keyboard.Controller()
        while self.macro_running:
            for action in self.macro:
                if not self.macro_running:
                    break
                if action['type'] == 'click':
                    mouse_controller.position = (action['x'], action['y'])
                    button_to_click = mouse.Button.left
                    if action['button'] == str(mouse.Button.right):
                        button_to_click = mouse.Button.right
                    mouse_controller.press(button_to_click)
                    time.sleep(action.get('click_hold_duration', self.click_hold_duration))
                    mouse_controller.release(button_to_click)
                elif action['type'] == 'key_press':
                    key_to_press = self._parse_key_from_string(action['key'])
                    if key_to_press:
                        keyboard_controller.press(key_to_press)
                        # Ensure there's a small delay to register the key press effectively
                        time.sleep(action.get('hold_duration', DEFAULT_KEYPRESS_HOLD_DURATION))
                        keyboard_controller.release(key_to_press)
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
        # Suppress hotkeys during recording to prevent them from being recorded as macro actions
        self.keyboard_listener = keyboard.Listener(on_press=self.on_record_key_press, suppress=True)
        self.keyboard_listener.start()

    def stop_recording(self):
        self.recording = False
        self.update_status("Stopped")
        self.record_button.text = "Record Macro (F7)"
        self.page.update()
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def on_record_click(self, x, y, button, pressed):
        if self.recording and pressed:
            # Add delay if previous action was also an interaction
            if self.macro and (self.macro[-1]['type'] == 'click' or self.macro[-1]['type'] == 'key_press'):
                delay = time.time() - self.macro[-1]['time']
                self.macro.append({'type': 'delay', 'duration': delay})

            self.macro.append({'type': 'click', 'x': x, 'y': y, 'button': str(button), 'time': time.time()})
            self.page.run_thread(self.update_macro_view)

    def on_record_key_press(self, key):
        if self.recording:
            # Avoid recording the hotkeys themselves (F6, F7, F8)
            if key in [keyboard.Key.f6, keyboard.Key.f7, keyboard.Key.f8]:
                return

            # Add delay if previous action was also an interaction
            if self.macro and (self.macro[-1]['type'] == 'click' or self.macro[-1]['type'] == 'key_press'):
                delay = time.time() - self.macro[-1]['time']
                self.macro.append({'type': 'delay', 'duration': delay})

            # Store key as its string representation and include default hold duration
            self.macro.append({'type': 'key_press', 'key': str(key), 'time': time.time(), 'hold_duration': self.keypress_hold_duration})
            self.page.run_thread(self.update_macro_view)


    def clear_macro(self, e):
        self.macro = []
        self.update_macro_view()

    def duplicate_last_action(self, e):
        if self.macro:
            last_action = self.macro[-1]
            duplicated_action = last_action.copy()
            if duplicated_action['type'] == 'click' or duplicated_action['type'] == 'key_press':
                duplicated_action['time'] = time.time() # Update timestamp for new action
            self.macro.append(duplicated_action)
            self.page.run_thread(self.update_macro_view) # Use page.run_thread for UI updates

    def add_click_action(self, e):
        # Default to left click at (0,0)
        self.macro.append({'type': 'click', 'x': 0, 'y': 0, 'button': str(mouse.Button.left), 'time': time.time()})
        self.update_macro_view()

    def add_key_action(self, e):
        # Default to 'a' key with current settings hold duration
        self.macro.append({'type': 'key_press', 'key': "'a'", 'time': time.time(), 'hold_duration': self.keypress_hold_duration})
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

    def save_macro_from_entries(self, e=None): # Added e=None to make it callable without an event
        new_macro = []
        for action in self.macro:
            if action['type'] == 'click':
                try:
                    # Get value from TextField if it exists, otherwise use existing value
                    x = int(action['x_field'].value) if 'x_field' in action and action['x_field'].value else action['x']
                    y = int(action['y_field'].value) if 'y_field' in action and action['y_field'].value else action['y']
                    # Preserve the original button (not directly editable in UI currently)
                    button = action['button']
                    new_macro.append({'type': 'click', 'x': x, 'y': y, 'button': button, 'time': action.get('time', time.time())})
                except (ValueError, AttributeError):
                    new_macro.append(action) # Keep original if parsing fails
            elif action['type'] == 'delay':
                try:
                    duration = float(action['duration_field'].value) if 'duration_field' in action and action['duration_field'].value else action['duration']
                    new_macro.append({'type': 'delay', 'duration': duration})
                except (ValueError, AttributeError):
                    new_macro.append(action)
            elif action['type'] == 'key_press':
                try:
                    key_val = action['key_field'].value if 'key_field' in action and action['key_field'].value else action['key']
                    hold_duration = float(action['hold_duration_field'].value) if 'hold_duration_field' in action and action['hold_duration_field'].value else action.get('hold_duration', DEFAULT_KEYPRESS_HOLD_DURATION)
                    new_macro.append({'type': 'key_press', 'key': key_val, 'time': action.get('time', time.time()), 'hold_duration': hold_duration})
                except (AttributeError, ValueError):
                    new_macro.append(action)
        self.macro = new_macro
        # self.page.update() # No need to update page here, on_change will trigger full view refresh

    def save_macro_to_file(self, e):
        self.save_macro_from_entries() # Ensure macro list is up-to-date with UI fields before saving
        self.file_picker.save_file(allowed_extensions=["json"])

    def load_macro_from_file(self, e):
        self.file_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if e.event_type == ft.FilePickerEventType.SAVE_FILE and e.path:
            # When saving, store only the essential data, not UI references like _field
            serializable_macro = []
            for action in self.macro:
                if action['type'] == 'click':
                    serializable_macro.append({'type': 'click', 'x': action['x'], 'y': action['y'], 'button': action['button']})
                elif action['type'] == 'delay':
                    serializable_macro.append({'type': 'delay', 'duration': action['duration']})
                elif action['type'] == 'key_press':
                    # Only save essential key_press data, including hold_duration
                    serializable_macro.append({'type': 'key_press', 'key': action['key'], 'hold_duration': action.get('hold_duration', DEFAULT_KEYPRESS_HOLD_DURATION)})

            with open(e.path, "w") as f:
                json.dump(serializable_macro, f, indent=4)
        elif e.event_type == ft.FilePickerEventType.PICK_FILES and e.files:
            with open(e.files[0].path, "r") as f:
                loaded_macro = json.load(f)
                self.macro = []
                for action in loaded_macro:
                    if action['type'] == 'click':
                        self.macro.append({'type': 'click', 'x': action['x'], 'y': action['y'], 'button': action.get('button', str(mouse.Button.left)), 'time': time.time()})
                    elif action['type'] == 'delay':
                        self.macro.append({'type': 'delay', 'duration': action['duration']})
                    elif action['type'] == 'key_press':
                        # Load hold_duration, defaulting if not present (for backward compatibility)
                        self.macro.append({'type': 'key_press', 'key': action['key'], 'time': time.time(), 'hold_duration': action.get('hold_duration', DEFAULT_KEYPRESS_HOLD_DURATION)})
            self.update_macro_view()

    def delete_macro_action(self, index):
        if 0 <= index < len(self.macro):
            self.macro.pop(index)
            self.update_macro_view()

    def update_macro_view(self):
        self.macro_list_column.controls.clear()
        for i, action in enumerate(self.macro):
            if action['type'] == 'click':
                # Pass self.save_macro_from_entries as on_change handler
                x_field = ft.TextField(value=str(action['x']), width=70, dense=True, content_padding=5, expand=True, on_change=self.save_macro_from_entries)
                y_field = ft.TextField(value=str(action['y']), width=70, dense=True, content_padding=5, expand=True, on_change=self.save_macro_from_entries)
                action['x_field'] = x_field
                action['y_field'] = y_field
                button_text = "Left Click" if action['button'] == str(mouse.Button.left) else "Right Click"
                row = ft.Row(
                    [
                        ft.Text(f"{i+1}. {button_text}:"), ft.Text("X:"), x_field, ft.Text("Y:"), y_field,
                        ft.IconButton(ft.Icons.DELETE, on_click=lambda _, index=i: self.delete_macro_action(index))
                    ], alignment=ft.MainAxisAlignment.START, expand=True
                )
            elif action['type'] == 'delay':
                duration_field = ft.TextField(value=f"{action.get('duration', 0.1):.2f}", width=70, dense=True, content_padding=5, expand=True, on_change=self.save_macro_from_entries)
                action['duration_field'] = duration_field
                row = ft.Row(
                    [
                        ft.Text(f"{i+1}. Delay:"), duration_field, ft.Text("s"),
                        ft.IconButton(ft.Icons.DELETE, on_click=lambda _, index=i: self.delete_macro_action(index))
                    ], alignment=ft.MainAxisAlignment.START, expand=True
                )
            elif action['type'] == 'key_press':
                key_field = ft.TextField(value=str(action['key']), width=100, dense=True, content_padding=5, expand=True, on_change=self.save_macro_from_entries)
                hold_duration_field = ft.TextField(value=f"{action.get('hold_duration', DEFAULT_KEYPRESS_HOLD_DURATION):.2f}", width=70, dense=True, content_padding=5, expand=True, on_change=self.save_macro_from_entries)
                action['key_field'] = key_field
                action['hold_duration_field'] = hold_duration_field
                row = ft.Row(
                    [
                        ft.Text(f"{i+1}. Key Press:"), key_field, ft.Text("Hold:"), hold_duration_field, ft.Text("s"),
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
    page.window.width = 600
    page.window.height = 860

    app_logic = AutoClickerLogic(page)

    # --- UI Elements ---
    button_color = ft.Colors.BLUE_700
    text_color = ft.Colors.WHITE

    delay_entry = ft.TextField(value="0.1", width=80, dense=True, content_padding=5)
    autoclick_button = ft.ElevatedButton("Start Auto-Click (F6)", on_click=app_logic.toggle_autoclick, bgcolor=button_color, color=text_color)
    status_label = ft.Text("Status: Stopped")
    mouse_pos_label = ft.Text("Mouse Position: (0, 0)")

    # Settings elements
    settings_keypress_entry = ft.TextField(
        value=f"{DEFAULT_KEYPRESS_HOLD_DURATION:.3f}", width=90, dense=True, content_padding=5,
        tooltip="How long a key is held down before being released (in seconds). Increase if the game misses key presses."
    )
    settings_click_entry = ft.TextField(
        value=f"{DEFAULT_CLICK_HOLD_DURATION:.3f}", width=90, dense=True, content_padding=5,
        tooltip="How long the mouse button is held down before being released (in seconds). Increase if the game misses clicks."
    )
    apply_settings_button = ft.ElevatedButton(
        "Apply", on_click=app_logic.apply_settings, bgcolor=button_color, color=text_color
    )

    record_button = ft.ElevatedButton("Record Macro (F7)", on_click=app_logic.toggle_recording, expand=True, bgcolor=button_color, color=text_color)
    run_macro_button = ft.ElevatedButton("Run Macro (F8)", on_click=app_logic.toggle_macro, expand=True, bgcolor=button_color, color=text_color)
    save_macro_button = ft.ElevatedButton("Save Macro", on_click=app_logic.save_macro_to_file, expand=True, bgcolor=button_color, color=text_color)
    load_macro_button = ft.ElevatedButton("Load Macro", on_click=app_logic.load_macro_from_file, expand=True, bgcolor=button_color, color=text_color)
    clear_macro_button = ft.ElevatedButton("Clear Macro", on_click=app_logic.clear_macro, expand=True, bgcolor=button_color, color=text_color)
    duplicate_last_button = ft.ElevatedButton("Duplicate Last", on_click=app_logic.duplicate_last_action, expand=True, bgcolor=button_color, color=text_color)
    add_click_button = ft.ElevatedButton("Add Click", on_click=app_logic.add_click_action, expand=True, bgcolor=button_color, color=text_color)
    add_delay_button = ft.ElevatedButton("Add Delay", on_click=app_logic.add_delay_action, expand=True, bgcolor=button_color, color=text_color)
    add_key_button = ft.ElevatedButton("Add Keypress", on_click=app_logic.add_key_action, expand=True, bgcolor=button_color, color=text_color)

    global_delay_entry = ft.TextField(value="0.1", dense=True, content_padding=5, expand=True)
    apply_global_delay_button = ft.ElevatedButton("Apply to All Delays", on_click=app_logic.apply_global_delay, bgcolor=button_color, color=text_color, expand=True)
    loop_macro_switch = ft.Switch(label="Loop Macro", value=False, on_change=app_logic.toggle_loop_macro)
    macro_list_column = ft.Column(controls=[], expand=True, scroll=ft.ScrollMode.ALWAYS)

    app_logic.set_ui_elements(delay_entry, autoclick_button, status_label, record_button, run_macro_button, macro_list_column, loop_macro_switch, global_delay_entry, mouse_pos_label)
    app_logic.set_settings_elements(settings_keypress_entry, settings_click_entry)

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
                                ft.Text("Settings", weight=ft.FontWeight.BOLD),
                                ft.Row(
                                    [
                                        ft.Text("Key Hold (s):", tooltip="How long a key is held before release. Increase if keys are missed."),
                                        settings_keypress_entry,
                                        ft.Text("Click Hold (s):", tooltip="How long mouse button is held before release. Increase if clicks are missed."),
                                        settings_click_entry,
                                        apply_settings_button,
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER, spacing=8, wrap=True
                                ),
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
                                ft.Row([add_click_button, add_delay_button, add_key_button], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
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