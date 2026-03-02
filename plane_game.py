#!/usr/bin/env python3
"""小飞机弹弓飞行模拟（Tkinter 可视化版）"""

from __future__ import annotations

from dataclasses import dataclass, field
import argparse
import math
import sys
import tkinter as tk
from tkinter import messagebox
from typing import List

RHO_AIR = 1.225
G = 9.81
DT = 0.04
WORLD_HEIGHT = 35.0


@dataclass
class Plane:
    mass: float = 0.6
    wing_area: float = 0.22
    lift_coeff: float = 1.0
    drag_coeff: float = 0.06
    control_authority: float = 0.16

    def upgrade(self) -> None:
        self.wing_area *= 1.08
        self.lift_coeff *= 1.06
        self.drag_coeff *= 0.95
        self.mass *= 0.98
        self.control_authority *= 1.05


@dataclass
class Slingshot:
    strength: float = 30.0
    efficiency: float = 0.9

    def launch_speed(self, power_ratio: float) -> float:
        p = max(0.1, min(1.0, power_ratio))
        return self.strength * self.efficiency * p

    def upgrade(self) -> None:
        self.strength *= 1.12
        self.efficiency = min(1.0, self.efficiency + 0.03)


@dataclass
class Obstacle:
    x_start: float
    x_end: float
    clearance_height: float

    def collides(self, x: float, y: float) -> bool:
        return self.x_start <= x <= self.x_end and y < self.clearance_height


@dataclass
class Level:
    level_id: int
    target_distance: float
    obstacles: List[Obstacle] = field(default_factory=list)
    coin_interval: float = 40.0
    completion_bonus: int = 80


@dataclass
class FlightState:
    x: float = 0.0
    y: float = 1.2
    vx: float = 0.0
    vy: float = 0.0
    t: float = 0.0


class FlightSimulator:
    def __init__(self, plane: Plane) -> None:
        self.plane = plane

    def step(self, state: FlightState, attack_input: float) -> FlightState:
        speed = max(0.01, min(80.0, math.hypot(state.vx, state.vy)))
        vx_hat = state.vx / speed
        vy_hat = state.vy / speed

        cl = max(0.2, self.plane.lift_coeff + attack_input * self.plane.control_authority)
        lift = 0.5 * RHO_AIR * speed * speed * self.plane.wing_area * cl
        drag = 0.5 * RHO_AIR * speed * speed * self.plane.wing_area * self.plane.drag_coeff

        lift_x = -vy_hat * lift
        lift_y = vx_hat * lift
        drag_x = -vx_hat * drag
        drag_y = -vy_hat * drag

        fx = lift_x + drag_x
        fy = lift_y + drag_y - self.plane.mass * G

        ax = max(-40.0, min(40.0, fx / self.plane.mass))
        ay = max(-45.0, min(45.0, fy / self.plane.mass))

        return FlightState(
            x=state.x + state.vx * DT,
            y=state.y + state.vy * DT,
            vx=state.vx + ax * DT,
            vy=state.vy + ay * DT,
            t=state.t + DT,
        )


class PlaneGameGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("小飞机弹弓闯关模拟")
        self.root.geometry("1000x680")

        self.canvas_w = 980
        self.canvas_h = 520
        self.scale_y = self.canvas_h / WORLD_HEIGHT

        self.plane = Plane()
        self.slingshot = Slingshot()
        self.levels = self._create_levels()

        self.current_level_idx = 0
        self.coins = 0
        self.state = FlightState()
        self.sim = FlightSimulator(self.plane)
        self.running = False
        self.next_coin_mark = 0.0
        self.gained_this_level = 0

        self._build_ui()
        self._load_level(0)
        self._render()
        self.root.lift()
        self.root.focus_force()

    def _create_levels(self) -> List[Level]:
        return [
            Level(1, 220, [Obstacle(90, 110, 6), Obstacle(165, 190, 8)], 40, 80),
            Level(2, 320, [Obstacle(70, 95, 5), Obstacle(175, 210, 10), Obstacle(260, 285, 8)], 45, 110),
            Level(3, 430, [Obstacle(110, 140, 7), Obstacle(210, 245, 11), Obstacle(320, 355, 9)], 50, 150),
        ]

    def _build_ui(self) -> None:
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=8, pady=6)

        self.info_var = tk.StringVar()
        tk.Label(top, textvariable=self.info_var, font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        self.canvas = tk.Canvas(self.root, width=self.canvas_w, height=self.canvas_h, bg="#dff3ff")
        self.canvas.pack(padx=8, pady=4)

        ctrl = tk.Frame(self.root)
        ctrl.pack(fill=tk.X, padx=8, pady=6)

        self.angle_scale = tk.Scale(ctrl, from_=10, to=50, orient=tk.HORIZONTAL, label="发射角度(度)")
        self.angle_scale.set(26)
        self.angle_scale.pack(side=tk.LEFT, padx=6)

        self.power_scale = tk.Scale(ctrl, from_=10, to=100, orient=tk.HORIZONTAL, label="弹弓力度(%)")
        self.power_scale.set(85)
        self.power_scale.pack(side=tk.LEFT, padx=6)

        self.attack_scale = tk.Scale(ctrl, from_=-100, to=100, orient=tk.HORIZONTAL, label="俯仰控制", length=200)
        self.attack_scale.set(0)
        self.attack_scale.pack(side=tk.LEFT, padx=6)

        self.launch_btn = tk.Button(ctrl, text="发射", command=self.launch)
        self.launch_btn.pack(side=tk.LEFT, padx=8)

        tk.Button(ctrl, text="升级飞机(120)", command=self.upgrade_plane).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="升级弹弓(90)", command=self.upgrade_slingshot).pack(side=tk.LEFT, padx=4)

        self.level_hint_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.level_hint_var, fg="#333").pack(anchor="w", padx=10)

    def _load_level(self, idx: int) -> None:
        self.current_level_idx = idx
        self.level = self.levels[idx]
        self.state = FlightState()
        self.running = False
        self.next_coin_mark = self.level.coin_interval
        self.gained_this_level = 0
        self._update_info()

    def _update_info(self) -> None:
        self.info_var.set(
            f"关卡: {self.level.level_id}/{len(self.levels)}  金币: {self.coins}  "
            f"x={self.state.x:.1f}m y={self.state.y:.1f}m vx={self.state.vx:.1f}m/s"
        )
        self.level_hint_var.set(f"目标距离: {self.level.target_distance}m，障碍数量: {len(self.level.obstacles)}")

    def world_to_canvas(self, x: float, y: float) -> tuple[float, float]:
        camera_x = max(0.0, self.state.x - 120)
        return (x - camera_x) * 3.0, self.canvas_h - y * self.scale_y

    def launch(self) -> None:
        if self.running:
            return
        angle_deg = self.angle_scale.get()
        power = self.power_scale.get() / 100
        speed = self.slingshot.launch_speed(power)
        angle = math.radians(angle_deg)

        self.state = FlightState(vx=speed * math.cos(angle), vy=speed * math.sin(angle))
        self.running = True
        self._tick()

    def upgrade_plane(self) -> None:
        if self.coins < 120:
            messagebox.showinfo("提示", "金币不足")
            return
        self.coins -= 120
        self.plane.upgrade()
        self._update_info()

    def upgrade_slingshot(self) -> None:
        if self.coins < 90:
            messagebox.showinfo("提示", "金币不足")
            return
        self.coins -= 90
        self.slingshot.upgrade()
        self._update_info()

    def _tick(self) -> None:
        if not self.running:
            return

        attack_input = self.attack_scale.get() / 100
        self.state = self.sim.step(self.state, attack_input)

        if not all(math.isfinite(v) for v in (self.state.x, self.state.y, self.state.vx, self.state.vy)):
            self._end_level(False, "数值异常，判定失败")
            return

        if self.state.y <= 0:
            self._end_level(False, f"坠地，飞行距离 {self.state.x:.1f}m")
            return

        for ob in self.level.obstacles:
            if ob.collides(self.state.x, self.state.y):
                self._end_level(False, f"撞上障碍物 x={ob.x_start}-{ob.x_end}m")
                return

        while self.state.x >= self.next_coin_mark:
            self.gained_this_level += 10
            self.next_coin_mark += self.level.coin_interval

        if self.state.x >= self.level.target_distance:
            self.gained_this_level += self.level.completion_bonus
            self._end_level(True, f"成功过关！本关金币 +{self.gained_this_level}")
            return

        if self.state.t > 90:
            self._end_level(False, "超时失败")
            return

        self._update_info()
        self._render()
        self.root.after(int(DT * 1000), self._tick)

    def _end_level(self, passed: bool, reason: str) -> None:
        self.running = False
        self.coins += self.gained_this_level
        self._update_info()
        self._render()

        if passed:
            if self.current_level_idx + 1 < len(self.levels):
                messagebox.showinfo("过关", reason)
                self._load_level(self.current_level_idx + 1)
            else:
                messagebox.showinfo("通关", f"{reason}\n恭喜你完成全部关卡！")
                self._load_level(0)
        else:
            messagebox.showwarning("失败", f"{reason}\n本关金币 +{self.gained_this_level}")

    def _render(self) -> None:
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, self.canvas_h - 2, self.canvas_w, self.canvas_h, fill="#3a8d2f", outline="")

        camera_x = max(0.0, self.state.x - 120)
        for i in range(0, self.canvas_w, 80):
            self.canvas.create_line(i, 0, i, self.canvas_h, fill="#cfe8f8")
        for y in range(0, int(WORLD_HEIGHT) + 1, 5):
            _, sy = self.world_to_canvas(camera_x, y)
            self.canvas.create_line(0, sy, self.canvas_w, sy, fill="#e7f4fc")

        for ob in self.level.obstacles:
            x1, y1 = self.world_to_canvas(ob.x_start, 0)
            x2, y2 = self.world_to_canvas(ob.x_end, ob.clearance_height)
            if x2 < 0 or x1 > self.canvas_w:
                continue
            self.canvas.create_rectangle(x1, y2, x2, y1, fill="#8b3d2f", outline="#5c251c")
            self.canvas.create_text((x1 + x2) / 2, y2 - 8, text=f"{ob.clearance_height}m", fill="#5c251c")

        tx, _ = self.world_to_canvas(self.level.target_distance, 0)
        self.canvas.create_line(tx, 0, tx, self.canvas_h, fill="#ff6a00", width=3)
        self.canvas.create_text(tx + 28, 14, text="终点", fill="#ff6a00")

        px, py = self.world_to_canvas(self.state.x, self.state.y)
        angle = math.atan2(self.state.vy, max(0.01, self.state.vx))
        size = 14
        nose = (px + math.cos(angle) * size, py - math.sin(angle) * size)
        left = (px + math.cos(angle + 2.5) * size * 0.8, py - math.sin(angle + 2.5) * size * 0.8)
        right = (px + math.cos(angle - 2.5) * size * 0.8, py - math.sin(angle - 2.5) * size * 0.8)
        self.canvas.create_polygon(nose, left, right, fill="#1f6fff", outline="#0d3d99", width=2)

        sx, sy = self.world_to_canvas(0, 0)
        self.canvas.create_line(sx - 18, sy - 8, sx, sy - 35, fill="#5f3b1f", width=4)
        self.canvas.create_line(sx + 18, sy - 8, sx, sy - 35, fill="#5f3b1f", width=4)
        self.canvas.create_text(80, self.canvas_h - 22, text="弹弓发射点", fill="#5f3b1f")

    def run(self) -> None:
        self.root.mainloop()


