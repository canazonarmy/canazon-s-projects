import flet as ft
import asyncio
import random

WIDTH, HEIGHT = 360, 600
FPS = 60

# Flappy
SKY = "#71c5cf"
GROUND_FL = "#ded895"
PIPE_GREEN = "#6abe30"
BIRD_Y = "#ffdc3c"
BIRD_O = "#ff9628"
WHITE = "#ffffff"

# Crossy
CELL = 40
COLS = 9
VISIBLE_ROWS = HEIGHT // CELL
GRASS = "#7ec850"
ROAD = "#3a3a3a"
CAR_COLORS = ["#e74c3c", "#3498db", "#f39c12", "#9b59b6", "#1abc9c"]


def main(page: ft.Page):
    page.title = "Arcade"
    page.padding = 0
    page.bgcolor = "#0f1115"
    try:
        page.window.width = WIDTH
        page.window.height = HEIGHT
    except Exception:
        pass

    tasks = {"current": None}
    key_handler = {"fn": None}

    def on_key(e):
        fn = key_handler.get("fn")
        if fn:
            try:
                fn(e)
            except Exception:
                pass

    try:
        page.on_keyboard_event = on_key
    except Exception:
        pass

    def cancel_current():
        t = tasks.get("current")
        if t is not None and not t.done():
            try:
                t.cancel()
            except Exception:
                pass
        tasks["current"] = None

    async def game_loop(tick):
        try:
            while True:
                tick()
                try:
                    page.update()
                except Exception:
                    pass
                await asyncio.sleep(1 / FPS)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    def show(container, tick=None, on_key_fn=None):
        cancel_current()
        page.controls.clear()
        page.add(container)
        key_handler["fn"] = on_key_fn
        try:
            page.update()
        except Exception:
            pass
        if tick:
            tasks["current"] = page.run_task(game_loop, tick)

    def goto_menu(e=None):
        show(build_menu(), None, None)

    def goto_flappy(e=None):
        c, t, k = make_flappy()
        show(c, t, k)

    def goto_crossy(e=None):
        c, t, k = make_crossy()
        show(c, t, k)

    # ============================================================
    # MENU
    # ============================================================
    def build_menu():
        title = ft.Text("ARCADE", size=52, weight=ft.FontWeight.BOLD,
                        color="#7aa2f7")
        sub = ft.Text("Choose a game", size=15, color="#888888")
        flappy_btn = ft.ElevatedButton(
            text="FLAPPY BIRD", width=240, height=60,
            bgcolor="#1f6feb", color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            on_click=goto_flappy)
        crossy_btn = ft.ElevatedButton(
            text="CROSSY ROAD", width=240, height=60,
            bgcolor="#238636", color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            on_click=goto_crossy)
        return ft.Container(
            width=WIDTH, height=HEIGHT, bgcolor="#0f1115",
            content=ft.Column(
                [title, sub, ft.Container(height=40),
                 flappy_btn, ft.Container(height=16), crossy_btn],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8))

    # ============================================================
    # FLAPPY BIRD
    # ============================================================
    def make_flappy():
        GRAV, FLAP = 0.5, -8
        PIPE_W = 70
        BASE_GAP, MIN_GAP = 180, 110
        BASE_SPEED, MAX_SPEED = 3.0, 6.0
        BASE_SPAWN, MIN_SPAWN = 95, 55
        GH = 80

        def diff(score):
            t = min(score / 25.0, 1.0)
            return (BASE_SPEED + (MAX_SPEED - BASE_SPEED) * t,
                    int(BASE_GAP - (BASE_GAP - MIN_GAP) * t),
                    int(BASE_SPAWN - (BASE_SPAWN - MIN_SPAWN) * t))

        bird = ft.Container(
            width=30, height=30, bgcolor=BIRD_Y, border_radius=15,
            left=65, top=HEIGHT // 2 - 15,
            content=ft.Container(width=14, height=14, bgcolor=BIRD_O,
                                 border_radius=7),
            alignment=ft.alignment.center)

        score_text = ft.Text("0", size=36, weight=ft.FontWeight.BOLD,
                             color=WHITE)

        pipe_layer = ft.Stack(width=WIDTH, height=HEIGHT, left=0, top=0)

        start_screen = ft.Container(
            bgcolor="#00000088", left=0, top=0, right=0, bottom=0,
            content=ft.Column(
                [ft.Text("FLAPPY", size=48, weight=ft.FontWeight.BOLD,
                         color=WHITE),
                 ft.Container(height=10),
                 ft.Text("Tap / Space to flap.\nArrow up also works.",
                         size=14, color=WHITE,
                         text_align=ft.TextAlign.CENTER),
                 ft.Container(height=20),
                 ft.ElevatedButton(text="START", bgcolor="#1f6feb",
                                   color="white")],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8),
            alignment=ft.alignment.center)

        over_score = ft.Text("Score: 0", size=22, color=WHITE)
        over_best = ft.Text("Best: 0", size=15, color="#dddddd")
        gameover_screen = ft.Container(
            bgcolor="#00000099", left=0, top=0, right=0, bottom=0,
            content=ft.Column(
                [ft.Text("GAME OVER", size=38, weight=ft.FontWeight.BOLD,
                         color="#ff5c5c"),
                 over_score, over_best, ft.Container(height=16),
                 ft.ElevatedButton(text="RETRY", bgcolor="#238636",
                                   color="white"),
                 ft.TextButton("Menu", on_click=goto_menu)],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8),
            alignment=ft.alignment.center, visible=False)

        state = {"y": HEIGHT // 2, "vy": 0, "pipes": [], "frame": 0,
                 "score": 0, "best": 0, "screen": "start"}

        def reset():
            state.update({"y": HEIGHT // 2, "vy": 0, "frame": 0, "score": 0})
            for p in state["pipes"]:
                try:
                    pipe_layer.controls.remove(p["top"])
                    pipe_layer.controls.remove(p["bot"])
                except Exception:
                    pass
            state["pipes"] = []
            bird.top = state["y"] - 15
            score_text.value = "0"

        def spawn():
            speed, gap, _ = diff(state["score"])
            gy = random.randint(140, HEIGHT - GH - 140)
            top_h = gy - gap // 2
            bot_y = gy + gap // 2
            bot_h = HEIGHT - GH - bot_y
            t = ft.Container(bgcolor=PIPE_GREEN, left=WIDTH + 20, top=0,
                             width=PIPE_W, height=top_h)
            b = ft.Container(bgcolor=PIPE_GREEN, left=WIDTH + 20, top=bot_y,
                             width=PIPE_W, height=bot_h)
            pipe_layer.controls.append(t)
            pipe_layer.controls.append(b)
            state["pipes"].append({"x": WIDTH + 20, "gy": gy, "gap": gap,
                                   "passed": False, "speed": speed,
                                   "top": t, "bot": b})

        def start(e=None):
            reset()
            state["screen"] = "playing"
            start_screen.visible = False
            gameover_screen.visible = False

        def game_over():
            state["screen"] = "gameover"
            if state["score"] > state["best"]:
                state["best"] = state["score"]
            over_score.value = f"Score: {state['score']}"
            over_best.value = f"Best: {state['best']}"
            gameover_screen.visible = True

        def flap():
            if state["screen"] == "playing":
                state["vy"] = FLAP
            else:
                start()

        def on_tap(e):
            flap()

        def on_key_flappy(e):
            k = getattr(e, "key", "")
            kc = getattr(e, "key_code", 0)
            if kc in (32, 38) or k in (" ", "Arrow Up", "Space"):
                flap()

        try:
            start_screen.content.controls[4].on_click = start
            gameover_screen.content.controls[4].on_click = start
        except Exception:
            pass

        def tick():
            if state["screen"] != "playing":
                return
            state["vy"] += GRAV
            state["y"] += state["vy"]
            state["frame"] += 1

            _, _, spawn_every = diff(state["score"])
            if state["frame"] % spawn_every == 0:
                spawn()

            bx, by = 80, state["y"]
            for p in state["pipes"]:
                p["x"] -= p["speed"]
                p["top"].left = p["x"]
                p["bot"].left = p["x"]

            keep = []
            for p in state["pipes"]:
                if p["x"] + PIPE_W > -10:
                    keep.append(p)
                else:
                    try:
                        pipe_layer.controls.remove(p["top"])
                        pipe_layer.controls.remove(p["bot"])
                    except Exception:
                        pass
            state["pipes"] = keep

            if by + 15 >= HEIGHT - GH or by - 15 <= 0:
                game_over()
                return

            for p in state["pipes"]:
                gy, gap = p["gy"], p["gap"]
                top_h = gy - gap // 2
                bot_y = gy + gap // 2
                if bx + 15 > p["x"] and bx - 15 < p["x"] + PIPE_W:
                    if by - 15 < top_h or by + 15 > bot_y:
                        game_over()
                        return
                if not p["passed"] and p["x"] + PIPE_W < bx:
                    p["passed"] = True
                    state["score"] += 1
                    score_text.value = str(state["score"])

            bird.top = by - 15

        # tap area: GestureDetector wrapped in a positioned Container
        tap_area = ft.Container(
            left=0, top=0, width=WIDTH, height=HEIGHT,
            content=ft.GestureDetector(
                content=ft.Container(width=WIDTH, height=HEIGHT,
                                     bgcolor="#00000001"),
                on_tap=on_tap),
        )

        stack = ft.Stack(
            controls=[
                ft.Container(bgcolor=SKY, width=WIDTH, height=HEIGHT,
                             left=0, top=0),
                pipe_layer,
                bird,
                ft.Container(bgcolor=GROUND_FL, left=0, right=0, bottom=0,
                             height=GH),
                ft.Container(content=score_text, top=40, left=0, right=0,
                             alignment=ft.alignment.center),
                tap_area,
                start_screen,
                gameover_screen],
            width=WIDTH, height=HEIGHT)

        return stack, tick, on_key_flappy

    # ============================================================
    # CROSSY ROAD
    # ============================================================
    def make_crossy():
        bg_layer = ft.Stack(width=WIDTH, height=HEIGHT, left=0, top=0)
        car_layer = ft.Stack(width=WIDTH, height=HEIGHT, left=0, top=0)

        player = ft.Container(
            width=CELL - 6, height=CELL - 6, bgcolor="#f5f5f5",
            border_radius=6, left=4 * CELL + 3, top=HEIGHT - CELL + 3,
            content=ft.Container(width=CELL - 16, height=CELL - 16,
                                 bgcolor="#f0c040", border_radius=4),
            alignment=ft.alignment.center)

        world = ft.Stack(
            controls=[bg_layer, car_layer, player],
            width=WIDTH, height=HEIGHT, left=0, top=0)

        score_text = ft.Text("0", size=28, weight=ft.FontWeight.BOLD,
                             color=WHITE)
        score_bg = ft.Container(content=score_text, top=20, left=0, right=0,
                                alignment=ft.alignment.center)

        STATE = {"col": 4, "row": 0, "rows": {}, "score": 0, "best": 0,
                 "screen": "playing", "cam_off": 4}

        def y_for_row(idx):
            cam_row = STATE["row"] - STATE["cam_off"]
            offset = idx - cam_row
            return HEIGHT - (offset + 1) * CELL

        def ensure_row(idx):
            if idx in STATE["rows"]:
                return
            rtype = "grass" if idx <= 0 else random.choice(
                ["road", "road", "grass"])
            bg = ft.Container(
                bgcolor=(GRASS if rtype == "grass" else ROAD),
                left=0, top=0, width=WIDTH, height=CELL)
            bg_layer.controls.append(bg)
            row = {"type": rtype, "cars": [], "bg": bg, "car_ctrls": []}
            if rtype == "road":
                direction = random.choice([-1, 1])
                speed = random.uniform(1.5, 3.0) * direction
                num = random.randint(1, 3)
                spacing = WIDTH / num
                for i in range(num):
                    cx = i * spacing + random.uniform(0, spacing * 0.4)
                    cw, ch = CELL + 10, CELL - 8
                    car = ft.Container(
                        bgcolor=random.choice(CAR_COLORS),
                        width=cw, height=ch, border_radius=4,
                        left=cx, top=0)
                    car_layer.controls.append(car)
                    row["cars"].append({"x": cx, "w": cw, "h": ch,
                                        "speed": speed, "c": car})
                    row["car_ctrls"].append(car)
            STATE["rows"][idx] = row

        def update_positions():
            cam_row = STATE["row"] - STATE["cam_off"]
            lo = cam_row - 1
            hi = STATE["row"] + VISIBLE_ROWS - STATE["cam_off"] + 1
            for i in range(lo, hi + 1):
                ensure_row(i)
            for idx, row in STATE["rows"].items():
                y = y_for_row(idx)
                if y < -CELL or y > HEIGHT + CELL:
                    row["bg"].visible = False
                    for c in row["car_ctrls"]:
                        c.visible = False
                    continue
                row["bg"].visible = True
                row["bg"].top = y
                if row["type"] == "road":
                    for cd in row["cars"]:
                        cd["c"].visible = True
                        cd["c"].left = cd["x"]
                        cd["c"].top = y + 4
            player.left = STATE["col"] * CELL + 3
            player.top = y_for_row(STATE["row"]) + 3
            score_text.value = str(STATE["score"])

        def move(dc, dr):
            if STATE["screen"] != "playing":
                return
            nc = STATE["col"] + dc
            nr = STATE["row"] + dr
            if nc < 0 or nc >= COLS or nr < 0:
                return
            STATE["col"] = nc
            STATE["row"] = nr
            if nr > STATE["score"]:
                STATE["score"] = nr
            ensure_row(nr)

        def fwd(e=None): move(0, 1)
        def lft(e=None): move(-1, 0)
        def rgt(e=None): move(1, 0)
        def bck(e=None): move(0, -1)

        def check_collision():
            row = STATE["rows"].get(STATE["row"])
            if not row or row["type"] != "road":
                return
            px1 = STATE["col"] * CELL + 4
            px2 = (STATE["col"] + 1) * CELL - 4
            for car in row["cars"]:
                if px2 > car["x"] and px1 < car["x"] + car["w"]:
                    STATE["screen"] = "gameover"
                    return

        def mk_dir(label, handler):
            return ft.Container(
                content=ft.Text(label, size=22, weight=ft.FontWeight.BOLD,
                                color=WHITE),
                width=55, height=55, bgcolor="#00000088", border_radius=28,
                alignment=ft.alignment.center, on_click=handler, ink=True)

        controls_row = ft.Container(
            content=ft.Row([mk_dir("←", lft), mk_dir("↓", bck),
                            mk_dir("→", rgt)],
                           alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            left=0, right=0, bottom=10, height=70,
            alignment=ft.alignment.center)

        go_score = ft.Text("Score: 0", size=22, color=WHITE)
        go_best = ft.Text("Best: 0", size=15, color="#dddddd")
        go_screen = ft.Container(
            bgcolor="#00000099", left=0, top=0, right=0, bottom=0,
            content=ft.Column(
                [ft.Text("CRASHED!", size=38, weight=ft.FontWeight.BOLD,
                         color="#ff5c5c"),
                 go_score, go_best, ft.Container(height=16),
                 ft.ElevatedButton(text="RETRY", bgcolor="#238636",
                                   color="white"),
                 ft.TextButton("Menu", on_click=goto_menu)],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8),
            alignment=ft.alignment.center, visible=False)

        def reset():
            STATE["col"] = 4
            STATE["row"] = 0
            STATE["score"] = 0
            STATE["screen"] = "playing"
            for row in STATE["rows"].values():
                try:
                    bg_layer.controls.remove(row["bg"])
                except Exception:
                    pass
                for c in row["car_ctrls"]:
                    try:
                        car_layer.controls.remove(c)
                    except Exception:
                        pass
            STATE["rows"] = {}
            go_screen.visible = False
            ensure_row(0)

        try:
            go_screen.content.controls[4].on_click = lambda e: reset()
        except Exception:
            pass

        ensure_row(0)

        # --- swipe state ---
        swipe = {"x0": 0, "y0": 0, "active": False}

        def pos(e):
            x = getattr(e, "local_x", None)
            if x is None:
                x = getattr(e, "x", 0)
            y = getattr(e, "local_y", None)
            if y is None:
                y = getattr(e, "y", 0)
            return x, y

        def on_pan_start(e):
            x, y = pos(e)
            swipe["x0"] = x
            swipe["y0"] = y
            swipe["active"] = True

        def on_pan_end(e):
            if not swipe["active"]:
                fwd()
                return
            swipe["active"] = False
            x, y = pos(e)
            dx = x - swipe["x0"]
            dy = y - swipe["y0"]
            threshold = 25
            if abs(dx) < threshold and abs(dy) < threshold:
                fwd()
                return
            if abs(dx) > abs(dy):
                if dx > 0: rgt()
                else: lft()
            else:
                if dy > 0: bck()   # swipe down = move back
                else: fwd()        # swipe up = move forward

        def on_tap(e):
            fwd()

        tap_area = ft.Container(
            left=0, top=0, width=WIDTH, height=HEIGHT,
            content=ft.GestureDetector(
                content=ft.Container(width=WIDTH, height=HEIGHT,
                                     bgcolor="#00000001"),
                on_tap=on_tap,
                on_pan_start=on_pan_start,
                on_pan_end=on_pan_end),
        )

        root = ft.Stack(
            controls=[world, score_bg, tap_area, controls_row, go_screen],
            width=WIDTH, height=HEIGHT)

        def on_key_crossy(e):
            k = getattr(e, "key", "")
            kc = getattr(e, "key_code", 0)
            if kc == 38 or k == "Arrow Up":
                fwd()
            elif kc == 40 or k == "Arrow Down":
                bck()
            elif kc == 37 or k == "Arrow Left":
                lft()
            elif kc == 39 or k == "Arrow Right":
                rgt()

        def tick():
            if STATE["screen"] != "playing":
                return
            for row in STATE["rows"].values():
                if row["type"] != "road":
                    continue
                for car in row["cars"]:
                    car["x"] += car["speed"]
                    if car["speed"] > 0 and car["x"] > WIDTH:
                        car["x"] = -car["w"] - random.uniform(0, 100)
                    elif car["speed"] < 0 and car["x"] + car["w"] < 0:
                        car["x"] = WIDTH + random.uniform(0, 100)
            check_collision()
            if STATE["screen"] == "gameover":
                if STATE["score"] > STATE["best"]:
                    STATE["best"] = STATE["score"]
                go_score.value = f"Score: {STATE['score']}"
                go_best.value = f"Best: {STATE['best']}"
                go_screen.visible = True
            update_positions()

        return root, tick, on_key_crossy

    # ============================================================
    # START
    # ============================================================
    async def _first():
        await asyncio.sleep(0.05)
        goto_menu()

    page.run_task(_first)


ft.app(target=main)