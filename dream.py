import tkinter as tk
from tkinter import scrolledtext, simpledialog
import re
import ast
import operator
import random
import time


# ============================================================
# DREAM v0.9.1
# STABILITY / BUG-FIX BUILD
#
# FIX:
# Nested blocks now preserve their active screen context.
#
# This allows:
#
# scrn game
#     rpt[frvr]
#         if x == 5
#             pxl[x,y]
#             clrr[x,y]
#         end
#     end
# end
#
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

        # ----------------------------------------------------
        # Screen data
        # ----------------------------------------------------

        self.screens = {}
        self.current_screen = None

        # ----------------------------------------------------
        # Runtime state
        # ----------------------------------------------------

        self.running = False

        self.run_id = 0

        self.key_bindings = {}

        self.loop_delay = 0.03

    # ========================================================
    # OUTPUT
    # ========================================================

    def output(self, text):

        try:
            self.output_callback(str(text))
        except Exception:
            pass

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

            if isinstance(node, ast.Constant):

                if isinstance(node.value, bool):
                    return node.value

                if isinstance(node.value, (int, float)):
                    return node.value

                raise ValueError(
                    "Only numbers are allowed in math."
                )

            if isinstance(node, ast.BinOp):

                left = evaluate(node.left)
                right = evaluate(node.right)

                op_type = type(node.op)

                if op_type not in operators:
                    raise ValueError(
                        "Operator not allowed."
                    )

                try:
                    return operators[op_type](
                        left,
                        right
                    )

                except ZeroDivisionError:
                    raise ValueError(
                        "Division by zero."
                    )

                except OverflowError:
                    raise ValueError(
                        "Math result is too large."
                    )

            if isinstance(node, ast.UnaryOp):

                operand = evaluate(node.operand)
                op_type = type(node.op)

                if op_type not in operators:
                    raise ValueError(
                        "Operator not allowed."
                    )

                try:
                    return operators[op_type](
                        operand
                    )

                except Exception:
                    raise ValueError(
                        "Invalid mathematical operation."
                    )

            raise ValueError(
                "Invalid mathematical expression."
            )

        try:

            tree = ast.parse(
                expression,
                mode="eval"
            )

        except SyntaxError:
            raise ValueError(
                "Invalid mathematical expression."
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
                    f"Unknown variable '{name}'."
                )

            value = self.variables[name]

            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Variable '{name}' is not a number."
                )

            return str(value)

        return re.sub(
            r"#([A-Za-z_][A-Za-z0-9_]*)",
            replace,
            expression
        )

    # ========================================================
    # REPLACE BARE VARIABLES IN MATH
    # ========================================================

    def replace_bare_math_variables(self, expression):

        def replace(match):

            name = match.group(0)

            if name in self.variables:

                value = self.variables[name]

                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Variable '{name}' is not a number."
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

        if value.startswith("#"):

            name = value[1:].strip()

            if not self.valid_variable_name(name):
                raise ValueError(
                    f"Invalid variable name '{name}'."
                )

            if name not in self.variables:
                raise ValueError(
                    f"Unknown variable '{name}'."
                )

            return self.variables[name]

        array_match = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*\]",
            value
        )

        if array_match:

            name = array_match.group(1)
            index = int(array_match.group(2))

            if name not in self.variables:
                raise ValueError(
                    f"Unknown variable '{name}'."
                )

            array = self.variables[name]

            if not isinstance(array, list):
                raise ValueError(
                    f"Variable '{name}' is not an array."
                )

            if index >= len(array):
                raise ValueError(
                    f"Array index {index} out of range."
                )

            return array[index]

        if re.fullmatch(
            r"-?\d+",
            value
        ):
            return int(value)

        if re.fullmatch(
            r"-?\d+\.\d+",
            value
        ):
            return float(value)

        if self.valid_variable_name(value):

            if value in self.variables:
                return self.variables[value]

        return value

    # ========================================================
    # FORMAT TEXT
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

        if name not in self.screens:
            return False

        return not self.screens[name].get(
            "closed",
            True
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
    # REMOVE SCREEN BINDINGS
    # ========================================================

    def remove_screen_bindings(self, name):

        screen = self.screens.get(name)

        if screen is None:
            return

        canvas = screen.get("canvas")

        if canvas is None:
            return

        bindings_to_remove = [
            key
            for key in self.key_bindings
            if key[0] == name
        ]

        for binding_key in bindings_to_remove:

            sequence = binding_key[1]

            binding_id = self.key_bindings.pop(
                binding_key,
                None
            )

            try:

                if binding_id:
                    canvas.unbind(
                        sequence,
                        binding_id
                    )

            except tk.TclError:
                pass

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

        self.remove_screen_bindings(name)

        window = screen.get("window")

        try:

            if window is not None and window.winfo_exists():
                window.destroy()

        except tk.TclError:
            pass

        if self.current_screen == name:
            self.current_screen = None

    # ========================================================
    # CREATE SCREEN
    # ========================================================

    def create_screen(self, name):

        if name in self.screens:

            old_screen = self.screens[name]

            if self.screen_alive(old_screen):
                return old_screen

            self.close_screen(name)

            self.screens.pop(
                name,
                None
            )

        try:

            window = tk.Toplevel(
                self.root
            )

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

        except tk.TclError:

            raise ValueError(
                "Could not create DREAM screen."
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

        window.protocol(
            "WM_DELETE_WINDOW",
            lambda n=name: self.close_screen(n)
        )

        try:
            canvas.focus_set()
        except tk.TclError:
            pass

        return screen

    # ========================================================
    # SCREEN OUTPUT
    # ========================================================

    def screen_output(self, text):

        if self.current_screen is None:
            self.output(text)
            return

        if not self.screen_exists(
            self.current_screen
        ):

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

            self.remove_screen_bindings(
                self.current_screen
            )

            self.current_screen = None

    # ========================================================
    # DRAW PIXEL
    # ========================================================

    def draw_pixel(self, x, y):

        if self.current_screen is None:
            raise ValueError(
                "pxl can only be used inside a scrn."
            )

        if not self.screen_exists(
            self.current_screen
        ):
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

            x = int(x)
            y = int(y)

        except (TypeError, ValueError):

            raise ValueError(
                "Pixel coordinates must be numbers."
            )

        canvas = screen["canvas"]
        size = screen["pixel_size"]

        key = (x, y)

        if key in screen["pixels"]:
            return

        try:

            canvas.create_rectangle(
                x * size,
                y * size,
                (x + 1) * size,
                (y + 1) * size,
                fill="white",
                outline="white",
                tags=f"pixel_{x}_{y}"
            )

            screen["pixels"].add(key)

        except tk.TclError:

            screen["closed"] = True

            self.remove_screen_bindings(
                self.current_screen
            )

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

        if not self.screen_exists(
            self.current_screen
        ):
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

            x = int(x)
            y = int(y)

        except (TypeError, ValueError):

            raise ValueError(
                "Pixel coordinates must be numbers."
            )

        key = (x, y)

        screen["pixels"].discard(
            key
        )

        try:

            screen["canvas"].delete(
                f"pixel_{x}_{y}"
            )

        except tk.TclError:

            screen["closed"] = True

            self.remove_screen_bindings(
                self.current_screen
            )

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

        if not self.screen_exists(
            self.current_screen
        ):
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

            screen["canvas"].delete(
                "all"
            )

            screen["pixels"].clear()
            screen["text_y"] = 20

        except tk.TclError:

            screen["closed"] = True

            self.remove_screen_bindings(
                self.current_screen
            )

            self.current_screen = None

            raise ValueError(
                "The DREAM screen was closed."
            )

    # ========================================================
    # BLOCK HELPERS
    # ========================================================

    def is_block_start(self, command):

        return re.match(
            r"^(scrn|rpt|w|if)\b",
            command
        ) is not None

    def find_block_end(
        self,
        lines,
        start
    ):

        depth = 1

        for i in range(
            start + 1,
            len(lines)
        ):

            command = lines[i].strip()

            if not command:
                continue

            if command.startswith("@"):
                continue

            if self.is_block_start(command):

                depth += 1

            elif command == "end":

                depth -= 1

                if depth == 0:
                    return i

        raise DreamError(
            "E02",
            "Missing 'end'.",
            start + 1
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

        for i in range(
            start + 1,
            end
        ):

            command = lines[i].strip()

            if not command:
                continue

            if command.startswith("@"):
                continue

            if self.is_block_start(command):

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

        if value.startswith("#"):

            name = value[1:].strip()

            if not self.valid_variable_name(name):
                raise ValueError(
                    f"Invalid variable name '{name}'."
                )

            if name not in self.variables:
                raise ValueError(
                    f"Unknown variable '{name}'."
                )

            return self.variables[name]

        if self.valid_variable_name(value):

            if value in self.variables:
                return self.variables[value]

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

        if re.fullmatch(
            r"-?\d+",
            value
        ):
            return int(value)

        if re.fullmatch(
            r"-?\d+\.\d+",
            value
        ):
            return float(value)

        if re.search(
            r"[+\-*/%]",
            value
        ):

            expression = (
                self.replace_math_variables(
                    value
                )
            )

            expression = (
                self.replace_bare_math_variables(
                    expression
                )
            )

            return self.safe_math(
                expression
            )

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
                "Invalid condition. "
                "Expected ==, !=, >, <, >= or <=."
            )

        parts = condition.split(
            selected_operator,
            1
        )

        if len(parts) != 2:

            raise ValueError(
                "Invalid condition."
            )

        left_text, right_text = parts

        if not left_text.strip():

            raise ValueError(
                "Condition is missing its left value."
            )

        if not right_text.strip():

            raise ValueError(
                "Condition is missing its right value."
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
                f"Cannot compare "
                f"{type(left).__name__} "
                f"with "
                f"{type(right).__name__}."
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
        block_lines,
        block_start_line
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
                f"'{event_type}'. "
                f"Use 'clk' or 'rel'."
            )

        old_binding_key = (
            screen_name,
            sequence
        )

        old_binding = self.key_bindings.get(
            old_binding_key
        )

        if old_binding:

            try:

                canvas.unbind(
                    sequence,
                    old_binding
                )

            except tk.TclError:
                pass

            self.key_bindings.pop(
                old_binding_key,
                None
            )

        handler_run_id = self.run_id

        def handler(
            event,
            lines=block_lines,
            screen_name=screen_name,
            source_line=block_start_line,
            expected_run_id=handler_run_id
        ):

            if expected_run_id != self.run_id:
                return

            if not self.running:
                return

            if not self.screen_exists(
                screen_name
            ):
                return

            screen = self.screens.get(
                screen_name
            )

            if not self.screen_alive(screen):
                return

            old_screen = self.current_screen

            self.current_screen = screen_name

            try:

                self.execute_block(
                    lines,
                    source_offset=source_line,
                    screen_context=screen_name
                )

            except DreamError as e:

                self.error(
                    e.code,
                    e.message,
                    e.line
                )

            except tk.TclError:

                if screen_name in self.screens:

                    self.screens[
                        screen_name
                    ]["closed"] = True

                self.current_screen = None

            except Exception as e:

                self.error(
                    "E99",
                    str(e),
                    source_line
                )

            finally:

                if self.screen_exists(
                    screen_name
                ):

                    self.current_screen = old_screen

                else:

                    self.current_screen = None

        try:

            binding_id = canvas.bind(
                sequence,
                handler
            )

            self.key_bindings[
                old_binding_key
            ] = binding_id

            canvas.focus_set()

        except tk.TclError:

            screen["closed"] = True

            self.key_bindings.pop(
                old_binding_key,
                None
            )

            raise ValueError(
                "Could not create keyboard binding."
            )

    # ========================================================
    # USER INPUT
    # ========================================================

    def request_input(self):

        if self.current_screen is None:

            try:

                value = simpledialog.askstring(
                    "DREAM Input",
                    "Input:"
                )

                return value or ""

            except tk.TclError:

                return ""

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

        try:

            entry = tk.Entry(
                canvas,
                bg="black",
                fg="white",
                insertbackground="white",
                font=("Consolas", 14)
            )

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

        try:
            entry.focus_set()
        except tk.TclError:
            pass

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
                canvas.delete(
                    window_id
                )
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
    #
    # IMPORTANT:
    # screen_context is passed through every nested block.
    # This prevents pxl/clrr from losing the active scrn.
    # ========================================================

    def execute_block(
        self,
        lines,
        start=0,
        end=None,
        source_offset=0,
        screen_context=None
    ):

        if end is None:
            end = len(lines)

        # ----------------------------------------------------
        # Preserve the caller's screen.
        # ----------------------------------------------------

        old_screen = self.current_screen

        # ----------------------------------------------------
        # If a screen context was explicitly provided,
        # restore/use it before executing this block.
        # ----------------------------------------------------

        if screen_context is not None:

            if self.screen_exists(
                screen_context
            ):

                self.current_screen = screen_context

        try:

            i = start

            while i < end:

                if not self.running:
                    return

                raw = lines[i]
                line = raw.strip()

                line_number = (
                    source_offset + i + 1
                )

                # ------------------------------------------------
                # Empty
                # ------------------------------------------------

                if not line:

                    i += 1
                    continue

                # ------------------------------------------------
                # Comment
                # ------------------------------------------------

                if line.startswith("@"):

                    i += 1
                    continue

                # ------------------------------------------------
                # End
                # ------------------------------------------------

                if line == "end":

                    return

                # ------------------------------------------------
                # Else
                # ------------------------------------------------

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

                    previous_screen = (
                        self.current_screen
                    )

                    self.current_screen = screen_name

                    try:

                        self.execute_block(
                            lines,
                            i + 1,
                            block_end,
                            source_offset=source_offset,
                            screen_context=screen_name
                        )

                    except DreamError:

                        raise

                    except tk.TclError:

                        screen["closed"] = True

                        self.remove_screen_bindings(
                            screen_name
                        )

                        self.current_screen = None

                    finally:

                        if self.screen_exists(
                            screen_name
                        ):

                            self.current_screen = (
                                previous_screen
                                if previous_screen is not None
                                else screen_name
                            )

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

                        if not isinstance(
                            parsed,
                            list
                        ):

                            raise ValueError(
                                "Array must be a list."
                            )

                        self.variables[name] = parsed

                    except Exception:

                        content = (
                            raw_array[1:-1].strip()
                        )

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

                    if index >= len(
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
                                "Random limits must be numbers."
                            )

                        low = int(low)
                        high = int(high)

                        if low > high:

                            raise ValueError(
                                "Random minimum cannot be greater "
                                "than maximum."
                            )

                        self.variables["random"] = (
                            random.randint(
                                low,
                                high
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

                    # --------------------------------------------
                    # TRUE BRANCH
                    # --------------------------------------------

                    if result:

                        self.execute_block(
                            lines,
                            i + 1,
                            (
                                else_index
                                if else_index is not None
                                else block_end
                            ),
                            source_offset=source_offset,
                            screen_context=(
                                screen_context
                                if screen_context is not None
                                else self.current_screen
                            )
                        )

                    # --------------------------------------------
                    # ELSE BRANCH
                    # --------------------------------------------

                    elif else_index is not None:

                        self.execute_block(
                            lines,
                            else_index + 1,
                            block_end,
                            source_offset=source_offset,
                            screen_context=(
                                screen_context
                                if screen_context is not None
                                else self.current_screen
                            )
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

                    active_screen = (
                        screen_context
                        if screen_context is not None
                        else self.current_screen
                    )

                    # --------------------------------------------
                    # FOREVER
                    # --------------------------------------------

                    if amount.lower() == "frvr":

                        while self.running:

                            if active_screen is not None:

                                if not self.screen_exists(
                                    active_screen
                                ):

                                    self.current_screen = None
                                    self.running = False
                                    break

                                # --------------------------------
                                # KEEP SCREEN ACTIVE
                                # --------------------------------

                                self.current_screen = (
                                    active_screen
                                )

                            try:

                                self.execute_block(
                                    block_lines,
                                    source_offset=(
                                        source_offset + i + 1
                                    ),
                                    screen_context=active_screen
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
                                    active_screen
                                    and active_screen in self.screens
                                ):

                                    self.screens[
                                        active_screen
                                    ]["closed"] = True

                                    self.remove_screen_bindings(
                                        active_screen
                                    )

                                self.current_screen = None
                                break

                            except Exception as e:

                                self.error(
                                    "E99",
                                    str(e),
                                    source_offset + i + 1
                                )

                                break

                            finally:

                                if (
                                    active_screen
                                    and self.screen_exists(
                                        active_screen
                                    )
                                ):

                                    self.current_screen = (
                                        active_screen
                                    )

                                else:

                                    self.current_screen = None

                            try:

                                self.root.update()

                            except tk.TclError:

                                self.running = False
                                break

                            time.sleep(
                                self.loop_delay
                            )

                        i = block_end + 1
                        continue

                    # --------------------------------------------
                    # NORMAL REPEAT
                    # --------------------------------------------

                    try:

                        parsed_amount = (
                            self.parse_condition_value(
                                amount
                            )
                        )

                        if isinstance(
                            parsed_amount,
                            bool
                        ):

                            raise ValueError(
                                "Repeat amount must be a number."
                            )

                        if not isinstance(
                            parsed_amount,
                            (int, float)
                        ):

                            raise ValueError(
                                "Repeat amount must be a number."
                            )

                        if (
                            isinstance(
                                parsed_amount,
                                float
                            )
                            and not parsed_amount.is_integer()
                        ):

                            raise ValueError(
                                "Repeat amount must be a whole number."
                            )

                        count = int(
                            parsed_amount
                        )

                        if count < 0:

                            raise ValueError(
                                "Repeat amount cannot be negative."
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

                        if active_screen is not None:

                            if not self.screen_exists(
                                active_screen
                            ):

                                self.current_screen = None
                                break

                            self.current_screen = (
                                active_screen
                            )

                        try:

                            self.execute_block(
                                block_lines,
                                source_offset=(
                                    source_offset + i + 1
                                ),
                                screen_context=active_screen
                            )

                        except DreamError:

                            raise

                        except tk.TclError:

                            if (
                                active_screen
                                and active_screen in self.screens
                            ):

                                self.screens[
                                    active_screen
                                ]["closed"] = True

                                self.remove_screen_bindings(
                                    active_screen
                                )

                            self.current_screen = None
                            break

                        finally:

                            if (
                                active_screen
                                and self.screen_exists(
                                    active_screen
                                )
                            ):

                                self.current_screen = (
                                    active_screen
                                )

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
                        block_lines,
                        line_number
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

                    if not isinstance(
                        value,
                        list
                    ):

                        raise DreamError(
                            "E04",
                            f"Variable '{name}' is not an array.",
                            line_number
                        )

                    if index >= len(value):

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

        finally:

            # ----------------------------------------------------
            # RESTORE THE SCREEN THAT WAS ACTIVE BEFORE THIS
            # BLOCK WAS EXECUTED.
            #
            # If this block has an explicit screen context,
            # keep that context instead.
            # ----------------------------------------------------

            if screen_context is not None:

                if self.screen_exists(
                    screen_context
                ):

                    self.current_screen = (
                        screen_context
                    )

                else:

                    self.current_screen = None

            else:

                self.current_screen = old_screen

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

        self.key_bindings.clear()

    # ========================================================
    # RUN
    # ========================================================

    def run(self, code):

        self.run_id += 1

        self.running = False

        self.close_all_screens()

        self.variables = {}
        self.current_screen = None

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
    # STOP
    # ========================================================

    def stop(self):

        self.running = False

        self.run_id += 1

        self.current_screen = None


# ============================================================
# DREAM IDE
# ============================================================


class DreamIDE:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "DREAM v0.9.1 IDE"
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
            text="DREAM v0.9.1",
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

        self.interpreter = None

        self.load_default_code()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close_ide
        )

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

        try:

            self.output_box.delete(
                "1.0",
                "end"
            )

        except tk.TclError:

            pass

    # ========================================================
    # RUN
    # ========================================================

    def run_code(self):

        self.clear_output()

        code = self.editor.get(
            "1.0",
            "end"
        )

        if self.interpreter is not None:

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

        if self.interpreter is not None:

            try:

                self.interpreter.stop()
                self.interpreter.close_all_screens()

            except Exception:
                pass

    # ========================================================
    # CLOSE IDE
    # ========================================================

    def close_ide(self):

        if self.interpreter is not None:

            try:

                self.interpreter.stop()
                self.interpreter.close_all_screens()

            except Exception:
                pass

        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ========================================================
    # DEFAULT DREAM TEST
    # ========================================================

    def load_default_code(self):

        code = """@ DREAM v0.9.1 STABILITY TEST

s hp = 100
s score = 0

r [DREAM v0.9.1]
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

    @ --------------------------------------------------------
    @ NESTED SCREEN TEST
    @ --------------------------------------------------------

    s testx = 10
    s testy = 10

    rpt[3]

        pxl[testx,testy]

        testx = testx + 1

    end

    if testx == 13

        clrr[10,10]
        pxl[20,20]

    end

end
"""

        self.editor.delete(
            "1.0",
            "end"
        )

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