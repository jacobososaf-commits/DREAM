import tkinter as tk
from tkinter import scrolledtext, simpledialog
import re
import ast
import operator
import random
import time


# ============================================================
# DREAM v0.9
# Stable / corrected build
# ============================================================


class DreamError(Exception):

    def __init__(self, code, message, line=None):
        self.code = code
        self.message = message
        self.line = line

        if line is not None:
            super().__init__(
                f"DREAM ERROR {code} | Line {line} {message}"
            )
        else:
            super().__init__(
                f"DREAM ERROR {code} | {message}"
            )


class DreamInterpreter:

    def __init__(self, root, output_callback):

        self.root = root
        self.output_callback = output_callback

        self.variables = {}

        # Screen data
        self.screens = {}
        self.current_screen = None

        # Interpreter state
        self.running = False

        # Keyboard bindings
        self.key_bindings = {}

        # Small delay for rpt[frvr]
        self.loop_delay = 0.03

    # ========================================================
    # OUTPUT
    # ========================================================

    def output(self, text):
        self.output_callback(str(text))

    def error(self, code, message, line=None):
        if line is not None:
            self.output(
                f"DREAM ERROR {code} | Line {line} {message}"
            )
        else:
            self.output(
                f"DREAM ERROR {code} | {message}"
            )

    # ========================================================
    # SAFE MATH
    # Python 3.14 compatible
    # ========================================================

    def safe_math(self, expression):

        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def evaluate(node):

            if isinstance(node, ast.Expression):
                return evaluate(node.body)

            # Python 3.14-safe number handling
            if isinstance(node, ast.Constant):

                if isinstance(node.value, bool):
                    return node.value

                if isinstance(node.value, (int, float)):
                    return node.value

                raise ValueError(
                    "Only numbers are allowed in math"
                )

            if isinstance(node, ast.BinOp):

                left = evaluate(node.left)
                right = evaluate(node.right)

                op_type = type(node.op)

                if op_type not in operators:
                    raise ValueError(
                        "Operator not allowed"
                    )

                return operators[op_type](
                    left,
                    right
                )

            if isinstance(node, ast.UnaryOp):

                operand = evaluate(node.operand)
                op_type = type(node.op)

                if op_type not in operators:
                    raise ValueError(
                        "Operator not allowed"
                    )

                return operators[op_type](
                    operand
                )

            raise ValueError(
                "Invalid expression"
            )

        tree = ast.parse(
            expression,
            mode="eval"
        )

        return evaluate(tree)

    # ========================================================
    # VARIABLE NAME
    # ========================================================

    def valid_variable_name(self, name):

        return re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            name
        ) is not None

    # ========================================================
    # REPLACE #VARIABLES IN MATH
    # ========================================================

    def replace_math_variables(self, expression):

        def replace(match):

            name = match.group(1)

            if name not in self.variables:
                raise ValueError(
                    f"Unknown variable '{name}'"
                )

            value = self.variables[name]

            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Variable '{name}' is not a number"
                )

            return str(value)

        return re.sub(
            r"#([A-Za-z_][A-Za-z0-9_]*)",
            replace,
            expression
        )

    # ========================================================
    # REPLACE BARE VARIABLES IN MATH
    #
    # Example:
    # hp - 10
    # ========================================================

    def replace_bare_math_variables(self, expression):

        def replace(match):

            name = match.group(0)

            if name in self.variables:

                value = self.variables[name]

                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Variable '{name}' is not a number"
                    )

                return str(value)

            return name

        return re.sub(
            r"\b[A-Za-z_][A-Za-z0-9_]*\b",
            replace,
            expression
        )

    # ========================================================
    # PARSE VALUE
    # ========================================================

    def parse_value(self, value):

        value = value.strip()

        # --------------------------------
        # Quoted string
        # --------------------------------

        if (
            len(value) >= 2
            and value[0] == '"'
            and value[-1] == '"'
        ):
            return value[1:-1]

        if (
            len(value) >= 2
            and value[0] == "'"
            and value[-1] == "'"
        ):
            return value[1:-1]

        # --------------------------------
        # #variable
        # --------------------------------

        if value.startswith("#"):

            name = value[1:].strip()

            if name not in self.variables:
                raise ValueError(
                    f"Unknown variable '{name}'"
                )

            return self.variables[name]

        # --------------------------------
        # Array index
        # --------------------------------

        array_match = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*\]",
            value
        )

        if array_match:

            name = array_match.group(1)
            index = int(array_match.group(2))

            if name not in self.variables:
                raise ValueError(
                    f"Unknown variable '{name}'"
                )

            array = self.variables[name]

            if not isinstance(array, list):
                raise ValueError(
                    f"Variable '{name}' is not an array"
                )

            if index < 0 or index >= len(array):
                raise ValueError(
                    f"Array index {index} out of range"
                )

            return array[index]

        # --------------------------------
        # Integer
        # --------------------------------

        if re.fullmatch(
            r"-?\d+",
            value
        ):
            return int(value)

        # --------------------------------
        # Float
        # --------------------------------

        if re.fullmatch(
            r"-?\d+\.\d+",
            value
        ):
            return float(value)

        # --------------------------------
        # Existing variable
        # --------------------------------

        if self.valid_variable_name(value):

            if value in self.variables:
                return self.variables[value]

        # --------------------------------
        # Raw text
        # --------------------------------

        return value

    # ========================================================
    # FORMAT TEXT
    #
    # {variable}
    # ========================================================

    def format_text(self, text):

        def replace_variable(match):

            name = match.group(1)

            if name in self.variables:
                return str(
                    self.variables[name]
                )

            return match.group(0)

        return re.sub(
            r"\{([A-Za-z_][A-Za-z0-9_]*)\}",
            replace_variable,
            text
        )

    # ========================================================
    # SCREEN SAFETY
    # ========================================================

    def screen_exists(self, name):

        return (
            name in self.screens
            and not self.screens[name].get("closed", True)
        )

    def screen_alive(self, screen):

        if screen is None:
            return False

        if screen.get("closed", True):
            return False

        window = screen.get("window")
        canvas = screen.get("canvas")

        try:

            if window is None or canvas is None:
                return False

            if not window.winfo_exists():
                return False

            if not canvas.winfo_exists():
                return False

            return True

        except tk.TclError:
            return False

    # ========================================================
    # CLOSE SCREEN
    # ========================================================

    def close_screen(self, name):

        if name not in self.screens:
            return

        screen = self.screens[name]

        if screen.get("closed", True):
            return

        screen["closed"] = True

        window = screen.get("window")

        try:

            if window is not None and window.winfo_exists():
                window.destroy()

        except tk.TclError:
            pass

        # If this was the active screen, remove the context
        if self.current_screen == name:
            self.current_screen = None

    # ========================================================
    # CREATE SCREEN
    # ========================================================

    def create_screen(self, name):

        # If an old screen exists but was closed,
        # remove its record so we can recreate it.
        if name in self.screens:

            old_screen = self.screens[name]

            if self.screen_alive(old_screen):
                return old_screen

            self.screens.pop(name, None)

        window = tk.Toplevel(self.root)

        window.title(
            f"DREAM - {name}"
        )

        window.geometry(
            "700x500"
        )

        window.configure(
            bg="black"
        )

        canvas = tk.Canvas(
            window,
            width=700,
            height=500,
            bg="black",
            highlightthickness=0
        )

        canvas.pack(
            fill="both",
            expand=True
        )

        screen = {
            "window": window,
            "canvas": canvas,
            "pixels": set(),
            "pixel_size": 12,
            "events": {},
            "text_y": 20,
            "closed": False
        }

        self.screens[name] = screen

        # IMPORTANT:
        # Safely handle the user closing the window.
        window.protocol(
            "WM_DELETE_WINDOW",
            lambda n=name: self.close_screen(n)
        )

        canvas.focus_set()

        return screen

    # ========================================================
    # SCREEN OUTPUT
    # ========================================================

    def screen_output(self, text):

        if self.current_screen is None:
            self.output(text)
            return

        if not self.screen_exists(self.current_screen):

            self.current_screen = None

            self.output(text)

            return

        screen = self.screens[
            self.current_screen
        ]

        if not self.screen_alive(screen):

            screen["closed"] = True
            self.current_screen = None

            self.output(text)

            return

        canvas = screen["canvas"]

        text = self.format_text(
            str(text)
        )

        try:

            canvas.create_text(
                10,
                screen["text_y"],
                anchor="nw",
                text=text,
                fill="white",
                font=("Consolas", 14),
                tags="dream_text"
            )

            screen["text_y"] += 24

            if screen["text_y"] > 470:

                canvas.delete(
                    "dream_text"
                )

                screen["text_y"] = 20

        except tk.TclError:

            screen["closed"] = True
            self.current_screen = None

    # ========================================================
    # DRAW PIXEL
    # ========================================================

    def draw_pixel(self, x, y):

        if self.current_screen is None:
            raise ValueError(
                "pxl can only be used inside a scrn."
            )

        if not self.screen_exists(self.current_screen):
            raise ValueError(
                "The DREAM screen is closed."
            )

        screen = self.screens[
            self.current_screen
        ]

        if not self.screen_alive(screen):
            screen["closed"] = True
            self.current_screen = None

            raise ValueError(
                "The DREAM screen is closed."
            )

        canvas = screen["canvas"]
        size = screen["pixel_size"]

        x = int(x)
        y = int(y)

        key = (x, y)

        if key in screen["pixels"]:
            return

        try:

            screen["pixels"].add(key)

            canvas.create_rectangle(
                x * size,
                y * size,
                (x + 1) * size,
                (y + 1) * size,
                fill="white",
                outline="white",
                tags=f"pixel_{x}_{y}"
            )

        except tk.TclError:

            screen["pixels"].discard(key)
            screen["closed"] = True
            self.current_screen = None

            raise ValueError(
                "The DREAM screen was closed."
            )

    # ========================================================
    # CLEAR PIXEL
    # ========================================================

    def clear_pixel(self, x, y):

        if self.current_screen is None:
            raise ValueError(
                "clrr can only be used inside a scrn."
            )

        if not self.screen_exists(self.current_screen):
            raise ValueError(
                "The DREAM screen is closed."
            )

        screen = self.screens[
            self.current_screen
        ]

        if not self.screen_alive(screen):
            screen["closed"] = True
            self.current_screen = None

            raise ValueError(
                "The DREAM screen is closed."
            )

        canvas = screen["canvas"]

        x = int(x)
        y = int(y)

        key = (x, y)

        screen["pixels"].discard(key)

        try:

            canvas.delete(
                f"pixel_{x}_{y}"
            )

        except tk.TclError:

            screen["closed"] = True
            self.current_screen = None

            raise ValueError(
                "The DREAM screen was closed."
            )

    # ========================================================
    # CLEAR ALL
    # ========================================================

    def clear_all(self):

        if self.current_screen is None:
            raise ValueError(
                "clra can only be used inside a scrn."
            )

        if not self.screen_exists(self.current_screen):
            raise ValueError(
                "The DREAM screen is closed."
            )

        screen = self.screens[
            self.current_screen
        ]

        if not self.screen_alive(screen):
            screen["closed"] = True
            self.current_screen = None

            raise ValueError(
                "The DREAM screen is closed."
            )

        try:

            screen["canvas"].delete("all")

            screen["pixels"].clear()

            screen["text_y"] = 20

        except tk.TclError:

            screen["closed"] = True
            self.current_screen = None

            raise ValueError(
                "The DREAM screen was closed."
            )

    # ========================================================
    # FIND BLOCK END
    # ========================================================

    def find_block_end(
        self,
        lines,
        start
    ):

        depth = 1

        block_start_pattern = re.compile(
            r"^(scrn|rpt|w|if)\b"
        )

        for i in range(
            start + 1,
            len(lines)
        ):

            command = lines[i].strip()

            if not command:
                continue

            if command.startswith("@"):
                continue

            if block_start_pattern.match(command):

                depth += 1

            elif command == "end":

                depth -= 1

                if depth == 0:
                    return i

        raise DreamError(
            "E02",
            "Missing 'end'."
        )

    # ========================================================
    # FIND ELSE
    # ========================================================

    def find_if_parts(
        self,
        lines,
        start,
        end
    ):

        depth = 0

        block_start_pattern = re.compile(
            r"^(scrn|rpt|w|if)\b"
        )

        for i in range(
            start + 1,
            end
        ):

            command = lines[i].strip()

            if block_start_pattern.match(command):

                depth += 1

            elif command == "end":

                depth -= 1

            elif (
                command == "else"
                and depth == 0
            ):

                return i

        return None

    # ========================================================
    # CONDITION VALUE
    # ========================================================

    def parse_condition_value(self, value):

        value = value.strip()

        # --------------------------------
        # #variable
        # --------------------------------

        if value.startswith("#"):

            name = value[1:].strip()

            if name not in self.variables:
                raise ValueError(
                    f"Unknown variable '{name}'"
                )

            return self.variables[name]

        # --------------------------------
        # Bare variable
        # --------------------------------

        if self.valid_variable_name(value):

            if value in self.variables:
                return self.variables[value]

        # --------------------------------
        # Quoted strings
        # --------------------------------

        if (
            len(value) >= 2
            and value[0] == '"'
            and value[-1] == '"'
        ):
            return value[1:-1]

        if (
            len(value) >= 2
            and value[0] == "'"
            and value[-1] == "'"
        ):
            return value[1:-1]

        # --------------------------------
        # Integer
        # --------------------------------

        if re.fullmatch(
            r"-?\d+",
            value
        ):
            return int(value)

        # --------------------------------
        # Float
        # --------------------------------

        if re.fullmatch(
            r"-?\d+\.\d+",
            value
        ):
            return float(value)

        # --------------------------------
        # Math expression
        # --------------------------------

        if re.search(
            r"[+\-*/%]",
            value
        ):

            expression = self.replace_math_variables(
                value
            )

            expression = self.replace_bare_math_variables(
                expression
            )

            return self.safe_math(
                expression
            )

        # --------------------------------
        # Raw text
        # --------------------------------

        return value

    # ========================================================
    # CONDITIONS
    # ========================================================

    def evaluate_condition(self, condition):

        operators = [
            "==",
            "!=",
            ">=",
            "<=",
            ">",
            "<"
        ]

        selected_operator = None

        for op in operators:

            if op in condition:

                selected_operator = op
                break

        if selected_operator is None:
            raise ValueError(
                "Invalid condition"
            )

        left_text, right_text = condition.split(
            selected_operator,
            1
        )

        left = self.parse_condition_value(
            left_text
        )

        right = self.parse_condition_value(
            right_text
        )

        try:

            if selected_operator == "==":
                return left == right

            if selected_operator == "!=":
                return left != right

            if selected_operator == ">":
                return left > right

            if selected_operator == "<":
                return left < right

            if selected_operator == ">=":
                return left >= right

            if selected_operator == "<=":
                return left <= right

        except TypeError:

            raise ValueError(
                f"Cannot compare {type(left).__name__} "
                f"with {type(right).__name__}"
            )

        return False

    # ========================================================
    # KEYBOARD
    # ========================================================

    def bind_key_event(
        self,
        screen_name,
        key,
        event_type,
        block_lines
    ):

        if not self.screen_exists(screen_name):
            return

        screen = self.screens[
            screen_name
        ]

        if not self.screen_alive(screen):
            return

        canvas = screen["canvas"]

        key_aliases = {
            "u-a": "Up",
            "d-a": "Down",
            "l-a": "Left",
            "r-a": "Right",
            "space": "space",
            "enter": "Return",
            "esc": "Escape",
            "tab": "Tab"
        }

        actual_key = key_aliases.get(
            key.lower(),
            key
        )

        if event_type == "clk":

            sequence = (
                f"<KeyPress-{actual_key}>"
            )

        elif event_type == "rel":

            sequence = (
                f"<KeyRelease-{actual_key}>"
            )

        else:

            raise ValueError(
                f"Unknown keyboard event "
                f"'{event_type}'"
            )

        def handler(
            event,
            lines=block_lines,
            screen_name=screen_name
        ):

            # Screen may have been closed
            if not self.screen_exists(screen_name):
                return

            screen = self.screens.get(
                screen_name
            )

            if not self.screen_alive(screen):
                return

            if not self.running:
                return

            old_screen = self.current_screen

            self.current_screen = screen_name

            try:

                self.execute_block(
                    lines
                )

            except DreamError as e:

                self.error(
                    e.code,
                    e.message,
                    e.line
                )

            except tk.TclError:

                # Window disappeared while event
                # was being processed.
                if screen_name in self.screens:
                    self.screens[screen_name]["closed"] = True

            except Exception as e:

                self.error(
                    "E99",
                    str(e)
                )

            finally:

                # Don't restore a screen that was closed.
                if self.screen_exists(screen_name):
                    self.current_screen = old_screen
                else:
                    self.current_screen = None

        try:

            binding_id = canvas.bind(
                sequence,
                handler
            )

            self.key_bindings[
                (screen_name, sequence)
            ] = binding_id

            canvas.focus_set()

        except tk.TclError:

            screen["closed"] = True

    # ========================================================
    # USER INPUT
    # ========================================================

    def request_input(self):

        if self.current_screen is None:

            value = simpledialog.askstring(
                "DREAM Input",
                "Input:"
            )

            return value or ""

        if not self.screen_exists(
            self.current_screen
        ):

            self.current_screen = None

            return ""

        screen = self.screens[
            self.current_screen
        ]

        if not self.screen_alive(screen):

            screen["closed"] = True
            self.current_screen = None

            return ""

        canvas = screen["canvas"]

        entry = tk.Entry(
            canvas,
            bg="black",
            fg="white",
            insertbackground="white",
            font=("Consolas", 14)
        )

        try:

            window_id = canvas.create_window(
                10,
                screen["text_y"],
                anchor="nw",
                window=entry,
                width=400
            )

        except tk.TclError:

            screen["closed"] = True
            self.current_screen = None

            return ""

        screen["text_y"] += 30

        entry.focus_set()

        result = {
            "value": None,
            "done": False
        }

        def submit(event=None):

            if result["done"]:
                return

            try:
                result["value"] = entry.get()
            except tk.TclError:
                result["value"] = ""

            result["done"] = True

            try:
                canvas.delete(window_id)
            except tk.TclError:
                pass

            try:
                entry.destroy()
            except tk.TclError:
                pass

        entry.bind(
            "<Return>",
            submit
        )

        while (
            not result["done"]
            and self.running
        ):

            try:

                if not self.screen_alive(screen):
                    break

                self.root.update()

            except tk.TclError:

                break

            time.sleep(0.01)

        if not result["done"]:

            try:
                entry.destroy()
            except tk.TclError:
                pass

        return result["value"] or ""

    # ========================================================
    # EXECUTE BLOCK
    # ========================================================

    def execute_block(
        self,
        lines,
        start=0,
        end=None
    ):

        if end is None:
            end = len(lines)

        i = start

        while i < end:

            if not self.running:
                return

            raw = lines[i]

            line = raw.strip()

            line_number = i + 1

            # --------------------------------------------
            # Empty
            # --------------------------------------------

            if not line:

                i += 1
                continue

            # --------------------------------------------
            # Comment
            # --------------------------------------------

            if line.startswith("@"):

                i += 1
                continue

            # --------------------------------------------
            # End
            # --------------------------------------------

            if line == "end":
                return

            # --------------------------------------------
            # Else
            # --------------------------------------------

            if line == "else":
                return

            # =================================================
            # SCREEN
            # =================================================

            screen_match = re.fullmatch(
                r"scrn\s+([A-Za-z_][A-Za-z0-9_]*)",
                line
            )

            if screen_match:

                screen_name = (
                    screen_match.group(1)
                )

                block_end = self.find_block_end(
                    lines,
                    i
                )

                screen = self.create_screen(
                    screen_name
                )

                old_screen = self.current_screen

                self.current_screen = screen_name

                try:

                    self.execute_block(
                        lines,
                        i + 1,
                        block_end
                    )

                except tk.TclError:

                    screen["closed"] = True
                    self.current_screen = None

                finally:

                    if self.screen_exists(
                        screen_name
                    ):

                        self.current_screen = old_screen

                    else:

                        self.current_screen = None

                i = block_end + 1
                continue

            # =================================================
            # ARRAY DECLARATION
            # =================================================

            array_match = re.fullmatch(
                r"a\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\[.*\])",
                line
            )

            if array_match:

                name = array_match.group(1)

                raw_array = array_match.group(2)

                try:

                    parsed = ast.literal_eval(
                        raw_array
                    )

                    if not isinstance(parsed, list):
                        raise ValueError(
                            "Array must be a list"
                        )

                    self.variables[name] = parsed

                except Exception:

                    content = raw_array[1:-1].strip()

                    if not content:

                        self.variables[name] = []

                    else:

                        items = [
                            item.strip()
                            for item in content.split(",")
                        ]

                        cleaned_items = []

                        for item in items:

                            if (
                                len(item) >= 2
                                and (
                                    (
                                        item[0] == '"'
                                        and item[-1] == '"'
                                    )
                                    or
                                    (
                                        item[0] == "'"
                                        and item[-1] == "'"
                                    )
                                )
                            ):

                                cleaned_items.append(
                                    item[1:-1]
                                )

                            elif re.fullmatch(
                                r"-?\d+",
                                item
                            ):

                                cleaned_items.append(
                                    int(item)
                                )

                            elif re.fullmatch(
                                r"-?\d+\.\d+",
                                item
                            ):

                                cleaned_items.append(
                                    float(item)
                                )

                            else:

                                cleaned_items.append(
                                    item
                                )

                        self.variables[name] = (
                            cleaned_items
                        )

                i += 1
                continue

            # =================================================
            # VARIABLE DECLARATION
            # =================================================

            variable_match = re.fullmatch(
                r"s\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)",
                line
            )

            if variable_match:

                name = variable_match.group(1)

                value_text = (
                    variable_match.group(2).strip()
                )

                try:

                    if (
                        re.search(
                            r"[+\-*/%]",
                            value_text
                        )
                        and not (
                            value_text.startswith('"')
                            or value_text.startswith("'")
                        )
                    ):

                        expression = (
                            self.replace_math_variables(
                                value_text
                            )
                        )

                        expression = (
                            self.replace_bare_math_variables(
                                expression
                            )
                        )

                        value = self.safe_math(
                            expression
                        )

                    else:

                        value = self.parse_value(
                            value_text
                        )

                    self.variables[name] = value

                except Exception as e:

                    raise DreamError(
                        "E03",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # ARRAY ASSIGNMENT
            # =================================================

            array_assignment = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*\]\s*=\s*(.+)",
                line
            )

            if array_assignment:

                name = array_assignment.group(1)

                index = int(
                    array_assignment.group(2)
                )

                value_text = (
                    array_assignment.group(3).strip()
                )

                if name not in self.variables:

                    raise DreamError(
                        "E04",
                        f"Unknown variable '{name}'.",
                        line_number
                    )

                if not isinstance(
                    self.variables[name],
                    list
                ):

                    raise DreamError(
                        "E04",
                        f"Variable '{name}' is not an array.",
                        line_number
                    )

                if index < 0 or index >= len(
                    self.variables[name]
                ):

                    raise DreamError(
                        "E04",
                        f"Array index {index} out of range.",
                        line_number
                    )

                try:

                    value = self.parse_value(
                        value_text
                    )

                    self.variables[name][index] = value

                except Exception as e:

                    raise DreamError(
                        "E03",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # VARIABLE REASSIGNMENT
            # =================================================

            assignment = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)",
                line
            )

            if assignment:

                name = assignment.group(1)

                value_text = (
                    assignment.group(2).strip()
                )

                if name not in self.variables:

                    raise DreamError(
                        "E04",
                        f"Unknown variable '{name}'.",
                        line_number
                    )

                try:

                    # ----------------------------------------
                    # Arithmetic
                    # ----------------------------------------

                    if (
                        re.search(
                            r"[+\-*/%]",
                            value_text
                        )
                        and not (
                            value_text.startswith('"')
                            or value_text.startswith("'")
                        )
                    ):

                        expression = (
                            self.replace_math_variables(
                                value_text
                            )
                        )

                        expression = (
                            self.replace_bare_math_variables(
                                expression
                            )
                        )

                        value = self.safe_math(
                            expression
                        )

                    else:

                        value = self.parse_value(
                            value_text
                        )

                    self.variables[name] = value

                except Exception as e:

                    raise DreamError(
                        "E03",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # RANDOM
            # =================================================

            random_match = re.fullmatch(
                r"rdm\s*\[\s*(.+?)\s*,\s*(.+?)\s*\]",
                line
            )

            if random_match:

                low_text = random_match.group(1)

                high_text = random_match.group(2)

                try:

                    low = self.parse_condition_value(
                        low_text
                    )

                    high = self.parse_condition_value(
                        high_text
                    )

                    if not isinstance(
                        low,
                        (int, float)
                    ) or not isinstance(
                        high,
                        (int, float)
                    ):

                        raise ValueError(
                            "Random limits must be numbers"
                        )

                    self.variables["random"] = (
                        random.randint(
                            int(low),
                            int(high)
                        )
                    )

                except Exception as e:

                    raise DreamError(
                        "E03",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # IF
            # =================================================

            if_match = re.fullmatch(
                r"if\s+(.+)",
                line
            )

            if if_match:

                condition = (
                    if_match.group(1)
                )

                block_end = self.find_block_end(
                    lines,
                    i
                )

                else_index = self.find_if_parts(
                    lines,
                    i,
                    block_end
                )

                try:

                    result = (
                        self.evaluate_condition(
                            condition
                        )
                    )

                except Exception as e:

                    raise DreamError(
                        "E06",
                        str(e),
                        line_number
                    )

                if result:

                    self.execute_block(
                        lines,
                        i + 1,
                        (
                            else_index
                            if else_index is not None
                            else block_end
                        )
                    )

                elif else_index is not None:

                    self.execute_block(
                        lines,
                        else_index + 1,
                        block_end
                    )

                i = block_end + 1
                continue

            # =================================================
            # REPEAT
            # =================================================

            repeat_match = re.fullmatch(
                r"rpt\s*\[\s*(.+?)\s*\]",
                line
            )

            if repeat_match:

                amount = (
                    repeat_match.group(1).strip()
                )

                block_end = self.find_block_end(
                    lines,
                    i
                )

                block_lines = lines[
                    i + 1:block_end
                ]

                # --------------------------------------------
                # FOREVER
                # --------------------------------------------

                if amount.lower() == "frvr":

                    while self.running:

                        # If the current screen disappeared,
                        # stop the running game safely.
                        if self.current_screen is not None:

                            if not self.screen_exists(
                                self.current_screen
                            ):

                                self.current_screen = None
                                self.running = False
                                break

                        old_screen = (
                            self.current_screen
                        )

                        try:

                            self.execute_block(
                                block_lines
                            )

                        except DreamError as e:

                            self.error(
                                e.code,
                                e.message,
                                e.line
                            )

                            break

                        except tk.TclError:

                            if (
                                old_screen
                                and old_screen in self.screens
                            ):

                                self.screens[
                                    old_screen
                                ]["closed"] = True

                            self.current_screen = None

                            break

                        except Exception as e:

                            self.error(
                                "E99",
                                str(e)
                            )

                            break

                        finally:

                            if (
                                old_screen
                                and self.screen_exists(
                                    old_screen
                                )
                            ):

                                self.current_screen = old_screen

                            else:

                                self.current_screen = None

                        # Process Tkinter events.
                        try:

                            self.root.update()

                        except tk.TclError:

                            self.running = False
                            break

                        # Small delay prevents 100% CPU loops.
                        time.sleep(
                            self.loop_delay
                        )

                    i = block_end + 1
                    continue

                # --------------------------------------------
                # Normal repeat
                # --------------------------------------------

                try:

                    count = int(
                        self.parse_condition_value(
                            amount
                        )
                    )

                except Exception as e:

                    raise DreamError(
                        "E03",
                        str(e),
                        line_number
                    )

                for _ in range(count):

                    if not self.running:
                        break

                    old_screen = (
                        self.current_screen
                    )

                    try:

                        self.execute_block(
                            block_lines
                        )

                    finally:

                        if (
                            old_screen
                            and self.screen_exists(
                                old_screen
                            )
                        ):

                            self.current_screen = old_screen

                        else:

                            self.current_screen = None

                i = block_end + 1
                continue

            # =================================================
            # KEYBOARD
            # =================================================

            keyboard_match = re.fullmatch(
                r"w\s+([^\s]+)\s+([^\s]+)",
                line
            )

            if keyboard_match:

                key = (
                    keyboard_match.group(1)
                )

                event_type = (
                    keyboard_match.group(2)
                )

                if self.current_screen is None:

                    raise DreamError(
                        "E41",
                        "w can only be used inside a scrn.",
                        line_number
                    )

                if not self.screen_exists(
                    self.current_screen
                ):

                    raise DreamError(
                        "E41",
                        "The DREAM screen is closed.",
                        line_number
                    )

                block_end = self.find_block_end(
                    lines,
                    i
                )

                block_lines = lines[
                    i + 1:block_end
                ]

                self.bind_key_event(
                    self.current_screen,
                    key,
                    event_type,
                    block_lines
                )

                i = block_end + 1
                continue

            # =================================================
            # CLEAR ALL
            # =================================================

            if line == "clra":

                try:

                    self.clear_all()

                except Exception as e:

                    raise DreamError(
                        "E41",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # CLEAR PIXEL
            # =================================================

            clear_match = re.fullmatch(
                r"clrr\s*\[\s*(.+?)\s*,\s*(.+?)\s*\]",
                line
            )

            if clear_match:

                x_text = (
                    clear_match.group(1)
                )

                y_text = (
                    clear_match.group(2)
                )

                try:

                    x = self.parse_condition_value(
                        x_text
                    )

                    y = self.parse_condition_value(
                        y_text
                    )

                    self.clear_pixel(
                        int(x),
                        int(y)
                    )

                except Exception as e:

                    raise DreamError(
                        "E41",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # PIXEL
            # =================================================

            pixel_match = re.fullmatch(
                r"pxl\s*\[\s*(.+?)\s*,\s*(.+?)\s*\]",
                line
            )

            if pixel_match:

                x_text = (
                    pixel_match.group(1)
                )

                y_text = (
                    pixel_match.group(2)
                )

                try:

                    x = self.parse_condition_value(
                        x_text
                    )

                    y = self.parse_condition_value(
                        y_text
                    )

                    self.draw_pixel(
                        int(x),
                        int(y)
                    )

                except Exception as e:

                    raise DreamError(
                        "E41",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # MATH
            # =================================================

            math_match = re.fullmatch(
                r"m\s*\[\s*(.+?)\s*\]",
                line
            )

            if math_match:

                expression = (
                    math_match.group(1)
                )

                try:

                    expression = (
                        self.replace_math_variables(
                            expression
                        )
                    )

                    expression = (
                        self.replace_bare_math_variables(
                            expression
                        )
                    )

                    result = self.safe_math(
                        expression
                    )

                    self.output(
                        result
                    )

                except Exception as e:

                    raise DreamError(
                        "E03",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # USER INPUT
            # =================================================

            if line == "r #usrinp":

                try:

                    value = self.request_input()

                    if self.current_screen is not None:

                        self.screen_output(
                            value
                        )

                    else:

                        self.output(
                            value
                        )

                except Exception as e:

                    raise DreamError(
                        "E99",
                        str(e),
                        line_number
                    )

                i += 1
                continue

            # =================================================
            # ARRAY OUTPUT
            # =================================================

            array_output = re.fullmatch(
                r"r\s+#([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]",
                line
            )

            if array_output:

                name = (
                    array_output.group(1)
                )

                index = int(
                    array_output.group(2)
                )

                if name not in self.variables:

                    raise DreamError(
                        "E04",
                        f"Unknown variable '{name}'.",
                        line_number
                    )

                value = self.variables[name]

                if not isinstance(value, list):

                    raise DreamError(
                        "E04",
                        f"Variable '{name}' is not an array.",
                        line_number
                    )

                if index < 0 or index >= len(value):

                    raise DreamError(
                        "E04",
                        f"Array index {index} out of range.",
                        line_number
                    )

                if self.current_screen is not None:

                    self.screen_output(
                        value[index]
                    )

                else:

                    self.output(
                        value[index]
                    )

                i += 1
                continue

            # =================================================
            # VARIABLE OUTPUT
            # =================================================

            variable_output = re.fullmatch(
                r"r\s+#([A-Za-z_][A-Za-z0-9_]*)",
                line
            )

            if variable_output:

                name = (
                    variable_output.group(1)
                )

                if name not in self.variables:

                    raise DreamError(
                        "E04",
                        f"Unknown variable '{name}'.",
                        line_number
                    )

                value = (
                    self.variables[name]
                )

                if self.current_screen is not None:

                    self.screen_output(
                        value
                    )

                else:

                    self.output(
                        value
                    )

                i += 1
                continue

            # =================================================
            # NORMAL OUTPUT
            # =================================================

            output_match = re.fullmatch(
                r"r\s*\[(.*)\]",
                line
            )

            if output_match:

                text = (
                    output_match.group(1)
                )

                text = self.format_text(
                    text
                )

                if self.current_screen is not None:

                    self.screen_output(
                        text
                    )

                else:

                    self.output(
                        text
                    )

                i += 1
                continue

            # =================================================
            # UNKNOWN COMMAND
            # =================================================

            raise DreamError(
                "E01",
                f"Unknown command '{line}'.",
                line_number
            )

    # ========================================================
    # CLOSE ALL SCREENS
    # ========================================================

    def close_all_screens(self):

        names = list(
            self.screens.keys()
        )

        for name in names:

            self.close_screen(name)

        self.screens.clear()
        self.current_screen = None

    # ========================================================
    # RUN
    # ========================================================

    def run(self, code):

        # Stop previous execution.
        self.running = False

        # Clean up old DREAM windows.
        self.close_all_screens()

        self.variables = {}
        self.key_bindings = {}

        self.running = True

        lines = code.splitlines()

        try:

            self.execute_block(
                lines
            )

        except DreamError as e:

            self.error(
                e.code,
                e.message,
                e.line
            )

        except tk.TclError as e:

            self.error(
                "E99",
                str(e)
            )

        except Exception as e:

            self.error(
                "E99",
                str(e)
            )

        finally:

            self.running = False

    # ========================================================
    # STOP FROM IDE
    # ========================================================

    def stop(self):

        self.running = False

        self.current_screen = None


# ============================================================
# DREAM IDE
# ============================================================


class DreamIDE:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "DREAM v0.9 IDE"
        )

        self.root.geometry(
            "1000x700"
        )

        self.root.configure(
            bg="#202020"
        )

        # ====================================================
        # TOP BAR
        # ====================================================

        top = tk.Frame(
            root,
            bg="#181818",
            height=50
        )

        top.pack(
            fill="x"
        )

        title = tk.Label(
            top,
            text="DREAM v0.9",
            bg="#181818",
            fg="white",
            font=("Consolas", 18, "bold")
        )

        title.pack(
            side="left",
            padx=15,
            pady=10
        )

        run_button = tk.Button(
            top,
            text="RUN",
            command=self.run_code,
            bg="#333333",
            fg="white",
            activebackground="#444444",
            activeforeground="white"
        )

        run_button.pack(
            side="right",
            padx=5
        )

        stop_button = tk.Button(
            top,
            text="STOP",
            command=self.stop_code,
            bg="#333333",
            fg="white",
            activebackground="#444444",
            activeforeground="white"
        )

        stop_button.pack(
            side="right",
            padx=5
        )

        clear_button = tk.Button(
            top,
            text="CLEAR",
            command=self.clear_output,
            bg="#333333",
            fg="white",
            activebackground="#444444",
            activeforeground="white"
        )

        clear_button.pack(
            side="right",
            padx=5
        )

        # ====================================================
        # CODE EDITOR
        # ====================================================

        editor_label = tk.Label(
            root,
            text="DREAM CODE",
            bg="#202020",
            fg="white",
            font=("Consolas", 11, "bold")
        )

        editor_label.pack(
            anchor="w",
            padx=10,
            pady=(10, 0)
        )

        self.editor = scrolledtext.ScrolledText(
            root,
            bg="#111111",
            fg="#eeeeee",
            insertbackground="white",
            font=("Consolas", 12),
            undo=True
        )

        self.editor.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        # ====================================================
        # OUTPUT
        # ====================================================

        output_label = tk.Label(
            root,
            text="OUTPUT",
            bg="#202020",
            fg="white",
            font=("Consolas", 11, "bold")
        )

        output_label.pack(
            anchor="w",
            padx=10,
            pady=(5, 0)
        )

        self.output_box = scrolledtext.ScrolledText(
            root,
            height=10,
            bg="#080808",
            fg="#00ff88",
            insertbackground="white",
            font=("Consolas", 11)
        )

        self.output_box.pack(
            fill="both",
            expand=False,
            padx=10,
            pady=(5, 10)
        )

        self.load_default_code()

    # ========================================================
    # OUTPUT
    # ========================================================

    def output(self, text):

        try:

            self.output_box.insert(
                "end",
                str(text) + "\n"
            )

            self.output_box.see(
                "end"
            )

        except tk.TclError:

            pass

    # ========================================================
    # CLEAR OUTPUT
    # ========================================================

    def clear_output(self):

        self.output_box.delete(
            "1.0",
            "end"
        )

    # ========================================================
    # RUN
    # ========================================================

    def run_code(self):

        self.clear_output()

        code = self.editor.get(
            "1.0",
            "end"
        )

        # Stop and clean up an old interpreter.
        if hasattr(
            self,
            "interpreter"
        ):

            try:
                self.interpreter.stop()
                self.interpreter.close_all_screens()
            except Exception:
                pass

        self.interpreter = DreamInterpreter(
            self.root,
            self.output
        )

        self.interpreter.run(
            code
        )

    # ========================================================
    # STOP
    # ========================================================

    def stop_code(self):

        if hasattr(
            self,
            "interpreter"
        ):

            self.interpreter.stop()

    # ========================================================
    # DEFAULT DREAM v0.9 TEST
    # ========================================================

    def load_default_code(self):

        code = """@ DREAM v0.9 OFFICIAL TEST

s hp = 100
s score = 0

r [DREAM v0.9]
r [HP: {hp}]
r [Score: {score}]

hp = hp - 25
score = score + 10

r [After changes:]
r [HP: {hp}]
r [Score: {score}]

m [10+5]

rdm [1,100]
r #random

if hp > 0
    r [PLAYER ALIVE]
else
    r [GAME OVER]
end

if score >= 10
    r [SCORE CONDITION WORKS]
end

a inventory = [apple,banana,orange]

r #inventory
r #inventory[0]

inventory[0] = sword

r #inventory
r #inventory[0]

scrn game

    r [DREAM SCREEN]
    r [PRESS ARROW KEYS]

    pxl[5,5]
    pxl[6,5]
    pxl[7,5]

    w u-a clk
        r [UP WORKS]
    end

    w d-a clk
        r [DOWN WORKS]
    end

    w l-a clk
        r [LEFT WORKS]
    end

    w r-a clk
        r [RIGHT WORKS]
    end

    w space clk
        r [SPACE WORKS]
    end

end
"""

        self.editor.insert(
            "1.0",
            code
        )


# ============================================================
# START DREAM
# ============================================================


if __name__ == "__main__":

    root = tk.Tk()

    app = DreamIDE(
        root
    )

    root.mainloop()