diff --git a/main.py b/main.py
index 8b00a34e80eaaf8394cb0afa47cd8faeae2d308c..52fdf9d6c6c84411672830e79cf19579b2bdcd99 100644
--- a/main.py
+++ b/main.py
@@ -1,130 +1,410 @@
-import os
-import time
-from datetime import datetime, timezone
-from typing import Dict, List, Optional
-
-import requests
-
-BASE_URL = "https://api.binance.com"
-EXCHANGE_INFO_URL = f"{BASE_URL}/api/v3/exchangeInfo"
-KLINES_URL = f"{BASE_URL}/api/v3/klines"
-REQUEST_TIMEOUT = 15
-RETRY_TIMES = 3
-RETRY_SLEEP_SECONDS = 1
-KLINE_INTERVAL = "1d"
-
-
-def request_json(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
-    """带基础重试能力的 GET 请求。"""
-    for attempt in range(1, RETRY_TIMES + 1):
-        try:
-            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
-            response.raise_for_status()
-            return response.json()
-        except requests.RequestException as exc:
-            print(f"[警告] 请求失败 {attempt}/{RETRY_TIMES}: {url} params={params}, error={exc}")
-            if attempt < RETRY_TIMES:
-                time.sleep(RETRY_SLEEP_SECONDS)
-    return None
-
-
-def fetch_usdt_symbols() -> List[Dict]:
-    """获取所有 USDT 交易对。"""
-    data = request_json(EXCHANGE_INFO_URL)
-    if not data or "symbols" not in data:
-        return []
-
-    usdt_symbols = []
-    for item in data["symbols"]:
-        # 仅保留状态正常、且以 USDT 结尾的现货交易对
-        if item.get("quoteAsset") == "USDT" and item.get("status") == "TRADING":
-            usdt_symbols.append(item)
-    return usdt_symbols
-
-
-def fetch_listing_datetime(symbol: str) -> Optional[datetime]:
-    """通过最早 K 线 open_time 推断交易对实际上线时间。"""
-    params = {
-        "symbol": symbol,
-        "interval": KLINE_INTERVAL,
-        "startTime": 0,
-        "limit": 1,
-    }
-    data = request_json(KLINES_URL, params=params)
-
-    # 返回数据格式示例: [[open_time, open, high, low, close, volume, ...]]
-    if not isinstance(data, list) or not data or not isinstance(data[0], list):
-        return None
-
-    open_time_ms = data[0][0]
-    if not isinstance(open_time_ms, int):
-        return None
-
-    return datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)
-
-
-def format_markdown(rows: List[Dict]) -> str:
-    """把筛选结果整理为 Markdown 表格。"""
-    if not rows:
-        return "## Binance 上线时间筛选结果\n\n最近 30~365 天内暂无符合条件的 USDT 交易对。"
-
-    lines = [
-        "## Binance 上线时间筛选结果",
-        "",
-        "| 币种名称 | 上线日期(UTC) | 存续天数 |",
-        "|---|---|---|",
-    ]
-
-    for row in rows:
-        lines.append(f"| {row['symbol']} | {row['listing_date']} | {row['age_days']} |")
-
-    return "\n".join(lines)
+import math
+import random
+import tkinter as tk
+from dataclasses import dataclass, field
+from typing import List
 
+WIDTH = 960
+HEIGHT = 640
+FPS = 60
 
