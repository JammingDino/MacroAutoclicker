# Smart AutoClicker

A feature-rich auto-clicker and macro recording tool built with Python and the Flet framework. This application allows you to automate mouse clicks, record and playback macros, and customize them to your needs.

## Features

*   **Auto-Clicker:**
    *   Start and stop auto-clicking with a single button or the **F6** hotkey.
    *   Set a custom delay (in seconds) between clicks for precise control.

*   **Macro Recording & Playback:**
    *   Record sequences of mouse clicks to create macros.
    *   Start/Stop recording with a button or the **F7** hotkey.
    *   Run recorded macros with a button or the **F8** hotkey.
    *   Option to loop macro playback for continuous execution.

*   **Advanced Macro Editing:**
    *   View and edit the recorded macro in a clear, list-based interface.
    *   Manually add new click or delay actions to your macro.
    *   Fine-tune click coordinates (X, Y) and delay durations.
    *   Delete individual actions or clear the entire macro.
    *   Duplicate the last action to quickly extend your macro.
    *   Apply a global delay to all delay actions in the macro at once.

*   **File Management:**
    *   Save your macros to a file in JSON format for later use.
    *   Load macros from JSON files to easily switch between different tasks.

*   **User-Friendly Interface:**
    *   Real-time status updates to keep you informed about the application's state.
    *   Live display of the current mouse cursor position.
    *   Intuitive layout built with the modern Flet framework.

## Installation and Usage

1.  **Prerequisites:**
    *   Python 3.x
    *   Install the required packages:
        ```bash
        python -m venv .venv
        .venv\Scripts\activate
        pip install flet[all] pynput pillow
        ```

2.  **Running the Application:**
    ```bash
    python autoclicker.py
    ```

3.  **Building the Application:**
    ```bash
    flet pack autoclicker.py --icon icon.png
    ```

## How to Use

1.  **Auto-Clicking:**
    *   Enter the desired delay in the "Click Delay (s)" field.
    *   Click the "Start Auto-Click (F6)" button or press the **F6** key to begin.
    *   Click the "Stop Auto-Click (F6)" button or press the **F6** key again to stop.

2.  **Recording a Macro:**
    *   Click the "Record Macro (F7)" button or press the **F7** key to start recording.
    *   Perform the desired mouse clicks on the screen.
    *   Click the "Stop Recording (F7)" button or press the **F7** key to finish.
    *   The recorded actions will appear in the "Macro Actions" list.

3.  **Playing a Macro:**
    *   After recording or loading a macro, click the "Run Macro (F8)" button or press the **F8** key.
    *   To loop the macro, toggle the "Loop Macro" switch.
    *   Click the "Stop Macro (F8)" button or press the **F8** key to stop playback.

4.  **Editing and Managing Macros:**
    *   Use the buttons under "Macro Editing" to modify your macro.
    *   Use the "File Operations" buttons to save your current macro or load one from a file.