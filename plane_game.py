#!/usr/bin/env python3
"""小飞机弹弓飞行模拟（命令行版）

功能：
1) 基于简化空气动力学（升力、阻力、重力）更新飞行状态。
2) 使用弹弓提供初始速度和发射角度。
3) 通关模式：每飞行一定距离给金币。
4) 金币可升级飞机和弹弓。
5) 多关卡与障碍物。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import argparse
import math
from typing import List


RHO_AIR = 1.225  # kg/m^3
G = 9.81  # m/s^2
DT = 0.1  # s


@dataclass
class Plane:
    mass: float = 0.6
    wing_area: float = 0.22
    lift_coeff: float = 1.15
    drag_coeff: float = 0.05
    control_authority: float = 0.12

    def upgrade(self) -> None:
        self.wing_area *= 1.08
        self.lift_coeff *= 1.06
        self.drag_coeff *= 0.95
        self.mass *= 0.98
        self.control_authority *= 1.06


@dataclass
class Slingshot:
    strength: float = 34.0
    efficiency: float = 0.9

    def launch_speed(self, power_ratio: float) -> float:
        power_ratio = max(0.1, min(1.0, power_ratio))
        return self.strength * self.efficiency * power_ratio

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
    coin_interval: float = 50.0
    completion_bonus: int = 60


@dataclass
class FlightState:
    x: float = 0.0
    y: float = 1.2
    vx: float = 0.0
    vy: float = 0.0
    t: float = 0.0


class FlightSimulator:
    def __init__(self, plane: Plane, level: Level):
        self.plane = plane
        self.level = level

    def step(self, state: FlightState, attack_input: float) -> FlightState:
        speed = max(0.01, min(80.0, math.hypot(state.vx, state.vy)))
        vx_hat = state.vx / speed
        vy_hat = state.vy / speed

        cl = max(0.2, self.plane.lift_coeff + attack_input * self.plane.control_authority)
        # 简化空气动力学：升力近似主要作用于竖直方向，阻力沿速度反向
        lift_y = 0.5 * RHO_AIR * speed * speed * self.plane.wing_area * cl
        drag = 0.5 * RHO_AIR * speed * speed * self.plane.wing_area * self.plane.drag_coeff

        drag_x = -vx_hat * drag
        drag_y = -vy_hat * drag

        fx = drag_x
        fy = lift_y + drag_y - self.plane.mass * G

        ax = max(-30.0, min(30.0, fx / self.plane.mass))
        ay = max(-35.0, min(35.0, fy / self.plane.mass))

        nxt = FlightState(
            x=state.x + state.vx * DT,
            y=state.y + state.vy * DT,
            vx=state.vx + ax * DT,
            vy=state.vy + ay * DT,
            t=state.t + DT,
        )
        return nxt


class Game:
    def __init__(self) -> None:
        self.plane = Plane()
        self.slingshot = Slingshot()
        self.coins = 0
        self.levels = self._create_levels()

    def _create_levels(self) -> List[Level]:
        return [
            Level(1, 220, [Obstacle(90, 110, 6), Obstacle(170, 185, 8)], 40, 80),
            Level(2, 320, [Obstacle(70, 95, 5), Obstacle(190, 220, 10), Obstacle(260, 280, 7)], 45, 110),
            Level(3, 430, [Obstacle(120, 150, 8), Obstacle(210, 235, 11), Obstacle(315, 350, 9)], 50, 150),
        ]

    def run(self, demo: bool = False) -> None:
        print("=== 小飞机弹弓闯关模拟 ===")
        for level in self.levels:
            print(f"\n--- 进入第 {level.level_id} 关，目标距离 {level.target_distance} m ---")
            print(f"当前金币: {self.coins}")
            self._shop_phase(demo)
            passed, gained = self._play_level(level, demo)
            self.coins += gained
            print(f"本关获得金币: {gained}，总金币: {self.coins}")
            if not passed:
                print("飞行失败，游戏结束。")
                return

        print(f"\n恭喜通关！最终金币: {self.coins}")

    def _shop_phase(self, demo: bool) -> None:
        while True:
            print("升级商店：1) 升级飞机(120) 2) 升级弹弓(90) 0) 出发")
            if demo:
                choice = "0"
            else:
                choice = input("选择: ").strip()

            if choice == "1" and self.coins >= 120:
                self.coins -= 120
                self.plane.upgrade()
                print("飞机升级完成。")
            elif choice == "2" and self.coins >= 90:
                self.coins -= 90
                self.slingshot.upgrade()
                print("弹弓升级完成。")
            elif choice == "0":
                break
            else:
                print("无法购买或输入无效。")

    def _play_level(self, level: Level, demo: bool) -> tuple[bool, int]:
        if demo:
            angle_deg = 22 + level.level_id * 2
            power = 0.88
        else:
            angle_deg = float(input("输入发射角度(建议15~35度): "))
            power = float(input("输入弹射力度(0.1~1.0): "))

        speed0 = self.slingshot.launch_speed(power)
        angle = math.radians(angle_deg)
        state = FlightState(vx=speed0 * math.cos(angle), vy=speed0 * math.sin(angle))

        sim = FlightSimulator(self.plane, level)
        next_coin_mark = level.coin_interval
        gained = 0

        while True:
            # 简单控制策略：目标是保持在障碍净空上方+安全裕度
            target_height = 7.0
            for ob in level.obstacles:
                if state.x + 12 >= ob.x_start and state.x <= ob.x_end:
                    target_height = max(target_height, ob.clearance_height + 2.5)

            attack_input = max(-1.0, min(1.0, (target_height - state.y) * 0.15))
            state = sim.step(state, attack_input)

            if not all(math.isfinite(v) for v in (state.x, state.y, state.vx, state.vy)):
                print("数值发散，判定失败。")
                return False, gained

            if state.y <= 0:
                print(f"坠地于 x={state.x:.1f}m")
                return False, gained

            for ob in level.obstacles:
                if ob.collides(state.x, state.y):
                    print(f"撞上障碍物（x={ob.x_start}-{ob.x_end}m）")
                    return False, gained

            if state.x >= next_coin_mark:
                crossed = int((state.x - next_coin_mark) // level.coin_interval) + 1
                crossed = min(crossed, 1000)
                gained += crossed * 10
                next_coin_mark += crossed * level.coin_interval

            if state.x >= level.target_distance:
                gained += level.completion_bonus
                print(
                    f"通过第 {level.level_id} 关！用时 {state.t:.1f}s, 终点高度 {state.y:.1f}m"
                )
                return True, gained

            if state.t > 35:
                print("超时，判定失败。")
                return False, gained



def main() -> None:
    parser = argparse.ArgumentParser(description="小飞机弹弓闯关模拟")
    parser.add_argument("--demo", action="store_true", help="演示模式（无需交互）")
    args = parser.parse_args()

    game = Game()
    game.run(demo=args.demo)


if __name__ == "__main__":
    main()
