# DREAM

### A custom programming language by OpenQ

**DREAM 1.0** is a custom programming language designed to be challenging, experimental, and different from traditional programming languages.

DREAM is built mainly in **Python** and comes with its own interpreter/IDE.

> **DREAM 1.0 — The first major release.**

---

## ✦ What is DREAM?

DREAM is a programming language created by **OpenQ**.

It has its own syntax for:

* Variables
* Output
* User input
* Mathematics
* Random values
* Conditions
* Loops
* Arrays
* Screens
* Pixels
* Keyboard events
* Interactive programs and games

DREAM is not designed to simply imitate Python. It has its own rules and syntax.

---

## 🚀 DREAM 1.0

DREAM 1.0 is the first major release of the language.

This release focuses on making the core DREAM experience stable and usable while keeping the language's unique syntax intact.

### 1.0 includes:

* Improved interpreter stability
* Improved variable handling
* Mathematical expressions
* Random value generation
* Normal repeat loops
* Infinite loops
* Conditions and `else`
* Arrays
* Screen creation
* Pixel drawing
* Pixel clearing
* Keyboard events
* Multiple keyboard bindings
* User input
* Code status indicators
* Run and stop shortcuts

---

# 📖 DREAM Syntax

## Variables

Create variables with `s`:

```dream
s name = OpenQ
s age = 15
```

Variables can later be changed:

```dream
age = 16
```

---

## Output

Use `r` to output text:

```dream
r [Hello from DREAM!]
```

Variables can be displayed using `#`:

```dream
s name = OpenQ

r [Welcome to {name}]
```

---

## User Input

DREAM can request input from the user:

```dream
r [What is your name?]
r #usrinp
```

`#usrinp` represents user input.

---

## Mathematics

Use `m` for mathematical expressions:

```dream
m [2+2]
```

Variables can also be used in calculations:

```dream
s x = 10
s y = 5

m [x+y]
```

---

## Random Values

Generate a random number with `rdm`:

```dream
rdm [1,100]
```

Random values can also be assigned to variables:

```dream
s number = rdm [1,100]
```

Or reassigned later:

```dream
number = rdm [1,100]
```

---

# 🔁 Loops

## Repeat

Repeat a block a specific number of times:

```dream
rpt[5]

    r [Hello!]

end
```

## Infinite Loop

Use `frvr` for an infinite loop:

```dream
rpt[frvr]

    r [DREAM]

end
```

Infinite loops are useful for interactive programs and games.

---

# ❓ Conditions

DREAM supports `if`, `else`, and `end`:

```dream
s age = 15

if age >= 13

    r [You can use DREAM!]

else

    r [Welcome!]

end
```

---

# 📦 Arrays

Create an array with `a`:

```dream
a inventory = [apple,banana,orange]
```

Access an item using its index:

```dream
r #inventory[0]
```

Arrays can also be changed:

```dream
inventory[0] = sword
```

---

# 🖥️ Screens

Create a screen with `scrn`:

```dream
scrn game

    r [Welcome to the game!]

end
```

Screens are especially useful for graphical DREAM programs.

---

# 🟦 Pixels

DREAM can draw individual pixels:

```dream
scrn pixel_demo

    pxl[10,10]
    pxl[11,10]
    pxl[12,10]

end
```

Pixels can be cleared with `clrr`:

```dream
clrr[10,10]
```

Clear the screen with:

```dream
clra
```

---

# ⌨️ Keyboard Events

DREAM supports keyboard events using `w`.

For example:

```dream
w [space] clk

    r [SPACE PRESSED!]

end
```

Arrow keys have aliases:

```dream
w [u-a] clk
w [d-a] clk
w [l-a] clk
w [r-a] clk
```

These represent:

* `u-a` → Up
* `d-a` → Down
* `l-a` → Left
* `r-a` → Right

Other supported keys include:

* `space`
* `enter`
* `esc`
* `tab`
* `backspace`
* `shift`
* `ctrl`
* `alt`

DREAM also supports key release events:

```dream
w [space] rel

    r [SPACE RELEASED!]

end
```

---

# 🎮 Example Game

DREAM can combine screens, variables, pixels, random numbers, keyboard events, conditions, and infinite loops to create games.

A simplified example:

```dream
scrn game

    s x = 20
    s y = 20

    s dx = 1
    s dy = 0

    s foodx = rdm [1,55]
    s foody = rdm [1,40]

    pxl[x,y]
    pxl[foodx,foody]

    w [u-a] clk

        dy = -1
        dx = 0

    end

    w [d-a] clk

        dy = 1
        dx = 0

    end

    w [l-a] clk

        dx = -1
        dy = 0

    end

    w [r-a] clk

        dx = 1
        dy = 0

    end

    rpt[frvr]

        clrr[x,y]

        x = x + dx
        y = y + dy

        pxl[x,y]

        if x == foodx

            if y == foody

                clrr[foodx,foody]

                foodx = rdm [1,55]
                foody = rdm [1,40]

                pxl[foodx,foody]

            end

        end

    end

end
```

This demonstrates how DREAM's different features can work together to create an interactive program.

---

# 💻 Running DREAM

DREAM is written in Python and uses a Tkinter-based IDE/interpreter.

Download:

```text
dream.py
```

Then run it with Python.

The DREAM IDE provides:

* Code editor
* Output panel
* Graphical screen support
* Run controls
* Stop controls
* Status indicator

### Keyboard shortcuts

**Ctrl + Enter**
Run the program.

**Escape**
Stop the program.

---

# 📁 Included Examples

This repository includes several `.dream` examples:

### `hello.dream`

A basic introduction to output and variables.

### `input.dream`

Demonstrates user input and conditions.

### `pixel.dream`

Demonstrates pixel drawing.

### `game.dream`

A graphical interactive game demonstrating movement, keyboard events, random food, collision detection, and an infinite game loop.

---

# 🛠️ Built With

DREAM is currently implemented using:

* **Python**
* **Tkinter**

The language itself is designed by **OpenQ**.

---

# 📜 Version History

## DREAM 1.0

**First major release.**

Improved stability, usability, keyboard controls, random values, loops, conditions, arrays, pixels, and the overall interpreter experience.

## DREAM 0.9.2

Quality-of-life update focused on keyboard input, random assignments, infinite loops, and overall usability.

## DREAM 0.9.1

Stability and bug-fix release.

## DREAM 0.9

Major development milestone in DREAM's development.

---

# 🎯 Philosophy

DREAM is about creating a language that feels like its **own thing**.

It doesn't try to be Python.

It doesn't try to copy another language.

DREAM has its own syntax, its own interpreter, and its own way of doing things.

**Learn it. Experiment with it. Break it. Build with it.**

---

# 🌐 DREAM

DREAM is part of **OpenQ**, a collection of creative programming, art, music, and experimental projects.

**DREAM 1.0**

> Made by OpenQ 💙

---

## License

See the repository for the current license information.
