#!/usr/bin/env python3
"""小飞机弹弓闯关模拟 Web 版（Flask）。"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

from flask import Flask, redirect, render_template_string, request, url_for

from plane_game import FlightSimulator, FlightState, Game

app = Flask(__name__)
GAME = Game()
CURRENT_LEVEL_INDEX = 0
LAST_MESSAGE = "欢迎来到小飞机弹弓闯关模拟 Web 版！"


HTML = """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>小飞机弹弓闯关模拟（Web）</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; background: #f7f9fc; }
      .card { background: #fff; border-radius: 12px; box-shadow: 0 2px 14px rgba(0,0,0,.08); padding: 1.2rem 1.4rem; margin-bottom: 1rem; }
      .row { display: flex; gap: .8rem; flex-wrap: wrap; }
      button { padding: .45rem .8rem; border: 0; border-radius: 8px; background: #2b7cff; color: #fff; cursor: pointer; }
      button.secondary { background: #65748b; }
      input { padding: .45rem .6rem; border-radius: 8px; border: 1px solid #d4dbe5; width: 9rem; }
      .ok { color: #0b7a31; }
      .warn { color: #8a4b00; }
      code { background: #eef2f8; padding: .15rem .35rem; border-radius: 6px; }
    </style>
  </head>
  <body>
    <h1>小飞机弹弓闯关模拟（Web）</h1>

    <div class="card">
      <h3>状态</h3>
      <p>金币：<b>{{ coins }}</b>，当前关卡：<b>{{ level_id }}</b> / {{ total_levels }}</p>
      <p>飞机参数：<code>{{ plane }}</code></p>
      <p>弹弓参数：<code>{{ slingshot }}</code></p>
      <p class="warn">{{ message }}</p>
    </div>

    <div class="card">
      <h3>商店</h3>
      <form method="post" action="/upgrade" class="row">
        <button name="item" value="plane">升级飞机（120）</button>
        <button name="item" value="slingshot">升级弹弓（90）</button>
      </form>
    </div>

    <div class="card">
      <h3>发射当前关卡</h3>
      <p>目标距离：<b>{{ target_distance }}m</b>；障碍物：<code>{{ obstacles }}</code></p>
      <form method="post" action="/launch" class="row">
        <label>角度(°)
          <input type="number" step="1" min="5" max="60" name="angle" value="24" required />
        </label>
        <label>力度(0.1~1.0)
          <input type="number" step="0.01" min="0.1" max="1.0" name="power" value="0.88" required />
        </label>
        <button type="submit">发射！</button>
      </form>
      <form method="post" action="/reset" style="margin-top:.7rem">
        <button class="secondary" type="submit">重置游戏</button>
      </form>
    </div>
  </body>
</html>
"""


def _level():
    return GAME.levels[CURRENT_LEVEL_INDEX]


def _play_level_manual(angle_deg: float, power: float) -> tuple[bool, int, str]:
    level = _level()
    speed0 = GAME.slingshot.launch_speed(power)
    angle = math.radians(angle_deg)
    state = FlightState(vx=speed0 * math.cos(angle), vy=speed0 * math.sin(angle))

    sim = FlightSimulator(GAME.plane, level)
    next_coin_mark = level.coin_interval
    gained = 0

    while True:
        target_height = 7.0
        for ob in level.obstacles:
            if state.x + 12 >= ob.x_start and state.x <= ob.x_end:
                target_height = max(target_height, ob.clearance_height + 2.5)

        attack_input = max(-1.0, min(1.0, (target_height - state.y) * 0.15))
        state = sim.step(state, attack_input)

        if not all(math.isfinite(v) for v in (state.x, state.y, state.vx, state.vy)):
            return False, gained, "数值发散，判定失败。"

        if state.y <= 0:
            return False, gained, f"坠地于 x={state.x:.1f}m"

        for ob in level.obstacles:
            if ob.collides(state.x, state.y):
                return False, gained, f"撞上障碍物（x={ob.x_start}-{ob.x_end}m）"

        if state.x >= next_coin_mark:
            crossed = int((state.x - next_coin_mark) // level.coin_interval) + 1
            crossed = min(crossed, 1000)
            gained += crossed * 10
            next_coin_mark += crossed * level.coin_interval

        if state.x >= level.target_distance:
            gained += level.completion_bonus
            return True, gained, f"通过第 {level.level_id} 关！用时 {state.t:.1f}s, 终点高度 {state.y:.1f}m"

        if state.t > 35:
            return False, gained, "超时，判定失败。"


@app.get("/")
def index() -> str:
    level = _level()
    return render_template_string(
        HTML,
        coins=GAME.coins,
        level_id=level.level_id,
        total_levels=len(GAME.levels),
        target_distance=level.target_distance,
        obstacles=[(o.x_start, o.x_end, o.clearance_height) for o in level.obstacles],
        plane=asdict(GAME.plane),
        slingshot=asdict(GAME.slingshot),
        message=LAST_MESSAGE,
    )


@app.post("/upgrade")
def upgrade() -> Any:
    global LAST_MESSAGE
    item = request.form.get("item")
    if item == "plane":
        if GAME.coins >= 120:
            GAME.coins -= 120
            GAME.plane.upgrade()
            LAST_MESSAGE = "飞机升级完成。"
        else:
            LAST_MESSAGE = "金币不足，无法升级飞机。"
    elif item == "slingshot":
        if GAME.coins >= 90:
            GAME.coins -= 90
            GAME.slingshot.upgrade()
            LAST_MESSAGE = "弹弓升级完成。"
        else:
            LAST_MESSAGE = "金币不足，无法升级弹弓。"
    return redirect(url_for("index"))


@app.post("/launch")
def launch() -> Any:
    global CURRENT_LEVEL_INDEX, LAST_MESSAGE
    try:
        angle = float(request.form.get("angle", "24"))
        power = float(request.form.get("power", "0.88"))
    except ValueError:
        LAST_MESSAGE = "输入格式错误，请输入数字。"
        return redirect(url_for("index"))

    passed, gained, msg = _play_level_manual(angle, power)
    GAME.coins += gained
    if passed:
        if CURRENT_LEVEL_INDEX == len(GAME.levels) - 1:
            LAST_MESSAGE = f"{msg} 恭喜通关！最终金币：{GAME.coins}"
        else:
            CURRENT_LEVEL_INDEX += 1
            LAST_MESSAGE = f"{msg} 获得金币 {gained}，已进入下一关。"
    else:
        LAST_MESSAGE = f"{msg} 本关获得金币 {gained}。"
    return redirect(url_for("index"))


@app.post("/reset")
def reset() -> Any:
    global GAME, CURRENT_LEVEL_INDEX, LAST_MESSAGE
    GAME = Game()
    CURRENT_LEVEL_INDEX = 0
    LAST_MESSAGE = "游戏已重置。"
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