def run_demo() -> None:
    plane = Plane()
    sling = Slingshot()
    sim = FlightSimulator(plane)
    state = FlightState()
    speed = sling.launch_speed(0.85)
    angle = math.radians(25)
    state.vx = speed * math.cos(angle)
    state.vy = speed * math.sin(angle)
    print("[demo] 已开始终端模拟（无 GUI）...")
    for i in range(120):
        state = sim.step(state, 0.15)
        if i % 10 == 0:
            print(f"[demo] t={state.t:4.1f}s x={state.x:6.1f}m y={state.y:5.1f}m")
        if state.y <= 0:
            print(f"[demo] 坠地: x={state.x:.1f}m")
            return
    print(f"[demo] 结束: x={state.x:.1f}m y={state.y:.1f}m")


def main() -> None:
    parser = argparse.ArgumentParser(description="小飞机弹弓闯关模拟")
    parser.add_argument("--demo", action="store_true", help="仅终端演示，不启动图形界面")
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    print("正在启动可视化窗口...（若无窗口，请检查是否允许 Python 打开图形界面）")
    try:
        app = PlaneGameGUI()
        app.run()
    except tk.TclError as exc:
        print("GUI 启动失败。请检查 macOS 图形权限或 Tk 支持。", file=sys.stderr)
        print(f"详细错误: {exc}", file=sys.stderr)
        print("你也可以先运行: python3 plane_game.py --demo", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
