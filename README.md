# 小飞机弹弓闯关模拟

一个纯 Python 命令行小游戏，包含：

- 简化空气动力学（升力、阻力、重力）
- 弹弓发射初速度
- 按飞行距离发放金币
- 商店升级（飞机 / 弹弓）
- 多关卡和障碍物

## 运行

```bash
python3 plane_game.py
```

## 演示模式（自动参数，无需输入）

```bash
python3 plane_game.py --demo
```

## Web 界面（可操作）

```bash
pip install flask
python3 web_app.py
```

浏览器打开 `http://localhost:8000`，即可：

- 在商店点击按钮升级飞机 / 弹弓
- 输入发射角度和力度并发射当前关卡
- 查看金币、关卡、参数和结果提示
- 一键重置游戏
