# -*- coding: utf-8 -*-
"""陈燕丽的异世界生活 — 单文件方块像素平台游戏。

运行：Python 3.8+，保存本文件后双击，或在 IDLE 中按 F5。
只使用 Python 标准库，不需要 pygame、图片、音频或网络。
Linux 若没有 Tkinter，请通过系统包管理器安装 python3-tk。

A/D 或 ←/→：移动；Space/W/↑：跳跃（支持二段跳）；Shift：加速；
J：魔法；B：切换建造；建造时左键放方块、右键拆自建方块；
P：暂停；R：重开本关；Esc：返回首页。到达发光传送门即可过关。
"""

import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tkinter as tk
except ImportError:
    raise SystemExit("此 Python 缺少 Tkinter。Windows/macOS 请安装完整版 Python；"
                     "Linux 请安装 python3-tk。")


TITLE = "陈燕丽的异世界生活"
HERO = "陈燕丽"
W, H, TILE = 1000, 640, 40
GRAVITY = 1680.0
SOLIDS = {"G", "D", "S", "B", "Q", "U", "X"}
SAVE_PATH = Path.home() / ".chen_yanli_adventure.json"


def overlap(a, b):
    return (a.x < b.x + b.w and a.x + a.w > b.x
            and a.y < b.y + b.h and a.y + a.h > b.y)


@dataclass
class Body:
    x: float
    y: float
    w: float
    h: float
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class Player(Body):
    hp: int = 5
    facing: int = 1
    grounded: bool = False
    jumps: int = 2
    invulnerable: float = 0.0
    star: float = 0.0
    cooldown: float = 0.0
    jump_buffer: float = 0.0
    coyote: float = 0.0


@dataclass
class Enemy(Body):
    kind: str = "slime"
    hp: int = 1
    dead: bool = False
    phase: float = 0.0
    base_y: float = 0.0
    flash: float = 0.0
    left: float = 0.0
    right: float = 0.0


@dataclass
class Pickup(Body):
    kind: str = "coin"
    collected: bool = False
    phase: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: str
    life: float
    size: int = 4


@dataclass
class Level:
    index: int
    name: str
    width: int
    tiles: dict = field(default_factory=dict)
    pickups: list = field(default_factory=list)
    enemies: list = field(default_factory=list)
    hazards: list = field(default_factory=list)
    built: set = field(default_factory=set)
    checkpoint_x: int = 0
    portal_x: int = 0
    gaps: list = field(default_factory=list)