-def main() -> None:
-    now = datetime.now(timezone.utc)
-    min_days = 30
-    max_days = 365
-
-    symbols = fetch_usdt_symbols()
-    if not symbols:
-        markdown = "## Binance 上线时间筛选结果\n\n获取交易对失败或无可用数据。"
-        print(markdown)
-        return
-
-    rows = []
-    for item in symbols:
-        symbol = item.get("symbol")
-        if not symbol:
-            continue
-
-        listing_dt = fetch_listing_datetime(symbol)
-        # 为避免触发接口限频，增加轻量延迟
-        time.sleep(0.05)
-
-        if not listing_dt:
-            continue
-
-        age_days = (now - listing_dt).days
-        if min_days <= age_days <= max_days:
-            rows.append(
-                {
-                    "symbol": symbol,
-                    "listing_date": listing_dt.strftime("%Y-%m-%d"),
-                    "age_days": age_days,
-                }
+PLAYER_SPEED = 4.2
+PLAYER_RADIUS = 14
+
+BULLET_SPEED = 10.0
+BULLET_RADIUS = 4
+BASE_FIRE_COOLDOWN = 0.35
+
+ENEMY_BASE_SPEED = 1.2
+ENEMY_RADIUS = 12
+
+XP_ORB_RADIUS = 5
+
+
+@dataclass
+class Vec2:
+    x: float
+    y: float
+
+    def copy(self) -> "Vec2":
+        return Vec2(self.x, self.y)
+
+    def distance_to(self, other: "Vec2") -> float:
+        return math.hypot(self.x - other.x, self.y - other.y)
+
+    def normalized_towards(self, target: "Vec2") -> "Vec2":
+        dx = target.x - self.x
+        dy = target.y - self.y
+        dist = math.hypot(dx, dy)
+        if dist == 0:
+            return Vec2(0.0, 0.0)
+        return Vec2(dx / dist, dy / dist)
+
+
+@dataclass
+class Player:
+    pos: Vec2
+    hp: int = 100
+    max_hp: int = 100
+    level: int = 1
+    xp: int = 0
+    xp_to_next: int = 20
+    fire_cooldown: float = BASE_FIRE_COOLDOWN
+    fire_timer: float = 0.0
+    damage: int = 10
+    move_speed: float = PLAYER_SPEED
+    pickup_radius: float = 40
+
+
+@dataclass
+class Enemy:
+    pos: Vec2
+    hp: int
+    speed: float
+    damage: int
+    size: float = ENEMY_RADIUS
+
+
+@dataclass
+class Bullet:
+    pos: Vec2
+    vel: Vec2
+    damage: int
+    radius: float = BULLET_RADIUS
+
+
+@dataclass
+class XpOrb:
+    pos: Vec2
+    value: int = 1
+    radius: float = XP_ORB_RADIUS
+
+
+@dataclass
+class GameState:
+    player: Player = field(default_factory=lambda: Player(pos=Vec2(WIDTH / 2, HEIGHT / 2)))
+    enemies: List[Enemy] = field(default_factory=list)
+    bullets: List[Bullet] = field(default_factory=list)
+    xp_orbs: List[XpOrb] = field(default_factory=list)
+    score: int = 0
+    time_alive: float = 0.0
+    enemy_spawn_timer: float = 0.0
+    enemy_spawn_cooldown: float = 1.0
+    game_over: bool = False
+
+
+class SurvivorGame:
+    def __init__(self, root: tk.Tk) -> None:
+        self.root = root
+        self.root.title("Mini Survivor")
+
+        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#111111", highlightthickness=0)
+        self.canvas.pack()
+
+        self.state = GameState()
+        self.keys_pressed = set()
+
+        self.root.bind("<KeyPress>", self.on_key_press)
+        self.root.bind("<KeyRelease>", self.on_key_release)
+        self.root.bind("<space>", self.on_space)
+
+        self.last_timestamp = None
+        self.loop()
+
+    def on_key_press(self, event: tk.Event) -> None:
+        self.keys_pressed.add(event.keysym.lower())
+
+    def on_key_release(self, event: tk.Event) -> None:
+        self.keys_pressed.discard(event.keysym.lower())
+
+    def on_space(self, _event: tk.Event) -> None:
+        if self.state.game_over:
+            self.state = GameState()
+
+    def loop(self) -> None:
+        now = self.root.tk.call("clock", "milliseconds")
+        if self.last_timestamp is None:
+            self.last_timestamp = now
+
+        dt = max(0.0, (now - self.last_timestamp) / 1000.0)
+        self.last_timestamp = now
+
+        self.update(dt)
+        self.render()
+
+        self.root.after(int(1000 / FPS), self.loop)
+
+    def update(self, dt: float) -> None:
+        if self.state.game_over:
+            return
+
+        st = self.state
+        st.time_alive += dt
+        self.move_player(dt)
+
+        st.enemy_spawn_timer -= dt
+        if st.enemy_spawn_timer <= 0:
+            self.spawn_enemies()
+            st.enemy_spawn_timer = max(0.2, st.enemy_spawn_cooldown - st.time_alive * 0.008)
+
+        st.player.fire_timer -= dt
+        if st.player.fire_timer <= 0:
+            self.auto_shoot()
+            st.player.fire_timer = max(0.08, st.player.fire_cooldown)
+
+        self.update_bullets(dt)
+        self.update_enemies(dt)
+        self.collect_xp_orbs()
+
+        if st.player.hp <= 0:
+            st.game_over = True
+
+    def move_player(self, dt: float) -> None:
+        st = self.state
+        dx = 0.0
+        dy = 0.0
+
+        if "w" in self.keys_pressed or "up" in self.keys_pressed:
+            dy -= 1
+        if "s" in self.keys_pressed or "down" in self.keys_pressed:
+            dy += 1
+        if "a" in self.keys_pressed or "left" in self.keys_pressed:
+            dx -= 1
+        if "d" in self.keys_pressed or "right" in self.keys_pressed:
+            dx += 1
+
+        length = math.hypot(dx, dy)
+        if length > 0:
+            dx /= length
+            dy /= length
+
+        st.player.pos.x += dx * st.player.move_speed * 60 * dt
+        st.player.pos.y += dy * st.player.move_speed * 60 * dt
+
+        st.player.pos.x = min(max(PLAYER_RADIUS, st.player.pos.x), WIDTH - PLAYER_RADIUS)
+        st.player.pos.y = min(max(PLAYER_RADIUS, st.player.pos.y), HEIGHT - PLAYER_RADIUS)
+
+    def spawn_enemies(self) -> None:
+        st = self.state
+        spawn_count = 1 + int(st.time_alive // 20)
+        for _ in range(min(5, spawn_count)):
+            side = random.choice(["top", "bottom", "left", "right"])
+            if side == "top":
+                pos = Vec2(random.uniform(0, WIDTH), -20)
+            elif side == "bottom":
+                pos = Vec2(random.uniform(0, WIDTH), HEIGHT + 20)
+            elif side == "left":
+                pos = Vec2(-20, random.uniform(0, HEIGHT))
+            else:
+                pos = Vec2(WIDTH + 20, random.uniform(0, HEIGHT))
+
+            hp = 12 + int(st.time_alive * 0.7)
+            speed = ENEMY_BASE_SPEED + min(2.5, st.time_alive * 0.015)
+            damage = 8 + int(st.time_alive * 0.04)
+            st.enemies.append(Enemy(pos=pos, hp=hp, speed=speed, damage=damage))
+
+    def auto_shoot(self) -> None:
+        st = self.state
+        if not st.enemies:
+            return
+
+        player_pos = st.player.pos
+        target = min(st.enemies, key=lambda e: e.pos.distance_to(player_pos))
+        direction = player_pos.normalized_towards(target.pos)
+        vel = Vec2(direction.x * BULLET_SPEED, direction.y * BULLET_SPEED)
+        st.bullets.append(Bullet(pos=player_pos.copy(), vel=vel, damage=st.player.damage))
+
+    def update_bullets(self, dt: float) -> None:
+        st = self.state
+        alive_bullets: List[Bullet] = []
+
+        for bullet in st.bullets:
+            bullet.pos.x += bullet.vel.x * 60 * dt
+            bullet.pos.y += bullet.vel.y * 60 * dt
+
+            hit_enemy = None
+            for enemy in st.enemies:
+                if bullet.pos.distance_to(enemy.pos) <= bullet.radius + enemy.size:
+                    enemy.hp -= bullet.damage
+                    hit_enemy = enemy
+                    break
+
+            if hit_enemy is not None:
+                if hit_enemy.hp <= 0:
+                    st.enemies.remove(hit_enemy)
+                    st.score += 1
+                    st.xp_orbs.append(XpOrb(pos=hit_enemy.pos.copy(), value=1 + int(st.time_alive // 45)))
+                continue
+
+            if 0 <= bullet.pos.x <= WIDTH and 0 <= bullet.pos.y <= HEIGHT:
+                alive_bullets.append(bullet)
+
+        st.bullets = alive_bullets
+
+    def update_enemies(self, dt: float) -> None:
+        st = self.state
+        player = st.player
+
+        for enemy in list(st.enemies):
+            direction = enemy.pos.normalized_towards(player.pos)
+            enemy.pos.x += direction.x * enemy.speed * 60 * dt
+            enemy.pos.y += direction.y * enemy.speed * 60 * dt
+
+            if enemy.pos.distance_to(player.pos) <= enemy.size + PLAYER_RADIUS:
+                player.hp -= enemy.damage
+                st.enemies.remove(enemy)
+
+    def collect_xp_orbs(self) -> None:
+        st = self.state
+        player = st.player
+
+        remained_orbs: List[XpOrb] = []
+        for orb in st.xp_orbs:
+            dist = orb.pos.distance_to(player.pos)
+            if dist <= player.pickup_radius:
+                self.gain_xp(orb.value)
+            else:
+                direction = orb.pos.normalized_towards(player.pos)
+                # 吸附效果
+                pull_speed = 2.0 + max(0.0, (player.pickup_radius - dist) / player.pickup_radius * 6)
+                orb.pos.x += direction.x * pull_speed
+                orb.pos.y += direction.y * pull_speed
+                remained_orbs.append(orb)
+
+        st.xp_orbs = remained_orbs
+
+    def gain_xp(self, amount: int) -> None:
+        st = self.state
+        st.player.xp += amount
+
+        while st.player.xp >= st.player.xp_to_next:
+            st.player.xp -= st.player.xp_to_next
+            st.player.level += 1
+            st.player.xp_to_next = int(st.player.xp_to_next * 1.35)
+            self.apply_levelup_bonus()
+
+    def apply_levelup_bonus(self) -> None:
+        player = self.state.player
+        choice = random.choice(["damage", "speed", "faster_fire", "pickup", "heal"])
+        if choice == "damage":
+            player.damage += 4
+        elif choice == "speed":
+            player.move_speed += 0.35
+        elif choice == "faster_fire":
+            player.fire_cooldown = max(0.1, player.fire_cooldown * 0.9)
+        elif choice == "pickup":
+            player.pickup_radius += 8
+        else:
+            player.hp = min(player.max_hp, player.hp + 18)
+
+    def render(self) -> None:
+        st = self.state
+        self.canvas.delete("all")
+
+        # 背景网格
+        grid_size = 40
+        for x in range(0, WIDTH, grid_size):
+            self.canvas.create_line(x, 0, x, HEIGHT, fill="#1c1c1c")
+        for y in range(0, HEIGHT, grid_size):
+            self.canvas.create_line(0, y, WIDTH, y, fill="#1c1c1c")
+
+        # 经验球
+        for orb in st.xp_orbs:
+            self.canvas.create_oval(
+                orb.pos.x - orb.radius,
+                orb.pos.y - orb.radius,
+                orb.pos.x + orb.radius,
+                orb.pos.y + orb.radius,
+                fill="#47b3ff",
+                outline="",
             )
 
-    rows.sort(key=lambda x: x["age_days"])
-    markdown = format_markdown(rows)
-    print(markdown)
+        # 子弹
+        for bullet in st.bullets:
+            self.canvas.create_oval(
+                bullet.pos.x - bullet.radius,
+                bullet.pos.y - bullet.radius,
+                bullet.pos.x + bullet.radius,
+                bullet.pos.y + bullet.radius,
+                fill="#ffd166",
+                outline="",
+            )
+
+        # 敌人
+        for enemy in st.enemies:
+            self.canvas.create_oval(
+                enemy.pos.x - enemy.size,
+                enemy.pos.y - enemy.size,
+                enemy.pos.x + enemy.size,
+                enemy.pos.y + enemy.size,
+                fill="#f94144",
+                outline="",
+            )
+
+        # 玩家
+        p = st.player.pos
+        self.canvas.create_oval(
+            p.x - PLAYER_RADIUS,
+            p.y - PLAYER_RADIUS,
+            p.x + PLAYER_RADIUS,
+            p.y + PLAYER_RADIUS,
+            fill="#90be6d",
+            outline="",
+        )
+
+        # HUD
+        hp_ratio = max(0.0, st.player.hp / st.player.max_hp)
+        self.canvas.create_rectangle(20, 20, 240, 40, fill="#333333", outline="")
+        self.canvas.create_rectangle(20, 20, 20 + 220 * hp_ratio, 40, fill="#2dc653", outline="")
+        self.canvas.create_text(130, 30, text=f"HP: {max(0, st.player.hp)}/{st.player.max_hp}", fill="white", font=("Arial", 11))
 
-    # 兼容直接运行时写入 GitHub Step Summary
-    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
-    if summary_path:
-        with open(summary_path, "a", encoding="utf-8") as f:
-            f.write(markdown + "\n")
+        xp_ratio = st.player.xp / st.player.xp_to_next
+        self.canvas.create_rectangle(20, 48, 240, 62, fill="#333333", outline="")
+        self.canvas.create_rectangle(20, 48, 20 + 220 * xp_ratio, 62, fill="#4cc9f0", outline="")
+
+        self.canvas.create_text(20, 85, anchor="w", fill="white", font=("Arial", 12), text=f"Level: {st.player.level}")
+        self.canvas.create_text(20, 106, anchor="w", fill="white", font=("Arial", 12), text=f"击败: {st.score}")
+        self.canvas.create_text(20, 127, anchor="w", fill="white", font=("Arial", 12), text=f"存活: {int(st.time_alive)} 秒")
+
+        self.canvas.create_text(
+            WIDTH - 20,
+            26,
+            anchor="e",
+            fill="#cccccc",
+            font=("Arial", 11),
+            text="WASD / 方向键移动，空格重开",
+        )
+
+        if st.game_over:
+            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="black", stipple="gray50", outline="")
+            self.canvas.create_text(
+                WIDTH / 2,
+                HEIGHT / 2 - 30,
+                text="你倒下了",
+                fill="white",
+                font=("Arial", 40, "bold"),
+            )
+            self.canvas.create_text(
+                WIDTH / 2,
+                HEIGHT / 2 + 18,
+                text=f"最终击败: {st.score}    存活: {int(st.time_alive)} 秒",
+                fill="#dddddd",
+                font=("Arial", 16),
+            )
+            self.canvas.create_text(
+                WIDTH / 2,
+                HEIGHT / 2 + 52,
+                text="按空格键重新开始",
+                fill="#9ad1d4",
+                font=("Arial", 14),
+            )
+
+
+def main() -> None:
+    root = tk.Tk()
+    SurvivorGame(root)
+    root.mainloop()
 
 
 if __name__ == "__main__":
     main()