def make_level(index):
    names = ["01  风铃草原", "02  暮色矿谷", "03  星光城堡"]
    widths = [112, 136, 156]
    gap_lists = [
        [(24, 27), (49, 52), (77, 81)],
        [(26, 30), (53, 57), (83, 87), (111, 115)],
        [(28, 32), (58, 62), (92, 96), (121, 125)],
    ]
    rng = random.Random(900 + index)
    width = widths[index]
    level = Level(index, names[index], width)
    level.gaps = gap_lists[index]
    level.checkpoint_x = [42, 69, 78][index] * TILE
    level.portal_x = (width - 5) * TILE
    ground = "G" if index == 0 else "S"

    for x in range(width):
        if any(a <= x < b for a, b in level.gaps):
            continue
        for y in range(14, 17):
            level.tiles[x, y] = ground if y == 14 else "D"

    # 地图由固定结构组成，便于确认每一处跳跃都可以完成。
    platform_specs = [
        [(9, 15, 11), (17, 21, 9), (29, 34, 11), (37, 41, 10),
         (54, 59, 11), (63, 68, 9), (71, 74, 11), (84, 90, 10),
         (95, 100, 11)],
        [(8, 13, 11), (17, 22, 9), (32, 38, 11), (43, 48, 10),
         (59, 64, 11), (72, 78, 10), (89, 95, 11), (99, 105, 9),
         (117, 122, 11)],
        [(9, 14, 11), (18, 24, 9), (34, 40, 11), (46, 51, 10),
         (64, 70, 11), (74, 80, 9), (83, 89, 11), (98, 104, 10),
         (108, 114, 9), (127, 133, 11)],
    ]
    for start, end, y in platform_specs[index]:
        for x in range(start, end):
            level.tiles[x, y] = "B"
            if x % 2 == 0:
                level.pickups.append(Pickup(x*TILE+11, y*TILE-36,
                                            18, 24, phase=rng.random()*6))
        level.tiles[(start+end)//2, y] = "Q"

    # 连续的金币既是奖励，也是路线提示。
    for x in range(6, width-7, 3):
        if not any(a <= x < b for a, b in level.gaps):
            level.pickups.append(Pickup(x*TILE+11, 504, 18, 24,
                                        phase=rng.random()*6))
    for a, b in level.gaps:
        for x in range(a, b):
            level.pickups.append(Pickup(x*TILE+11, 420, 18, 24,
                                        phase=rng.random()*6))

    enemy_columns = [
        [18, 35, 46, 61, 71, 92, 101],
        [16, 40, 49, 65, 78, 98, 106, 124],
        [16, 43, 52, 71, 87, 106, 117, 135],
    ][index]
    for n, col in enumerate(enemy_columns):
        kind = "crab" if index >= 1 and n % 3 == 1 else "slime"
        level.enemies.append(Enemy(col*TILE, 530, 32, 30,
                                    vx=(-1 if n % 2 else 1)*(65+index*12),
                                    kind=kind, hp=2 if kind=="crab" else 1))
    if index >= 1:
        for col in [22, 47, 81, 108]:
            level.enemies.append(Enemy(col*TILE, 340, 36, 28, vx=85,
                                        kind="bat", base_y=340,
                                        phase=rng.random()*6,
                                        left=(col-3)*TILE, right=(col+3)*TILE))
    if index == 2:
        level.enemies.append(Enemy((width-12)*TILE, 502, 64, 58,
                                    vx=-85, kind="guardian", hp=6))
    if index > 0:
        for col in ([44, 75, 101] if index == 1 else [49, 85, 111, 136]):
            level.hazards.append(Body(col*TILE+3, 542, 74, 18))

    level.pickups.append(Pickup(level.checkpoint_x-95, 505, 24, 24,
                                kind="heart"))
    level.pickups.append(Pickup((width-17)*TILE, 450, 26, 26,
                                kind="star"))
    return level


class GameModel:
    """物理和游戏规则独立于界面，方便验证。"""
    def __init__(self):
        self.rng = random.Random(77)
        self.state = "menu"
        self.time = 0.0
        self.score = 0
        self.coins = 0
        self.materials = 20
        self.level_index = 0
        self.level = make_level(0)
        self.player = Player(80, 514, 28, 46)
        self.particles = []
        self.shots = []
        self.camera = 0.0
        self.checkpoint = False
        self.build_mode = False
        self.message = ""
        self.message_time = 0.0
        self.entry_score = 0
        self.entry_coins = 0
        self.entry_materials = 20
        self.entry_hp = 5

    def start(self):
        self.score = self.coins = 0
        self.materials = 20
        self.load_level(0, 5)

    def load_level(self, index, hp):
        self.level_index = index
        self.level = make_level(index)
        self.player = Player(80, 514, 28, 46, hp=hp)
        self.particles = []
        self.shots = []
        self.camera = 0.0
        self.checkpoint = False
        self.build_mode = False
        self.state = "play"
        self.entry_score, self.entry_coins = self.score, self.coins
        self.entry_materials, self.entry_hp = self.materials, hp
        self.notify("陈燕丽，出发！到达右侧传送门即可过关。", 4)

    def restart(self):
        self.score, self.coins = self.entry_score, self.entry_coins
        self.materials = self.entry_materials
        self.load_level(self.level_index, self.entry_hp)

    def advance(self):
        if self.level_index == 2:
            self.state = "win"
        else:
            self.load_level(self.level_index+1, min(5, self.player.hp+1))

    def notify(self, text, seconds=2.5):
        self.message, self.message_time = text, seconds

    def burst(self, x, y, color, amount=12):
        for _ in range(amount):
            self.particles.append(Particle(x, y, self.rng.uniform(-160,160),
                                          self.rng.uniform(-230,30), color,
                                          self.rng.uniform(.3,.75)))

    def solid_at(self, x, y):
        return self.level.tiles.get((int(x//TILE), int(y//TILE))) in SOLIDS

    def nearby_tiles(self, body):
        x0, x1 = int(body.x//TILE)-1, int((body.x+body.w)//TILE)+1
        y0, y1 = int(body.y//TILE)-1, int((body.y+body.h)//TILE)+1
        for ty in range(y0, y1+1):
            for tx in range(x0, x1+1):
                kind = self.level.tiles.get((tx,ty))
                if kind in SOLIDS:
                    yield tx, ty, kind, Body(tx*TILE,ty*TILE,TILE,TILE)

    def move(self, body, dt, is_player=False):
        grounded = False
        body.x += body.vx * dt
        for tx, ty, kind, block in self.nearby_tiles(body):
            if overlap(body, block):
                if body.vx > 0:
                    body.x = block.x-body.w
                elif body.vx < 0:
                    body.x = block.x+block.w
                if isinstance(body, Enemy):
                    body.vx = -body.vx
                else:
                    body.vx = 0
        body.x = max(0, min(body.x, self.level.width*TILE-body.w))
        body.y += body.vy * dt
        for tx, ty, kind, block in self.nearby_tiles(body):
            if overlap(body, block):
                if body.vy > 0:
                    body.y = block.y-body.h
                    grounded = True
                elif body.vy < 0:
                    body.y = block.y+block.h
                    if is_player and kind == "Q":
                        self.hit_block(tx,ty)
                body.vy = 0
        return grounded

    def hit_block(self, tx, ty):
        self.level.tiles[tx,ty] = "U"
        self.burst(tx*TILE+20,ty*TILE, "#ffe784")
        if (tx + self.level_index) % 4 == 0:
            self.player.hp = min(5,self.player.hp+1)
            self.notify("隐藏奖励：恢复一颗爱心！")
        elif (tx + self.level_index) % 7 == 0:
            self.player.star = 8
            self.notify("星光护盾：8 秒内碰到怪物也不会受伤！")
        else:
            self.coins += 3
            self.score += 150
            self.materials += 2
            self.notify("宝箱奖励：金币 +3，方块 +2")

    def damage(self, falling=False, source_x=None):
        p = self.player
        if not falling and (p.invulnerable > 0 or p.star > 0):
            return
        p.hp -= 1
        self.burst(p.x+p.w/2,p.y+p.h/2,"#ff8fa8",16)
        if p.hp <= 0:
            self.state = "gameover"
            return
        p.invulnerable = 1.7
        if falling:
            p.x = self.level.checkpoint_x if self.checkpoint else 80
            p.y = 514
            p.vx = p.vy = 0
            p.jumps = 2
            p.jump_buffer = 0
            self.camera = max(0, min(p.x-300, self.level.width*TILE-W))
            self.notify("别怕，站起来继续冒险！")
        else:
            p.vx = -240 if source_x is not None and source_x > p.x else 240
            p.vy = -330
            self.notify("受伤了！短暂无敌期间可以躲开怪物。",1.6)

    def kill_or_hit(self, enemy, power=1):
        enemy.hp -= power
        enemy.flash = .18
        if enemy.hp <= 0:
            enemy.dead = True
            self.score += 500 if enemy.kind=="guardian" else 120
            self.coins += 5 if enemy.kind=="guardian" else 1
            self.materials += 1
            self.burst(enemy.x+enemy.w/2, enemy.y+enemy.h/2,
                       "#c5b7ff" if enemy.kind=="bat" else "#8fffc3",20)
            if enemy.kind == "guardian":
                self.notify("城堡守卫已击败，传送门开启！",3)

    def shoot(self):
        p = self.player
        if self.state != "play" or p.cooldown > 0:
            return
        self.shots.append(Body(p.x+p.w/2+p.facing*24,p.y+20,
                               12,12,vx=p.facing*570))
        p.cooldown = .32
        self.burst(p.x+p.w/2+p.facing*22,p.y+26,"#a3f6ff",4)

    def build(self, tx, ty, remove=False):
        if self.state != "play" or not self.build_mode:
            return False
        p = self.player
        if math.hypot(tx*TILE+20-(p.x+p.w/2),
                      ty*TILE+20-(p.y+p.h/2)) > 205:
            self.notify("只能改造身边 5 格以内的区域。",1.2)
            return False
        if remove:
            if (tx,ty) in self.level.built:
                del self.level.tiles[tx,ty]
                self.level.built.remove((tx,ty))
                self.materials += 1
                return True
            self.notify("右键可以回收自己放置的方块。",1.2)
            return False
        block = Body(tx*TILE,ty*TILE,TILE,TILE)
        if self.materials <= 0:
            self.notify("方块用完了，打怪或顶宝箱可以补充。")
            return False
        if (not (0 <= tx < self.level.width and 3 <= ty <= 14)
                or (tx,ty) in self.level.tiles or overlap(p,block)
                or abs(tx*TILE-self.level.portal_x)<100
                or abs(tx*TILE-self.level.checkpoint_x)<65
                or any(not e.dead and overlap(e,block) for e in self.level.enemies)
                or any(overlap(h,block) for h in self.level.hazards)):
            return False
        self.level.tiles[tx,ty] = "X"
        self.level.built.add((tx,ty))
        self.materials -= 1
        self.burst(tx*TILE+20,ty*TILE+20,"#9eeed9",6)
        return True

    def update(self, dt, keys):
        if self.state != "play":
            return
        self.time += dt
        p = self.player
        p.invulnerable = max(0,p.invulnerable-dt)
        p.star = max(0,p.star-dt)
        p.cooldown = max(0,p.cooldown-dt)
        p.jump_buffer = max(0,p.jump_buffer-dt)
        p.coyote = .10 if p.grounded else max(0,p.coyote-dt)
        self.message_time = max(0,self.message_time-dt)

        axis = int(bool(keys & {"d","right"})) - int(bool(keys & {"a","left"}))
        speed = 350 if keys & {"shift_l","shift_r"} else 245
        target = axis * speed
        acceleration = 2000 if p.grounded else 1450
        if p.invulnerable > 1.4:
            acceleration = 420
        p.vx += max(-acceleration*dt,min(acceleration*dt,target-p.vx))
        if axis:
            p.facing = axis
        if p.jump_buffer > 0 and (p.jumps > 0 or p.coyote > 0):
            if p.coyote > 0:
                p.jumps = 2
            p.vy = -655
            p.jumps -= 1
            p.jump_buffer = p.coyote = 0
            p.grounded = False
            self.burst(p.x+p.w/2,p.y+p.h,"#f5cfef",8)
        if "j" in keys:
            self.shoot()
        p.vy = min(900,p.vy+GRAVITY*dt)
        previous_bottom = p.y+p.h
        p.grounded = self.move(p,dt,True)
        if p.grounded:
            p.jumps = 2
        if p.y > H+80:
            self.damage(falling=True)
            return

        for item in self.level.pickups:
            if not item.collected and overlap(p,item):
                item.collected = True
                if item.kind == "coin":
                    self.coins += 1
                    self.score += 50
                    color = "#ffe58c"
                elif item.kind == "heart":
                    p.hp = min(5,p.hp+1)
                    self.notify("拾取爱心，恢复生命！")
                    color = "#ff8faa"
                else:
                    p.star = 8
                    self.notify("获得星光护盾！")
                    color = "#fff3b0"
                self.burst(item.x+item.w/2,item.y+item.h/2,color,8)

        for e in self.level.enemies:
            if e.dead:
                continue
            e.flash = max(0,e.flash-dt)
            if e.kind == "bat":
                e.x += e.vx*dt
                if e.x < e.left or e.x > e.right:
                    e.vx = -e.vx
                    e.x = max(e.left,min(e.x,e.right))
                e.y = e.base_y+math.sin(self.time*2.5+e.phase)*35
            else:
                e.vy = min(900,e.vy+GRAVITY*dt)
                landed = self.move(e,dt)
                if landed:
                    ahead = e.x+e.w+5 if e.vx>0 else e.x-5
                    if not self.solid_at(ahead,e.y+e.h+4):
                        e.vx = -e.vx
                if e.y > H+120:
                    e.dead = True
                    continue
            if overlap(p,e):
                if p.star > 0:
                    self.kill_or_hit(e,10)
                elif p.vy >= 0 and previous_bottom <= e.y+13:
                    self.kill_or_hit(e,1)
                    p.y = e.y-p.h
                    p.vy = -460
                    p.jumps = max(1,p.jumps)
                else:
                    self.damage(source_x=e.x)
            if self.state != "play":
                return

        for hazard in self.level.hazards:
            if overlap(p,hazard):
                self.damage(source_x=hazard.x)
        if self.state != "play":
            return

        live_shots = []
        for shot in self.shots:
            shot.x += shot.vx*dt
            hit = any(overlap(shot,b) for _,_,_,b in self.nearby_tiles(shot))
            if not hit:
                for e in self.level.enemies:
                    if not e.dead and overlap(shot,e):
                        self.kill_or_hit(e)
                        hit = True
                        break
            if not hit and abs(shot.x-p.x)<850:
                live_shots.append(shot)
        self.shots = live_shots

        if not self.checkpoint and abs(p.x-self.level.checkpoint_x)<48 and p.y>420:
            self.checkpoint = True
            p.hp = min(5,p.hp+1)
            self.notify("存档点已激活，摔落后从这里继续。",3)
            self.burst(self.level.checkpoint_x,490,"#bff7dc",25)

        portal = Body(self.level.portal_x,440,72,120)
        if overlap(p,portal):
            guardian_alive = any(e.kind=="guardian" and not e.dead
                                 for e in self.level.enemies)
            if guardian_alive:
                self.notify("先击败附近的城堡守卫，再进入传送门。",1)
            else:
                self.score += 600+p.hp*100
                self.state = "stageclear" if self.level_index<2 else "win"
                self.burst(portal.x+30,portal.y+50,"#d9b5ff",40)

        target_camera = max(0,min(p.x-W*.36,self.level.width*TILE-W))
        self.camera += (target_camera-self.camera)*min(1,dt*7)
        live_particles = []
        for part in self.particles:
            part.life -= dt
            if part.life > 0:
                part.x += part.vx*dt
                part.y += part.vy*dt
                part.vy += 550*dt
                live_particles.append(part)
        self.particles = live_particles[-180:]


# 原创像素角色和怪物；每个字符代表一个像素，不依赖外部素材。
HERO_PIXELS = [
    "................", ".....hhhhhh.....", "....hhhhhhhh....",
    "...hhhhhhhhhh...", "...hhsssssshh...", "...hhskssskhh...",
    "...hhsssssshh...", "...hhhssrshhh...", "...hhhsssshhh...",
    "...hhpppppphh...", "...hbppppppbh...", "...hbppppppbh...",
    "...hsppppppsh...", "....sppwwpps....", "....sppwwpps....",
    ".....pppppp.....", ".....vvvvvv.....", ".....vvvvvv.....",
    ".....vv..vv.....", ".....ss..ss.....", ".....ss..ss.....",
    "....kkk..kkk....", "....kkk..kkk....", "................",
]
SLIME_PIXELS = [
    "................", "................", ".....gggggg.....",
    "...gggggggggg...", "..gggllllllggg..", ".ggllllllllllgg.",
    ".gllkkllllkkllg.", ".gllkkllllkkllg.", ".gllllllllllllg.",
    ".gllllmmmmllllg.", ".ggllllllllllgg.", "..gggggggggggg..",
    "...gggggggggg...", "..ggg......ggg..", "................",
    "................",
]
CRAB_PIXELS = [
    "................", "..r..........r..", ".rrr........rrr.",
    ".rrr..rrrr..rrr.", "..rrrrrrrrrrrr..", "...rrrwwwwrrr...",
    "..rrrrkwkwrrrr..", "..rrrrrrrrrrrr..", ".rrrrrrrrrrrrrr.",
    "..rrrrssssrrrr..", "...rrrrrrrrrr...", "..rr..rrrr..rr..",
    ".rr...r..r...rr.", ".r....r..r....r.", "................",
    "................",
]
BAT_PIXELS = [
    "..................", ".b..............b.", ".bb............bb.",
    ".bbb...bb...bbb...", ".bbbb.bbbb.bbbbb..", ".bbbbbbbbbbbbbbb..",
    "..bbbwwbbwwbbb...", "...bbwkbbkwbb....", "....bbbbbbbb.....",
    ".....bbrrbb......", "......bbbb.......", ".......bb........",
    "..................", "..................",
]
COIN_PIXELS = [
    "..yyyy..", ".yooooy.", "yooyyooy", "yoyyyyoy",
    "yoywyyoy", "yoywyyoy", "yoywyyoy", "yoyyyyoy", "yooyyooy",
    ".yooooy.", "..yyyy..", "........",
]
HEART_PIXELS = [
    "............", "..rrr..rrr..", ".rppprrpppr.", ".rppppppppr.",
    ".rppwwppppr.", "..rppppppr..", "...rppppr...", "....rppr....",
    ".....rr.....", "............", "............", "............",
]
STAR_PIXELS = [
    "......y......", ".....yyy.....", ".....ywy.....", "yyyyyywyyyyyy",
    ".yyyywwwyyyy.", "..yyywwwyyy..", "...yyyyyyy...", "..yyyyyyyyy..",
    "..yyyy.yyyy..", ".yyy.....yyy.", ".y.........y.", ".............",
    ".............",
]
PALETTES = {
    "hero": {"h":"#343348","s":"#ffd7bb","k":"#272b45","r":"#d67581",
             "p":"#ed8eae","w":"#fff0dc","v":"#a495d6","b":"#72bfae"},
    "slime": {"g":"#318273","l":"#86d9a3","k":"#243e51","m":"#448b79"},
    "crab": {"r":"#c06e77","s":"#f1a5a0","w":"#fff2d0","k":"#352d52"},
    "bat": {"b":"#8270bd","w":"#efe5ff","k":"#352c57","r":"#f4b3d1"},
    "coin": {"y":"#bd7b32","o":"#ffd473","w":"#fff9d4"},
    "heart": {"r":"#b66082","p":"#ff9cb7","w":"#ffdecb"},
    "star": {"y":"#ffd879","w":"#fff8c7"},
}


class PixelArt:
    def __init__(self):
        self.cache = {}

    def sprite(self, name, scale=2, flip=False, frame=0):
        key = (name,scale,flip,frame)
        if key in self.cache:
            return self.cache[key]
        patterns = {"hero":HERO_PIXELS,"slime":SLIME_PIXELS,"crab":CRAB_PIXELS,
                    "bat":BAT_PIXELS,"coin":COIN_PIXELS,"heart":HEART_PIXELS,
                    "star":STAR_PIXELS}
        original = patterns[name]
        width = max(map(len,original))
        pixels = [list(row.ljust(width,".")) for row in original]
        if name == "hero" and frame:
            # 改变脚的位置形成两帧走路动画。
            for y in [19,20,21,22]:
                pixels[y] = ["."]*width
            for y in [19,20]:
                for x in [4,5,10,11]:
                    pixels[y][x] = "s"
            for x in [3,4,5,10,11,12]:
                pixels[21][x] = "k"
                pixels[22][x] = "k"
        if name == "slime" and frame:
            pixels = [["."]*width]*2 + pixels[:-2]
        if flip:
            pixels = [row[::-1] for row in pixels]
        image = tk.PhotoImage(width=width,height=len(pixels))
        palette = PALETTES[name]
        for y,row in enumerate(pixels):
            for x,char in enumerate(row):
                if char in palette:
                    image.put(palette[char],to=(x,y))
        image = image.zoom(scale,scale)
        self.cache[key] = image
        return image

    def tile(self, kind, theme):
        key = ("tile",kind,theme)
        if key in self.cache:
            return self.cache[key]
        image = tk.PhotoImage(width=20,height=20)
        rng = random.Random(ord(kind)*17+theme)
        if kind == "G":
            base,spot,top = "#a17c69","#866452","#84b78b"
        elif kind == "D":
            base,spot,top = "#9a7868","#795c52","#aa8974"
        elif kind == "S":
            base,spot,top = "#797890","#605f7b","#b2abc1"
        elif kind == "B":
            base,spot,top = ("#b29488","#826c77","#dbc1a1") if theme==0 else (
                "#8b81a5","#625d80","#b5a5c8")
        elif kind == "Q":
            base,spot,top = "#e6b86c","#bf854e","#ffe5a1"
        elif kind == "U":
            base,spot,top = "#a28b7f","#816d71","#c5b299"
        else:
            base,spot,top = "#69aaae","#3e7f8d","#acf0d5"
        image.put(base,to=(0,0,20,20))
        image.put(top,to=(0,0,20,2))
        image.put(spot,to=(0,18,20,20))
        image.put(spot,to=(18,2,20,20))
        for _ in range(13):
            x,y = rng.randrange(2,17),rng.randrange(4,17)
            image.put(spot,to=(x,y,x+2,y+2))
        if kind == "G":
            image.put(top,to=(0,0,20,4))
            for x in range(0,20,4):
                image.put("#638e73",to=(x,3,x+2,6))
        if kind == "B":
            for y in [7,14]:
                image.put(spot,to=(0,y,20,y+1))
            for x,y in [(10,2),(5,8),(15,8),(10,15)]:
                image.put(spot,to=(x,y,x+1,min(20,y+6)))
        if kind == "Q":
            question = [".xxx.","x...x","....x","...x.","..x..",".....","..x.."]
            for y,row in enumerate(question):
                for x,c in enumerate(row):
                    if c=="x":
                        image.put("#fff4cf",to=(5+x*2,3+y*2,7+x*2,5+y*2))
        if kind == "X":
            image.put(top,to=(4,4,16,6))
            image.put(top,to=(4,6,6,16))
        self.cache[key] = image.zoom(2,2)
        return self.cache[key]


class GameApp:
    def __init__(self, root):
        self.root = root
        root.title(TITLE+"  |  Python 像素冒险")
        root.resizable(False,False)
        self.canvas = tk.Canvas(root,width=W,height=H,bg="#29283e",
                                highlightthickness=0)
        self.canvas.pack()
        self.art = PixelArt()
        self.game = GameModel()
        self.keys = set()
        self.buttons = []
        self.record = {"best":0,"unlocked":0}
        self.load_record()
        self.last = time.perf_counter()
        self.accumulator = 0.0
        self.saved_result = None
        self.font = self.choose_font()
        root.bind("<KeyPress>",self.key_down)
        root.bind("<KeyRelease>",self.key_up)
        root.bind("<FocusOut>",self.focus_out)
        self.canvas.bind("<Button-1>",self.left_click)
        self.canvas.bind("<Button-3>",self.right_click)
        self.canvas.bind("<Control-Button-1>",self.right_click)
        self.canvas.focus_set()
        self.loop()

    def choose_font(self):
        try:
            import tkinter.font as tkfont
            families = set(tkfont.families(self.root))
            for name in ["Microsoft YaHei","PingFang SC","Noto Sans CJK SC",
                         "WenQuanYi Zen Hei","SimHei"]:
                if name in families:
                    return name
        except tk.TclError:
            pass
        return "Arial"

    def load_record(self):
        try:
            data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
            self.record["best"] = max(0,int(data.get("best",0)))
            self.record["unlocked"] = max(0,min(2,int(data.get("unlocked",0))))
        except (OSError,ValueError,TypeError,AttributeError):
            pass

    def save_record(self):
        self.record["best"] = max(self.record["best"],self.game.score)
        if self.game.state in {"stageclear","win"}:
            self.record["unlocked"] = max(self.record["unlocked"],
                                         min(2,self.game.level_index+1))
        try:
            SAVE_PATH.write_text(json.dumps(self.record,ensure_ascii=False),
                                 encoding="utf-8")
        except OSError:
            pass  # 不能写存档时仍然可以正常游戏。

    def text(self,x,y,value,size=16,fill="#fff0de",anchor="center",bold=False):
        return self.canvas.create_text(x,y,text=value,fill=fill,anchor=anchor,
            font=(self.font,size,"bold" if bold else "normal"))

    def rect(self,x,y,w,h,color,outline="",width=1):
        self.canvas.create_rectangle(x,y,x+w,y+h,fill=color,
                                     outline=outline,width=width)

    def image(self,x,y,sprite,scale=2,flip=False,frame=0):
        self.canvas.create_image(round(x),round(y),anchor="nw",
                                 image=self.art.sprite(sprite,scale,flip,frame))

    def background(self, theme, camera):
        palettes = [
            ["#e8d2cc","#eddbce","#f1e3d0","#f7ebd7", "#c7b9be","#9eabb2","#8baaa2"],
            ["#a9a5c8","#b9afd0","#cebad3","#ddc5d5", "#9d92b5","#7d7e9e","#686f8c"],
            ["#292d51","#33385d","#424465","#55506f", "#4c486e","#57516e","#67607a"],
        ]
        colors = palettes[theme]
        for n,color in enumerate(colors[:4]):
            self.rect(0,n*130,W,130,color)
        self.rect(0,520,W,120,colors[3])
        # 方块太阳或月亮。
        self.rect(804,100,60,60,"#fff1be" if theme<2 else "#ede5ff")
        self.rect(796,108,76,44,"#fff1be" if theme<2 else "#ede5ff")
        if theme==2:
            for n in range(36):
                x = (n*137+43)%W
                y = 92+(n*79)%260
                self.rect(x,y,2+(n%2)*2,2+(n%2)*2,"#bcb5d6")
        # 像素云朵随远景缓慢移动。
        for n in range(7):
            x = (n*220-camera*.12)%(W+260)-180
            y = 136+(n%3)*42
            c = "#fff3e2" if theme<2 else "#66617f"
            self.rect(x,y+14,112,20,c)
            self.rect(x+18,y,68,40,c)
            self.rect(x+88,y+20,38,14,c)
        # 多层阶梯山峦，保持方块质感。
        for layer in range(3):
            parallax = [.16,.28,.42][layer]
            baseline = 460+layer*40
            for n in range(-2,12):
                x = n*150-(camera*parallax)%150
                height = 90+((n+layer*5)%4)*25
                self.rect(x,baseline-height,150,height+180,colors[4+layer])
                self.rect(x+22,baseline-height-30,106,30,colors[4+layer])
                self.rect(x+48,baseline-height-50,54,20,colors[4+layer])
        # 远景树木和城堡。
        if theme<2:
            for n in range(8):
                x = n*180-(camera*.55)%180
                trunk = "#8c7985" if theme==0 else "#655d7f"
                leaves = "#7b9b91" if theme==0 else "#8b82a5"
                self.rect(x+35,410,14,150,trunk)
                self.rect(x+5,366,72,66,leaves)
                self.rect(x+17,342,48,26,leaves)
                self.rect(x-7,388,96,30,leaves)
        else:
            for n in range(4):
                x = n*310-(camera*.4)%310
                self.rect(x,320,120,240,"#5b5575")
                self.rect(x-12,290,36,270,"#655e7d")
                self.rect(x+96,290,36,270,"#655e7d")
                for bx in [x-12,x,x+12,x+96,x+108,x+120]:
                    self.rect(bx,280,8,15,"#655e7d")
                self.rect(x+42,375,32,90,"#8d8098")
        # 标题真实出现在游戏背景中。
        self.text(W/2+2,109,TITLE,28,"#79758b",bold=True)
        self.text(W/2,107,TITLE,28,"#fff0de" if theme<2 else "#d9c9ec",bold=True)

    def draw_world(self):
        g = self.game
        level,p = g.level,g.player
        camera = g.camera
        self.background(g.level_index,camera)
        # 沟壑底部绘制熔岩或虚空，落入后返回存档点。
        for a,b in level.gaps:
            x = a*TILE-camera
            if x>W or x+(b-a)*TILE<0:
                continue
            self.rect(x,596,(b-a)*TILE,44,"#8d5768" if g.level_index<2 else "#6f5c98")
            for n in range(a,b):
                bob = int(math.sin(g.time*3+n)*3)
                self.rect(n*TILE-camera,594+bob,40,8,"#eaa17f" if g.level_index<2 else "#b796dc")

        for (tx,ty),kind in level.tiles.items():
            x = tx*TILE-camera
            if -TILE < x < W:
                self.canvas.create_image(round(x),ty*TILE,anchor="nw",
                                          image=self.art.tile(kind,g.level_index))
        # 地表小草与花。
        for tx in range(max(0,int(camera//TILE)),min(level.width,int((camera+W)//TILE)+1)):
            if level.tiles.get((tx,14)) == "G" and tx%3==0:
                x = tx*TILE-camera+8
                self.rect(x,552,3,8,"#638e73")
                self.rect(x-3,548,8,5,"#f3bdc4" if tx%2 else "#f1e3a0")

        for item in level.pickups:
            if item.collected or not -40 < item.x-camera < W+40:
                continue
            bob = math.sin(g.time*3+item.phase)*4
            self.image(item.x-camera,item.y+bob,item.kind)

        # 存档旗。
        cx = level.checkpoint_x-camera
        if -70<cx<W+70:
            self.rect(cx,470,5,90,"#d9ccb5")
            self.rect(cx+5,473,39,28,"#8ed8bb" if g.checkpoint else "#e1b597")
            self.text(cx+22,453,"存档点",12,"#fff3e0")
        # 终点传送门。
        px = level.portal_x-camera
        if -100<px<W+100:
            self.rect(px-6,426,84,134,"#8d75b4")
            self.rect(px+2,434,68,126,"#ead8f2")
            self.rect(px+10,442,52,118,"#53466c")
            for n in range(10):
                sy = 451+((n*21+g.time*32)%98)
                sx = px+16+(n*17)%40
                self.rect(sx,sy,4,4,"#c6b5fa")
            self.text(px+36,403,"传送门",14,"#fff1db",bold=True)

        for hazard in level.hazards:
            hx = hazard.x-camera
            if -80<hx<W:
                for n in range(4):
                    self.canvas.create_polygon(hx+n*18,560,hx+n*18+9,542,
                        hx+n*18+18,560,fill="#d9d4e1",outline="#8a809a")

        for e in level.enemies:
            if e.dead or not -80<e.x-camera<W+80:
                continue
            if e.flash>0 and int(g.time*40)%2==0:
                continue
            ex = e.x-camera
            if e.kind=="guardian":
                self.image(ex,e.y-4,"crab",4,flip=e.vx<0)
                self.rect(ex,e.y-14,64,5,"#463c60")
                self.rect(ex,e.y-14,64*max(0,e.hp)/6,5,"#f2b18f")
                self.text(ex+32,e.y-30,"城堡守卫",12)
            else:
                self.image(ex,e.y-2,e.kind,flip=e.vx<0,
                           frame=int(g.time*4)%2 if e.kind=="slime" else 0)
        # 主角阴影、星光护盾与像素动画。
        sx = p.x-camera
        if p.grounded:
            self.rect(sx-4,p.y+p.h-3,36,5,"#79687b")
        if p.star>0:
            self.canvas.create_oval(sx-12,p.y-12,sx+42,p.y+56,
                                     outline="#ffe7a0",width=3)
            for n in range(5):
                angle = g.time*2+n*math.tau/5
                self.rect(sx+14+math.cos(angle)*35,p.y+23+math.sin(angle)*35,
                          4,4,"#fff2bb")
        visible = p.invulnerable<=0 or int(g.time*12)%2==0
        if visible:
            frame = int(g.time*9)%2 if abs(p.vx)>20 and p.grounded else 0
            self.image(sx-2,p.y-2,"hero",flip=p.facing<0,frame=frame)
            self.text(sx+15,p.y-15,HERO,12,"#fff0de",bold=True)
        for shot in g.shots:
            x = shot.x-camera
            self.rect(x-5,shot.y-3,22,18,"#77b9c5")
            self.rect(x,shot.y,12,12,"#c5fff0")
            self.rect(x+3,shot.y+3,6,6,"#ffffff")
        for particle in g.particles:
            self.rect(particle.x-camera,particle.y,particle.size,particle.size,particle.color)

        if g.build_mode:
            # 建造网格仅覆盖附近可见区域。
            for x in range(-int(camera)%TILE,W,TILE):
                self.canvas.create_line(x,160,x,600,fill="#b3b7b1",dash=(2,8))
            for y in range(160,601,TILE):
                self.canvas.create_line(0,y,W,y,fill="#b3b7b1",dash=(2,8))
        self.draw_hud()

    def draw_hud(self):
        g,p = self.game,self.game.player
        self.rect(0,0,W,72,"#333047")
        self.rect(0,70,W,2,"#71657e")
        self.text(22,18,HERO,15,anchor="w",bold=True)
        for n in range(5):
            if n<p.hp:
                self.image(19+n*27,34,"heart")
            else:
                self.rect(24+n*27,39,14,12,"#665469")
        self.image(178,23,"coin")
        self.text(204,35,f"{g.coins:03d}",18,anchor="w",bold=True)
        self.text(295,23,"冒险分数",11,fill="#bdb0c7",anchor="w")
        self.text(295,45,f"{g.score:05d}",17,anchor="w",bold=True)
        self.text(500,27,g.level.name,17,bold=True)
        progress = max(0,min(1,p.x/g.level.portal_x))
        self.rect(422,49,156,5,"#63536e")
        self.rect(422,49,156*progress,5,"#e8b3c1")
        self.text(665,24,f"方块 {g.materials}",13)
        self.text(665,47,"建造中" if g.build_mode else "B 开启建造",11,
                  fill="#a7e2cd" if g.build_mode else "#bdb0c7")
        self.text(821,24,"二段跳  ·  J 魔法",13)
        self.text(821,48,f"护盾 {p.star:.0f}s" if p.star>0 else "P 暂停  /  R 重开",11,
                  fill="#ffe4a5" if p.star>0 else "#bdb0c7")
        self.rect(0,614,W,26,"#333047")
        hint = ("建造模式：左键放置  ·  右键回收自建方块  ·  B 退出建造"
                if g.build_mode else "A D / ← → 移动    Space / W / ↑ 跳跃    Shift 加速    J 魔法    B 建造    Esc 首页")
        self.text(W/2,626,hint,12,"#ded0dc")
        if g.message_time>0:
            self.rect(205,82,590,31,"#514660")
            self.text(500,97,g.message,13,"#fff1d8")

    def button(self,x,y,w,h,label,action,disabled=False):
        self.rect(x,y,w,h,"#696076" if disabled else "#e9b1bd")
        self.rect(x,y+h-4,w,4,"#51425e" if disabled else "#a57894")
        self.text(x+w/2,y+h/2-1,label,16,
                  "#a9a0b3" if disabled else "#343047",bold=True)
        if not disabled:
            self.buttons.append((x,y,x+w,y+h,action))

    def draw_menu(self):
        self.background(0,0)
        # 预览世界的地表和奖励方块。
        for x in range(0,W,TILE):
            self.canvas.create_image(x,560,anchor="nw",image=self.art.tile("G",0))
            self.canvas.create_image(x,600,anchor="nw",image=self.art.tile("D",0))
        self.rect(100,130,800,405,"#393247")
        self.rect(100,130,800,5,"#a493b3")
        self.text(500,182,TITLE,34,"#fff0dc",bold=True)
        self.text(500,222,"方块世界里，每一次出发都是新的故事。",14,"#c9b5ce")
        self.image(206,277,"hero",4)
        self.text(238,391,HERO,18,"#f5c1cc",bold=True)
        self.image(163,310,"coin",3)
        self.image(293,303,"star",3)
        self.text(400,269,"收集金币  ·  击败怪物  ·  探索三个世界",17,anchor="w")
        self.text(400,303,"二段跳越过沟壑，魔法击退敌人。",14,"#c9b5ce",anchor="w")
        self.text(400,330,"也可以搭起方块，走出自己的路。",14,"#c9b5ce",anchor="w")
        self.button(425,367,320,48,"开始冒险  /  Enter",("start",0))
        self.text(586,438,f"最高分 {self.record['best']:05d}    已解锁 {self.record['unlocked']+1}/3",12,"#c9b5ce")
        for n,name in enumerate(["风铃草原","暮色矿谷","星光城堡"]):
            unlocked = n<=self.record["unlocked"]
            self.button(225+n*190,472,170,36,
                        name if unlocked else name+"  未解锁",("start",n),not unlocked)
        self.text(500,590,"A D 移动   Space 二段跳   Shift 加速   J 魔法   B 建造   P 暂停",13,"#fff0dc")

    def draw_overlay(self):
        g = self.game
        if g.state=="paused":
            title,description = "旅途暂停", "休息一下，异世界会等你回来。"
            buttons = [("继续冒险  /  P",("resume",None)),("回到首页",("menu",None))]
        elif g.state=="gameover":
            title,description = "这次冒险暂时结束", "陈燕丽，下一次一定能走得更远。"
            buttons = [("重试本关  /  R",("restart",None)),("回到首页",("menu",None))]
        elif g.state=="stageclear":
            title,description = "世界探索完成", "下一片风景，正在等待陈燕丽。"
            buttons = [("进入下一关  /  Enter",("next",None)),("回到首页",("menu",None))]
        else:
            title,description = "陈燕丽的冒险圆满完成", "金币、勇气和星光，都是这段旅途的纪念。"
            buttons = [("再来一次  /  R",("start",0)),("回到首页",("menu",None))]
        self.rect(165,155,670,338,"#393247",outline="#b09ab9",width=3)
        self.text(500,207,title,27,"#fff0dc",bold=True)
        self.text(500,251,description,15,"#d5bfd6")
        self.text(500,299,f"冒险分数  {g.score}      金币  {g.coins}",20,"#f4c5ba",bold=True)
        for n,(label,action) in enumerate(buttons):
            self.button(325,345+n*60,350,45,label,action)

    def render(self):
        self.canvas.delete("all")
        self.buttons = []
        if self.game.state=="menu":
            self.draw_menu()
        else:
            self.draw_world()
            if self.game.state!="play":
                self.draw_overlay()

    def action(self, action):
        name,value = action
        self.keys.clear()
        if name=="start":
            self.game.start()
            if value:
                self.game.load_level(value,5)
            self.saved_result = None
        elif name=="resume":
            self.game.state = "play"
        elif name=="restart":
            self.game.restart()
            self.saved_result = None
        elif name=="next":
            self.game.advance()
            self.saved_result = None
        elif name=="menu":
            self.save_record()
            self.game.state = "menu"

    def key_down(self,event):
        key = event.keysym.lower()
        first = key not in self.keys
        self.keys.add(key)
        g = self.game
        if not first:
            return
        if key=="escape":
            self.action(("menu",None))
        elif key in {"return","kp_enter"}:
            if g.state=="menu":
                self.action(("start",0))
            elif g.state=="stageclear":
                self.action(("next",None))
        elif key=="p" and g.state in {"play","paused"}:
            g.state = "paused" if g.state=="play" else "play"
            self.keys = {"p"}
        elif key=="r" and g.state!="menu":
            self.action(("start",0) if g.state=="win" else ("restart",None))
        elif key=="b" and g.state=="play":
            g.build_mode = not g.build_mode
            g.notify("建造已开启：左键放置，右键回收。" if g.build_mode else "已返回冒险模式。")
        elif key in {"space","w","up"} and g.state=="play":
            g.player.jump_buffer = .15

    def key_up(self,event):
        key = event.keysym.lower()
        self.keys.discard(key)
        if key in {"space","w","up"} and self.game.player.vy < -280:
            self.game.player.vy *= .60

    def focus_out(self,event):
        self.keys.clear()
        if self.game.state=="play":
            self.game.state = "paused"

    def left_click(self,event):
        self.canvas.focus_set()
        for x1,y1,x2,y2,action in self.buttons:
            if x1<=event.x<=x2 and y1<=event.y<=y2:
                self.action(action)
                return
        if event.y>115:
            self.game.build(int((event.x+self.game.camera)//TILE),int(event.y//TILE))

    def right_click(self,event):
        if event.y>115:
            self.game.build(int((event.x+self.game.camera)//TILE),int(event.y//TILE),True)
        return "break"

    def loop(self):
        now = time.perf_counter()
        delta = min(.065,now-self.last)
        self.last = now
        self.accumulator += delta
        step = 1/120
        while self.accumulator>=step:
            self.game.update(step,self.keys)
            self.accumulator -= step
        state = self.game.state
        signature = (state,self.game.level_index,self.game.score)
        if state in {"stageclear","win","gameover"} and signature!=self.saved_result:
            self.save_record()
            self.saved_result = signature
        self.render()
        self.root.after(16,self.loop)


def main():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise SystemExit("无法打开游戏窗口，请在有桌面环境的电脑上运行本文件。\n"
                         +str(exc)) from exc
    GameApp(root)
    root.mainloop()


if __name__=="__main__":
    main()
