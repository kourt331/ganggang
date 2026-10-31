"""Physics Chronicles: a small three-era pixel-art action prototype.

Run: python3 physics_chronicles.py
Controls: Left/Right move, C double jump, Down+C drop through, Z dash, X sword/staff,
V blessing skill, F hand cannon/meteor, B buy staff, Space parry, Q/W/E physics skills.
M opens settings, F11 fullscreen, Esc windowed mode.
"""

import ctypes
import math
import random
import shutil
import subprocess
import sys
import time
import traceback
from functools import lru_cache
from pathlib import Path
import tkinter as tk


W, H = 1000, 640
ROOM_WIDTH = 2000
ROOM_COUNT = 5
SHOP_ROOM_INDEX = 2
SHOP_START_X = SHOP_ROOM_INDEX * ROOM_WIDTH
SHOP_EXIT_X = (SHOP_ROOM_INDEX + 1) * ROOM_WIDTH
SHOP_LEVER_X = SHOP_EXIT_X - 150
NEWTON_STALL_X = SHOP_START_X + 840
SHOP_BIRD_X = SHOP_START_X + 1220
SHOP_APPEAR_CHANCE = .35
SHOP_BLESSING_CHANCE = .30
SHOP_BLESSING_BRIBE = 500
WORLD = ROOM_WIDTH * ROOM_COUNT
WORLD_H = 1360
ROOF_TOP = 142
ROOF_BOTTOM = 182
PIT_DEPTH = 92
PX = 1.0
PLAYER_W, PLAYER_H = 32, 56
PLAYER_SPRITE_W, PLAYER_SPRITE_H = 40, 60
GRAVITY = 1.35
TERMINAL_VELOCITY = 24
MOB_HEAL_CHANCE = 0.25
MOB_HEAL_AMOUNT = 12
MAX_ACTIVE_ENEMIES = 6
FIXED_STEP_SECONDS = 1 / 60
MAX_CATCH_UP_STEPS = 8
ERAS = [
    {"place": "SYRACUSE", "age": "ANCIENT GREECE · STONE HARBOR", "boss": "ARCHIMEDES", "scholar": "ERATOSTHENES",
     "sky": "#59446f", "far": "#775b83", "near": "#c47e91", "ground": "#624b65", "accent": "#ffd17e",
     "mobs": ["지렛대 병사", "부력 장치병", "투석기 수호병"], "skill": "지렛대 올려베기"},
    {"place": "PISA · FLORENCE", "age": "RENAISSANCE ITALY · MEDIEVAL CITY", "boss": "GALILEO", "scholar": "TORRICELLI",
     "sky": "#57436f", "far": "#936887", "near": "#df918f", "ground": "#60485f", "accent": "#ffcf86",
     "mobs": ["경사면 기사", "낙하 장치병", "화승총 사수"], "skill": "관성 참격"},
    {"place": "CAMBRIDGE · LONDON", "age": "17TH-CENTURY ENGLAND · STONE TOWERS", "boss": "NEWTON", "scholar": "HALLEY",
     "sky": "#34466f", "far": "#50658c", "near": "#ae7899", "ground": "#494d70", "accent": "#f6cf8c",
     "mobs": ["중력 기사", "궤도 관측자", "반작용 수호병"], "skill": "중력 강타"},
]

MELEE_MOBS = {"지렛대 병사", "경사면 기사", "중력 기사", "반작용 수호병"}
RANGED_MOBS = {"부력 장치병", "투석기 수호병", "낙하 장치병", "화승총 사수", "궤도 관측자"}

DEFAULT_CONTROLS = {
    "move_left": "left", "move_right": "right", "jump": "c", "drop": "down",
    "dash": "z", "attack": "x", "parry": "space", "ranged": "f",
    "interact": "up", "skill_q": "q", "skill_w": "w", "skill_e": "e",
    "blessing": "v", "stats": "i", "shop_staff": "b",
}
CONTROL_ORDER = tuple(DEFAULT_CONTROLS)
CONTROL_LABELS = {
    "move_left": "왼쪽 이동", "move_right": "오른쪽 이동", "jump": "점프/더블 점프",
    "drop": "아래 발판으로 내려가기", "dash": "대쉬", "attack": "기본 공격",
    "parry": "패링", "ranged": "원거리 공격", "interact": "대화/상호작용",
    "skill_q": "물리 기술 Q", "skill_w": "물리 기술 W", "skill_e": "물리 기술 E",
    "blessing": "가호 기술", "stats": "스탯 창", "shop_staff": "지팡이 구매",
}
BLESSINGS = {
    "archimedes": {"figure": "아르키메데스", "skill": "지렛대 파동",
                   "damage": .12, "move": 0.0, "hp": 0},
    "galileo": {"figure": "갈릴레오", "skill": "관성 참격",
                "damage": 0.0, "move": .15, "hp": 0},
    "newton": {"figure": "뉴턴", "skill": "중력장",
               "damage": 0.0, "move": 0.0, "hp": 150},
}
CHAPTER_BLESSINGS = ("archimedes", "galileo", "newton")

PLAYER_PIXELS = [
    "......HHHH......", ".....HHHHHH.....", "....HHHHHHHH....", "...HHHPPPPHHH...",
    "...HHPPPPPPHH...", "....HPPPPPPH....", ".....HHHHHH.....", ".....BBBBBB.....",
    "....BBBBBBBB....", "...BBBBBBBBBB...", "..BBBBCCCCBBBB..", "..BBBBCCCCBBBB..",
    "..BBBBBBBBBBBB..", "..BBBBBBBBBBBB..", "..BBBBBBRBBBBB..", "...BBBBRRBBBB...",
    "...BBBBRRBBBB...", "...BBBRRRRBBB...", "....BBRRRRBB....", "....RR....RR....",
    "....RR....RR....", "...SSS....SSS...", "...SSS....SSS...", "..SSSS....SSSS..",
    "..SSSS....SSSS..",
]

SUNSET_PALETTE = {
    "melee": "#f18a8c", "ranged": "#56b7c4", "scholar": "#cb91d2",
    "boss": "#ffd16e", "hit": "#fff1d8", "outline": "#34354f",
}


class PhysicsChronicles:
    def __init__(self, root):
        self.root = root
        root.title("PHYSICS CHRONICLES")
        root.geometry("1100x700")
        root.minsize(760, 500)
        root.configure(bg="#090d16")
        self.canvas = tk.Canvas(root, bg="#090d16", highlightthickness=0)
        canvas = self.canvas
        canvas._physics_draw_tag = "frame"
        canvas_create = canvas._create

        def tagged_canvas_create(item_type, args, options):
            tag = canvas._physics_draw_tag
            if tag:
                tags = options.get("tags", ())
                if isinstance(tags, str):
                    tags = (tags,)
                options["tags"] = (*tags, tag)
            return canvas_create(item_type, args, options)

        canvas._create = tagged_canvas_create
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.resize)
        self.canvas.bind("<KeyPress>", self.key_down)
        self.canvas.bind("<KeyRelease>", self.key_up)
        self.canvas.focus_set()
        self.w, self.h = 1100, 700
        self.frame = 0
        self._last_tick_time = time.perf_counter()
        self._tick_accumulator = 0.0
        self.keys = set()
        self.controls = dict(DEFAULT_CONTROLS)
        self.settings_open = False
        self.settings_selection = 0
        self.rebinding_action = None
        self.stats_open = False
        self.blessing = None
        self.blessing_cd = 0
        self.blessing_events = {}
        self.blessing_menu = False
        self.blessing_offer_room = None
        self.shop_bird_menu = False
        self.blessing_damage_bonus = 0.0
        self.blessing_move_bonus = 0.0
        self.blessing_hp_bonus = 0
        self.chapter = 0
        self._background_cache_key = None
        self._background_camera = 0.0
        self.sky_gradient_cache = {
            chapter: tuple(
                self.color_mix(
                    era["sky"], era["far"], band / 29 * 1.65
                ) if band / 29 < .6 else self.color_mix(
                    era["far"], era["near"], (band / 29 - .6) / .4
                )
                for band in range(30)
            )
            for chapter, era in enumerate(ERAS)
        }
        self.phase = 0  # 0: enemy room, 1: scholar room, 2: historical boss room
        self.wave = 1
        self.round_number = 1
        self.skills = []
        self.max_hp = getattr(self, "max_hp", 200)
        self.player_damage_multiplier = getattr(self, "player_damage_multiplier", 1)
        self.gold = getattr(self, "gold", 0)
        self.damage_bonus = getattr(self, "damage_bonus", 0.0)
        self.staff_owned = getattr(self, "staff_owned", False)
        self.attack_speed_bonus = getattr(self, "attack_speed_bonus", 0.0)
        self.stat_purchases = getattr(self, "stat_purchases", {"health": 0, "damage": 0, "attack_speed": 0})
        self.hp = self.max_hp
        self.invulnerable = 0
        self.player = {"x": 120.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "face": 1, "grounded": False, "drop": 0, "jumps_used": 0,
                       "knockback_vx": 0.0, "knockback_frames": 0,
                       "dash_vx": 0.0, "dash_frames": 0, "dash_dir": 1,
                       "pit_id": None, "pit_damage_at": 0}
        self.attack_until = self.attack_cd = self.dash_until = self.dash_cd = 0
        self.attack_combo_count = 0
        self.attack_last_frame = None
        self.gun_until = self.gun_cd = self.player_action_until = 0
        self.player_action = ""
        self.hitstop_until = 0
        self.shake_until = 0
        self.shake_strength = 0
        self.parry_until = self.parry_cd = 0
        self.skill_cd = [0, 0, 0]
        self.swing_hits = set()
        self.enemies, self.platforms, self.obstacles = [], [], []
        self.coin_drops = []
        self.enemy_shots, self.player_shots, self.effects = [], [], []
        self.meteors = []
        self.spawn_queue = []
        self.spawn_next_at = 0
        # Keep the same wave size, but space appearances by 0.4 s so canvas
        # work and spawn flashes do not pile up in a single burst.
        self.spawn_gap = 24
        self.spawn_grace = 60
        self.room_waves = []
        self.room_wave_index = 0
        self.room_wave_started = False
        self.midrun_shop_active = False
        self.shop_room_index = None
        self.shop_bird_menu = False
        self.shop_exit_open = False
        self.waves_complete = False
        self.static_obstacles = []
        self.gate_obstacle = None
        self.safe_start_end = int(ROOM_WIDTH * .30)
        self.pits = []
        self.tnt_crates = []
        self.archimedes_ship_active = False
        self.transition = 0
        self.in_shop = False
        self.round_clear = False
        self.exit_door_x = None
        self.bird_x = None
        self.bird_menu = False
        self.blessing_menu = False
        self.blessing_offer_room = None
        self.blessing_events = {}
        self.training_damage = 0
        self.finished = False
        self.game_over = False
        self.notice = "세 시대를 지나 물리의 공식을 익히세요"
        self.notice_until = 240
        self.music_path = Path(__file__).with_name("physics_chronicles.wav")
        self.music_process = None
        self.music_mci_alias = "physicschroniclesmusic"
        self.music_mci_open = False
        self.music_enabled = True
        self.music_volume = 0.32
        self.closing = False
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.player_images = self.build_player_images()
        self.new_encounter()
        root.after(500, self.music_tick)
        self.tick()

    def music_tick(self):
        if self.closing:
            return
        if self.music_enabled and sys.platform == "darwin" and shutil.which("afplay") and self.music_path.exists():
            if self.music_process is None:
                self.start_music()
            elif self.music_process.poll() is not None:
                if self.music_process.returncode == 0:
                    self.start_music()
                else:
                    self.music_enabled = False
        elif self.music_enabled and sys.platform == "win32" and not self.music_mci_open:
            self.start_music()
        self.root.after(700, self.music_tick)

    def send_mci(self, command):
        if sys.platform != "win32":
            return False
        try:
            send_string = ctypes.windll.winmm.mciSendStringW
            send_string.argtypes = (
                ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p
            )
            send_string.restype = ctypes.c_uint
            return send_string(command, None, 0, None) == 0
        except (AttributeError, OSError, ctypes.ArgumentError, TypeError):
            return False

    def start_music(self):
        if not self.music_enabled or not self.music_path.exists():
            return
        if sys.platform == "darwin" and shutil.which("afplay"):
            self.music_process = subprocess.Popen(
                ["afplay", "-v", f"{self.music_volume:.2f}", str(self.music_path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "win32":
            if not self.music_mci_open:
                path = str(self.music_path).replace('"', '""')
                if not self.send_mci(
                        f'open "{path}" type waveaudio alias {self.music_mci_alias}'):
                    self.music_enabled = False
                    return
                self.music_mci_open = True
            volume = round(self.music_volume * 1000)
            self.send_mci(f"setaudio {self.music_mci_alias} volume to {volume}")
            if not self.send_mci(f"play {self.music_mci_alias} repeat"):
                self.music_enabled = False

    def restart_music(self):
        if self.music_process and self.music_process.poll() is None:
            self.music_process.terminate()
        self.music_process = None
        if sys.platform == "win32" and self.music_mci_open:
            self.send_mci(f"stop {self.music_mci_alias}")
            self.send_mci(f"seek {self.music_mci_alias} to start")
        if self.music_enabled:
            self.start_music()

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        if not self.music_enabled and self.music_process and self.music_process.poll() is None:
            self.music_process.terminate()
            self.music_process = None
        elif not self.music_enabled and sys.platform == "win32" and self.music_mci_open:
            self.send_mci(f"stop {self.music_mci_alias}")
        elif self.music_enabled:
            if sys.platform == "win32" and self.music_mci_open:
                self.send_mci(f"seek {self.music_mci_alias} to start")
            self.start_music()

    def close(self):
        self.closing = True
        if self.music_process and self.music_process.poll() is None:
            self.music_process.terminate()
        if sys.platform == "win32" and self.music_mci_open:
            self.send_mci(f"stop {self.music_mci_alias}")
            self.send_mci(f"close {self.music_mci_alias}")
            self.music_mci_open = False
        self.root.destroy()

    @property
    def ground(self):
        # Keep the play floor fixed when the spike-pit depth changes.
        return int(WORLD_H * .61)

    @property
    def camera(self):
        return max(0, min(WORLD - self.w, self.player["x"] - self.w * .4))

    @property
    def camera_y(self):
        # Keep the scholar below the viewport midpoint while following jumps
        # and the taller multi-level rooms.
        target = self.player["y"] + PLAYER_H / 2 - self.h * .68
        return max(0, min(WORLD_H - self.h, target))

    def sy(self, y):
        return y - self.camera_y

    def resize(self, event):
        self.w, self.h = max(1, event.width), max(1, event.height)

    def new_encounter(self):
        local_round = (self.round_number - 1) % 8 + 1
        self.chapter = min(2, (self.round_number - 1) // 8)
        era = ERAS[self.chapter]
        self.phase = 2 if local_round == 8 else 1 if local_round == 4 else 0
        self.boss_only_round = self.phase == 2
        self.shop_room_index = (SHOP_ROOM_INDEX
                                if not self.boss_only_round
                                and random.random() < SHOP_APPEAR_CHANCE else None)
        # Regular rounds get reachable platform lanes; boss rounds use a clear arena.
        self.platforms = []
        self.build_stage_geometry(boss_only=self.boss_only_round)
        self.room_patterns = []
        if self.boss_only_round:
            self.room_patterns = [0]
        else:
            for room in range(ROOM_COUNT):
                room_platforms = self.make_room_platforms(room)
                self.room_patterns.append(len(room_platforms))
                self.platforms.extend(room_platforms)
        self.enemies = []
        self.in_shop = False
        self.round_clear = False
        self.exit_door_x = None
        self.bird_x = None
        self.bird_menu = False
        self.blessing_events = {}
        self.blessing_menu = False
        self.blessing_offer_room = None
        self.enemy_shots.clear()
        self.player_shots.clear()
        self.meteors.clear()
        self.effects.clear()
        self.spawn_queue.clear()
        self.coin_drops.clear()
        self.spawn_next_at = self.frame + self.spawn_grace
        self.room_wave_index = 0
        self.room_wave_started = False
        self.midrun_shop_active = False
        self.shop_bird_menu = False
        self.shop_exit_open = False
        self.waves_complete = False
        self.player.update(pit_id=None, pit_damage_at=self.frame + 60)
        self.player.update(x=120.0, y=float(self.ground - PLAYER_H), vx=0, vy=0, face=1, grounded=True, drop=0, jumps_used=0)
        self.player.update(knockback_vx=0.0, knockback_frames=0, dash_vx=0.0, dash_frames=0, dash_dir=1)
        self.transition = 0
        self.room_waves = []
        if self.boss_only_round:
            # Eighth rounds are a single, obstacle-free boss arena.
            self.room_waves = [[(era["boss"], int(ROOM_WIDTH * .72), "boss")]]
        else:
            for room in range(ROOM_COUNT):
                base = room * ROOM_WIDTH
                # The third zone becomes a safe shop only on selected rounds.
                if room == self.shop_room_index:
                    group = []
                else:
                    mob_count = random.randint(2, 3) if room < SHOP_ROOM_INDEX else random.randint(2, 6)
                    group = self.make_room_wave(room, mob_count, era)
                if self.phase == 1 and room == 3:
                    group.append((era["scholar"], base + int(ROOM_WIDTH * .72), "scholar"))
                random.shuffle(group)
                self.room_waves.append(group)
            # Boons can appear only in a safe shop, with a separate chance roll.
            if self.shop_room_index is not None and random.random() < SHOP_BLESSING_CHANCE:
                self.blessing_events[self.shop_room_index] = {
                    "x": float(SHOP_START_X + 1550),
                    "chapter": self.chapter,
                    "used": False,
                    "clear_offer_shown": False,
                    "offer_until": 0,
                    "shop": True,
                }
        self.set_room_gate(0)
        if self.phase == 2:
            self.archimedes_ship_active = False
            self.say(f"PART {self.chapter + 1} BOSS  /  ROUND {self.round_number}  ·  안전 구역에서 출발")
        elif self.phase == 1:
            self.say(f"SCHOLAR MIDBOSS  /  ROUND {self.round_number}  ·  안전 구역에서 출발")
        else:
            self.say(f"ROUND {self.round_number}  /  PART {self.chapter + 1}  ·  안전 구역에서 출발")

    def make_room_platforms(self, room):
        """Create reachable air platforms with clear gaps and no overlaps."""
        base = room * ROOM_WIDTH
        start_ratio, end_ratio = ((.34, .91) if room == 0 else (.12, .88))
        lane_left = base + int(ROOM_WIDTH * start_ratio)
        lane_right = base + int(ROOM_WIDTH * end_ratio)
        count = 3 if room == 0 else 4
        cell_width = (lane_right - lane_left) / count
        room_pits = [pit for pit in self.pits
                     if pit["left"] < lane_right and pit["right"] > lane_left]
        ledges = []
        for index in range(count):
            cell_left = lane_left + index * cell_width
            cell_right = lane_left + (index + 1) * cell_width
            margin = 28
            safe_segments = [(cell_left + margin, cell_right - margin)]
            for pit in room_pits:
                next_segments = []
                for left, right in safe_segments:
                    if pit["left"] >= right or pit["right"] <= left:
                        next_segments.append((left, right))
                    else:
                        if pit["left"] - 24 > left:
                            next_segments.append((left, pit["left"] - 24))
                        if pit["right"] + 24 < right:
                            next_segments.append((pit["right"] + 24, right))
                safe_segments = next_segments
            if not safe_segments:
                continue
            left_edge, right_edge = max(safe_segments, key=lambda pair: pair[1] - pair[0])
            segment_width = right_edge - left_edge
            width = min(random.randint(250, 320), int(segment_width))
            if width < 150:
                continue
            left = int((left_edge + right_edge - width) / 2)
            # The fixed cells and margins leave a visible gap between every block.
            rise = random.randint(145, 205) if index == count - 1 else random.randint(85, 190)
            ledges.append((left, left + width, rise))

        # At least one elevated perch remains available to ranged enemies.
        if ledges and not any(rise >= 105 for _left, _right, rise in ledges):
            left, right, _rise = ledges[-1]
            ledges[-1] = (left, right, 150)
        return ledges

    def make_room_wave(self, room, count, era):
        """Spread a room's wave across the ground and each available high ledge."""
        base = room * ROOM_WIDTH
        melee_pool = [kind for kind in era["mobs"] if kind not in RANGED_MOBS]
        ranged_pool = [kind for kind in era["mobs"] if kind in RANGED_MOBS]
        ranged_count = random.randint(0, min(2, count, len(ranged_pool)))
        melee_kinds = [random.choice(melee_pool) for _ in range(count - ranged_count)]
        ranged_kinds = [random.choice(ranged_pool) for _ in range(ranged_count)]
        group = []

        if melee_kinds:
            start_ratio, end_ratio = ((.56, .94) if room == 0 else (.12, .88))
            start = base + int(ROOM_WIDTH * start_ratio)
            span = ROOM_WIDTH * (end_ratio - start_ratio)
            spacing = span / len(melee_kinds)
            for index, kind in enumerate(melee_kinds):
                jitter = random.uniform(-spacing * .15, spacing * .15)
                x = start + spacing * (index + .5) + jitter
                group.append((kind, int(x), "mob"))

        if ranged_kinds:
            ledges = [p for p in self.platforms
                      if base <= p[0] < base + ROOM_WIDTH
                      and p[2] >= 100 and p[1] - p[0] >= 150]
            if room == 0:
                min_spawn_x = base + int(ROOM_WIDTH * .55)
                ledges = [p for p in ledges if p[1] >= min_spawn_x + 220]
            else:
                min_spawn_x = base + int(ROOM_WIDTH * .18)
                ledges = [p for p in ledges if p[1] >= min_spawn_x + 220]
            random.shuffle(ledges)
            if ledges:
                lane_groups = [[] for _ in ledges]
                for index, kind in enumerate(ranged_kinds):
                    lane_groups[index % len(ledges)].append(kind)
                for lane, lane_kinds in zip(ledges, lane_groups):
                    if not lane_kinds:
                        continue
                    left, right, _rise = lane
                    margin = 56
                    lane_start = max(left + margin, min_spawn_x)
                    lane_end = right - margin
                    usable = max(1, lane_end - lane_start)
                    spacing = usable / len(lane_kinds)
                    for index, kind in enumerate(lane_kinds):
                        jitter = random.uniform(-spacing * .12, spacing * .12)
                        x = lane_start + spacing * (index + .5) + jitter
                        x = max(left + 12, min(right - 60, x))
                        group.append((kind, int(x), "mob"))
            else:
                # All generated room plans have ledges; this keeps any future
                # plan edits playable if one accidentally omits them.
                start = base + int(ROOM_WIDTH * (.55 if room == 0 else .18))
                for index, kind in enumerate(ranged_kinds):
                    group.append((kind, start + index * 150, "mob"))
        return group

    def build_stage_geometry(self, boss_only=False):
        """Generate ordinary room hazards, or leave a boss arena unobstructed."""
        ground = self.ground
        self.static_obstacles = []
        self.pits = []
        self.tnt_crates = []
        if boss_only:
            self.gate_obstacle = None
            self.refresh_obstacles()
            return
        for room in range(ROOM_COUNT):
            base = room * ROOM_WIDTH
            self.static_obstacles.append((base, ROOF_TOP, base + ROOM_WIDTH, ROOF_BOTTOM))

        # Keep the starting chamber safe, then place a few deep spike trenches
        # across the route. Their bottoms sit below the walking floor, so a
        # player who falls in must jump out instead of walking through them.
        pit_candidates = [room for room in range(1, ROOM_COUNT)
                          if room != self.shop_room_index]
        pit_rooms = random.sample(pit_candidates, k=min(2, len(pit_candidates)))
        for room in pit_rooms:
            base = room * ROOM_WIDTH
            width = random.randint(int(ROOM_WIDTH * .105), int(ROOM_WIDTH * .14))
            left = random.randint(base + int(ROOM_WIDTH * .34),
                                  base + int(ROOM_WIDTH * .70) - width)
            self.pits.append({"left": left, "right": left + width,
                              "bottom": ground + PIT_DEPTH})
        self.pits.sort(key=lambda pit: pit["left"])

        for boundary in range(ROOM_WIDTH, WORLD, ROOM_WIDTH):
            if (self.shop_room_index is not None
                    and boundary == self.shop_room_index * ROOM_WIDTH):
                continue
            # Keep explosive barrels clear of the spike trenches.
            if random.random() < .58:
                crate_x = boundary + random.choice(tuple(int(ROOM_WIDTH * ratio)
                                                         for ratio in (.12, .17, .22)))
                self.tnt_crates.append({"x": crate_x, "y": ground - 62,
                                        "w": 52, "h": 62, "fuse": None})
        self.gate_obstacle = None
        self.refresh_obstacles()

    def pit_at(self, x):
        """Return (index, pit) for a horizontal world coordinate in a pit."""
        for index, pit in enumerate(self.pits):
            if pit["left"] <= x <= pit["right"]:
                return index, pit
        return None, None

    def refresh_obstacles(self):
        self.obstacles = list(self.static_obstacles)
        if self.gate_obstacle is not None:
            self.obstacles.append(self.gate_obstacle)
        self.obstacles.extend((crate["x"], crate["y"], crate["x"] + crate["w"],
                               crate["y"] + crate["h"]) for crate in self.tnt_crates)

    def set_room_gate(self, room):
        """Seal the next chamber until this room's entire enemy wave is cleared."""
        next_boundary = (room + 1) * ROOM_WIDTH
        if getattr(self, "boss_only_round", False) or room >= ROOM_COUNT - 1:
            self.gate_obstacle = None
        else:
            self.gate_obstacle = (next_boundary - 48, ROOF_BOTTOM,
                                  next_boundary + 48, self.ground)
        self.refresh_obstacles()

    def resolve_horizontal_obstacles(self, actor, old_x, y, width, height):
        """Resolve movement against the room dividers and solid props."""
        x = actor["x"]
        for left, top, right, bottom in self.obstacles:
            if y + height <= top or y >= bottom:
                continue
            if old_x + width <= left and x + width > left:
                x = left - width
            elif old_x >= right and x < right:
                x = right
            elif x < right and x + width > left:
                # Recover safely if an external impulse starts the actor inside a wall.
                push_left, push_right = x + width - left, right - x
                x = left - width if push_left < push_right else right
        actor["x"] = max(0, min(WORLD - width, x))

    def resolve_vertical_obstacles(self, actor, old_y, width, height):
        """Return a landing surface or stop an actor against a wall underside."""
        x, y = actor["x"], actor["y"]
        landing = None
        for left, top, right, bottom in self.obstacles:
            if x + width <= left or x >= right:
                continue
            old_bottom, new_bottom = old_y + height, y + height
            if actor.get("vy", 0) >= 0 and old_bottom <= top <= new_bottom:
                landing = top if landing is None else min(landing, top)
            elif actor.get("vy", 0) < 0 and old_y >= bottom >= y:
                actor["y"], actor["vy"] = bottom, 0
        return landing

    def shot_hits_wall(self, x1, y1, x2, y2):
        """Use swept segment collision so fast bolts cannot tunnel through stone."""
        return any(self.segment_hits_rect(x1, y1, x2, y2, rect)
                   for rect in self.obstacles)

    @staticmethod
    def segment_hits_rect(x1, y1, x2, y2, rect):
        """Liang–Barsky segment/rectangle test for projectiles and TNT barrels."""
        left, top, right, bottom = rect
        dx, dy = x2 - x1, y2 - y1
        low, high = 0.0, 1.0
        for p, q in ((-dx, x1 - left), (dx, right - x1),
                     (-dy, y1 - top), (dy, bottom - y1)):
            if abs(p) < 1e-9:
                if q < 0:
                    return False
                continue
            ratio = q / p
            if p < 0:
                low = max(low, ratio)
            else:
                high = min(high, ratio)
            if low > high:
                return False
        return True

    def ignite_tnt(self, x1, y1, x2, y2):
        for crate in self.tnt_crates:
            rect = (crate["x"], crate["y"], crate["x"] + crate["w"], crate["y"] + crate["h"])
            if self.segment_hits_rect(x1, y1, x2, y2, rect):
                if crate["fuse"] is None:
                    crate["fuse"] = self.frame + 36
                    self.say("TNT 점화! 폭발 범위에서 벗어나세요")
                return True
        return False

    def detonate_tnt(self, crate):
        x, y = crate["x"] + crate["w"] / 2, crate["y"] + crate["h"] / 2
        radius = 164
        self.effects.append(["tnt_blast", x, y, 22, radius])
        for enemy in self.enemies:
            ex, ey = enemy["x"] + enemy["w"] / 2, enemy["y"] + enemy["h"] / 2
            if math.hypot(ex - x, ey - y) <= radius:
                self.damage_enemy(enemy, 82)
        px, py = self.player["x"] + PLAYER_W / 2, self.player["y"] + PLAYER_H / 2
        if math.hypot(px - x, py - y) <= radius:
            self.hurt(30)

    def update_hazards(self):
        for crate in list(self.tnt_crates):
            if crate["fuse"] is not None and self.frame >= crate["fuse"]:
                self.tnt_crates.remove(crate)
                self.refresh_obstacles()
                self.detonate_tnt(crate)
        player = self.player
        pit_id = player.get("pit_id")
        if (pit_id is not None and pit_id < len(self.pits)
                and player["grounded"]
                and player["y"] + PLAYER_H >= self.pits[pit_id]["bottom"] - 1):
            if self.frame >= player.get("pit_damage_at", 0):
                # Pit damage ticks at one-second intervals and does not throw
                # the player upward, so the hazard remains readable and fair.
                self.hp = max(0, self.hp - 12)
                player["pit_damage_at"] = self.frame + 60
                self.effects.append(["hit", player["x"] + PLAYER_W / 2,
                                     self.pits[pit_id]["bottom"] - 5, 14])
                self.shake_strength = max(self.shake_strength, 2)
                self.shake_until = max(self.shake_until, self.frame + 5)
                if self.hp <= 0:
                    self.game_over = True
                    self.say("스파이크 함정에 쓰러졌습니다  /  R 키로 다시 시작")

    def queue_enemy(self, kind, x, rank):
        self.spawn_queue.append((kind, x, rank))

    def update_spawns(self):
        if (self.shop_room_index is not None
                and self.room_wave_index == self.shop_room_index):
            if not self.midrun_shop_active:
                if self.player["x"] + PLAYER_W < SHOP_START_X:
                    return
                self.midrun_shop_active = True
                self.room_wave_started = True
                self.spawn_queue.clear()
                if self.room_wave_index in self.blessing_events:
                    self.say(f"3번째 구역 · 안전 상점  /  위인의 기운이 감지됩니다 · {self.key_label(self.controls['interact'])} 레버로 출구 열기")
                else:
                    self.say(f"3번째 구역 · 안전 상점  /  비둘기와 지팡이 상점 · {self.key_label(self.controls['interact'])} 레버로 출구 열기")
            if self.shop_exit_open and self.player["x"] + PLAYER_W >= SHOP_EXIT_X + 24:
                self.collect_all_coins()
                self.room_wave_index += 1
                self.midrun_shop_active = False
                self.shop_exit_open = False
                self.room_wave_started = False
                self.set_room_gate(self.room_wave_index)
                self.say(f"상점을 나왔습니다 · 구역 {self.room_wave_index + 1}/{ROOM_COUNT} 진입")
            return

        if self.waves_complete or self.room_wave_index >= len(self.room_waves):
            self.waves_complete = True
            return
        if not self.room_wave_started:
            room_start = self.room_wave_index * ROOM_WIDTH
            trigger_x = self.safe_start_end if self.room_wave_index == 0 else room_start + 4
            if self.player["x"] < trigger_x:
                return
            self.room_wave_started = True
            self.spawn_queue = sorted(self.room_waves[self.room_wave_index],
                                      key=lambda spec: (spec[2] == "boss", spec[1]))
            grace = self.spawn_grace if self.room_wave_index == 0 else 30
            self.spawn_next_at = self.frame + grace
            if self.room_wave_index == 0:
                self.say("안전 구역을 벗어났습니다 · 적 무리가 접근합니다")

        # Preserve the complete wave in the queue, releasing one enemy only
        # when fewer than six are active so simultaneous load stays bounded.
        if (self.spawn_queue and len(self.enemies) < MAX_ACTIVE_ENEMIES
                and self.frame >= self.spawn_next_at):
            kind, x, rank = self.spawn_queue.pop(0)
            self.add_enemy(kind, x, rank)
            enemy = self.enemies[-1]
            self.effects.append(["spawn", enemy["x"] + enemy["w"] / 2,
                                 enemy["y"] + enemy["h"] / 2, 18])
            self.spawn_next_at = self.frame + self.spawn_gap
            return

        if not self.spawn_queue and not self.enemies:
            event = self.blessing_events.get(self.room_wave_index)
            if event and not event["used"]:
                if not event["clear_offer_shown"]:
                    event["x"] = max(self.room_wave_index * ROOM_WIDTH + 120,
                                     min((self.room_wave_index + 1) * ROOM_WIDTH - 160,
                                         self.player["x"] + 72))
                    event["clear_offer_shown"] = True
                    event["offer_until"] = self.frame + 240
                    self.say(f"{BLESSINGS[CHAPTER_BLESSINGS[event['chapter']]]['figure']}의 혼이 나타났다 · 가까이 가서 대화하세요")
                    return
                if self.frame < event["offer_until"]:
                    return
            if self.room_wave_index + 1 >= len(self.room_waves):
                self.waves_complete = True
                self.gate_obstacle = None
                self.refresh_obstacles()
                return
            collected = self.collect_all_coins()
            self.room_wave_index += 1
            self.room_wave_started = False
            self.set_room_gate(self.room_wave_index)
            pickup_text = f" · 남은 동전 {collected} G 자동 회수" if collected else ""
            self.say(f"구역 {self.room_wave_index + 1}/{ROOM_COUNT} 개방 · 다음 적 무리 접근 중{pickup_text}")

    def open_midrun_shop_exit(self):
        if not self.midrun_shop_active or self.shop_exit_open:
            return
        self.shop_exit_open = True
        self.gate_obstacle = None
        self.refresh_obstacles()
        self.effects.append(["lever", SHOP_LEVER_X, self.ground - 42, 18])
        self.say("레버를 내렸습니다 · 오른쪽 문이 열렸습니다")

    def add_enemy(self, kind, x, rank):
        if rank == "boss":
            width, height, hp = 250, 320, 1800
        elif rank == "scholar":
            width, height, hp = 58, 84, 390
        elif kind in RANGED_MOBS:
            width, height, hp = 44, 66, 72
        elif kind in MELEE_MOBS:
            width, height, hp = 48, 76, 96
        else:
            width, height, hp = 42, 68, 80
        if rank == "mob":
            # These regular enemies were previously at 1.5x lower HP. Reduce
            # that current value by another factor of 1.2.
            hp = int(round(hp * 10 / 9))
        ledge_bounds = None
        if rank == "mob" and kind in RANGED_MOBS:
            room = max(0, min(ROOM_COUNT - 1, int(x // ROOM_WIDTH)))
            elevated = [p for p in self.platforms
                        if room * ROOM_WIDTH <= p[0] < (room + 1) * ROOM_WIDTH
                        and p[2] >= 100 and p[1] - p[0] >= width + 32]
            lane_options = [p for p in elevated if p[0] <= x <= p[1]]
            lane = (random.choice(lane_options) if lane_options else
                    min(elevated, key=lambda p: abs((p[0] + p[1]) / 2 - x))
                    if elevated else (0, WORLD, 0))
            if elevated:
                left, right, _rise = lane
                x = max(left + 16, min(right - width - 16, x))
                ledge_bounds = (left, right)
        else:
            lane = (0, WORLD, 0)
        left, right, rise = lane
        x = max(left + 8, min(right - width - 8, x))
        self.enemies.append({"kind": kind, "rank": rank, "x": float(x), "y": float(self.ground - rise - height),
                             "w": width, "h": height, "hp": hp, "maxhp": hp, "vy": 0.0,
                             "grounded": False, "drop": 0, "jump_cd": 0, "face": -1,
                             "state": "idle", "timer": random.randint(25, 70), "action": "", "hit": 0,
                             "dash_cd": 0, "platform_bounds": ledge_bounds,
                             "pit_id": None, "pit_escape_side": None,
                             "float_y": float(self.ground - rise - height), "move_phase": random.random() * math.tau,
                             "boss_phase": "ship" if rank == "boss" and self.chapter == 0 and getattr(self, "archimedes_ship_active", False) else "normal",
                             "next_reposition": self.frame + 900, "wheel_hits": False,
                             "gravity_cd": self.frame + 180})

    def action_down(self, action):
        return self.controls.get(action) in self.keys

    def key_down(self, event):
        key = event.keysym.lower()
        if key in self.keys:
            return
        self.keys.add(key)
        if self.rebinding_action is not None:
            if key == "escape":
                self.rebinding_action = None
                self.keys.clear()
                return
            self.assign_control(self.rebinding_action, key)
            return
        if self.settings_open:
            self.handle_settings_key(key)
            return
        if key == "m":
            self.settings_open = True
            self.settings_selection = 0
            self.keys.clear()
            return
        if key == self.controls["stats"]:
            self.stats_open = not self.stats_open
            self.keys.clear()
            return
        if self.stats_open:
            if key == "escape":
                self.stats_open = False
                self.keys.clear()
            return
        if key == "f11":
            self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))
            return
        if self.bird_menu:
            if key == "1":
                self.buy_stat("health")
            elif key == "2":
                self.buy_stat("damage")
            elif key == "3":
                self.buy_stat("attack_speed")
            elif key == "5":
                self.buy_healing_potion()
            elif key in (self.controls["interact"], "escape"):
                self.bird_menu = False
                self.say("비둘기가 동전을 챙겨 날아간다")
            return
        if self.shop_bird_menu:
            if key == "1":
                self.buy_full_heal()
            elif key == "2":
                self.summon_shop_blessing()
            elif key in (self.controls["interact"], "escape"):
                self.shop_bird_menu = False
                self.say("비둘기가 망토 속으로 동전을 감췄다")
            return
        if self.blessing_menu:
            if key == "1":
                self.buy_blessing()
            elif key in ("2", "escape", self.controls["interact"]):
                self.blessing_menu = False
                self.say("위인의 혼이 다시 안개 속으로 사라진다")
            elif key == "m":
                self.settings_open = True
                self.settings_selection = 0
                self.keys.clear()
            return
        if key == "escape":
            self.root.attributes("-fullscreen", False)
            return
        if key == "r" and (self.game_over or self.finished):
            self.chapter, self.phase, self.skills = 0, 0, []
            self.wave, self.round_number = 1, 1
            self.max_hp = 200
            self.hp, self.game_over, self.finished = self.max_hp, False, False
            self.gold = 0
            self.staff_owned = False
            self.damage_bonus = self.attack_speed_bonus = 0.0
            self.stat_purchases = {"health": 0, "damage": 0, "attack_speed": 0}
            self.attack_combo_count = 0
            self.attack_last_frame = None
            self.player_damage_multiplier = 1
            self.blessing = None
            self.blessing_damage_bonus = self.blessing_move_bonus = 0.0
            self.blessing_hp_bonus = 0
            self.blessing_cd = 0
            self.archimedes_ship_active = False
            self.new_encounter()
            return

        if key == self.controls["interact"]:
            if self.midrun_shop_active and abs(self.player["x"] - SHOP_BIRD_X) < 115:
                self.shop_bird_menu = True
                self.say(f"비둘기 상점 · 1 완전 회복 50 G  ·  2 가호 소환 {SHOP_BLESSING_BRIBE} G")
                return
            if (self.round_clear and self.bird_x is not None
                    and abs(self.player["x"] - self.bird_x) < 86):
                self.bird_menu = True
                self.say("비둘기와 대화 · 1 체력  2 공격력  3 공격속도  5 회복 물약")
                return
            if self.try_open_blessing():
                return
            if self.midrun_shop_active and abs(self.player["x"] - NEWTON_STALL_X) < 150:
                self.buy_newton_staff()
                return
            if self.midrun_shop_active and not self.shop_exit_open and abs(self.player["x"] - SHOP_LEVER_X) < 100:
                self.open_midrun_shop_exit()
                return
            if self.in_shop and abs(self.player["x"] - 1080) < 100:
                self.leave_shop()
                return
            if self.round_clear and self.exit_door_x is not None and abs(self.player["x"] - self.exit_door_x) < 100:
                self.advance_from_door()
                return

        if key == self.controls["jump"] and not self.game_over and not self.finished and not self.transition:
            if self.action_down("drop") and self.player["grounded"]:
                self.player["drop"] = 14
                self.player["vy"] = 2.5
                self.player["grounded"] = False
            elif self.player["grounded"] or self.player["jumps_used"] < 2:
                was_grounded = self.player["grounded"]
                jump_boost = 1.16 if self.staff_owned else 1.0
                self.player["vy"] = (-18.6 if was_grounded else -17.2) * jump_boost
                self.player["grounded"] = False
                self.player["jumps_used"] = 1 if was_grounded else self.player["jumps_used"] + 1
                if not was_grounded:
                    self.player_action, self.player_action_until = "double_jump", self.frame + 14
                    self.effects.append(["double_jump", self.player["x"] + PLAYER_W / 2,
                                         self.player["y"] + PLAYER_H, 8])
        elif key == self.controls["dash"]:
            self.dash()
        elif key == self.controls["parry"]:
            self.parry()
        elif key == self.controls["attack"]:
            self.sword()
        elif key == self.controls["ranged"]:
            self.shoot_gun()
        elif key == self.controls["shop_staff"] and self.midrun_shop_active:
            if abs(self.player["x"] - SHOP_BIRD_X) < 115:
                self.summon_shop_blessing()
            else:
                self.buy_newton_staff()
        elif key == self.controls["blessing"]:
            self.use_blessing()
        else:
            for index, action in enumerate(("skill_q", "skill_w", "skill_e")):
                if key == self.controls[action]:
                    self.use_skill(index)
                    break

    def handle_settings_key(self, key):
        if key in ("m", "escape"):
            self.settings_open = False
            self.rebinding_action = None
            self.keys.clear()
            return
        row_count = len(CONTROL_ORDER) + 3
        if key == "up":
            self.settings_selection = (self.settings_selection - 1) % row_count
        elif key == "down":
            self.settings_selection = (self.settings_selection + 1) % row_count
        elif self.settings_selection == len(CONTROL_ORDER) + 1 and key in ("left", "right"):
            self.music_volume = round(max(0.0, min(1.0,
                self.music_volume + (.05 if key == "right" else -.05))), 2)
            self.restart_music()
        elif key in ("return", "space"):
            if self.settings_selection < len(CONTROL_ORDER):
                self.rebinding_action = CONTROL_ORDER[self.settings_selection]
            elif self.settings_selection == len(CONTROL_ORDER):
                self.toggle_music()
            elif self.settings_selection == len(CONTROL_ORDER) + 1:
                self.music_volume = round(min(1.0, self.music_volume + .05), 2)
                self.restart_music()
            else:
                self.controls = dict(DEFAULT_CONTROLS)
                self.keys.clear()
                self.say("키배치를 원래대로 초기화했습니다")

    def assign_control(self, action, key):
        if key in ("m", "escape", "f11", "shift_l", "shift_r", "control_l", "control_r",
                   "alt_l", "alt_r", "meta_l", "meta_r"):
            self.say("M, ESC, F11과 보조키는 조작키로 지정할 수 없습니다")
            return
        old_key = self.controls[action]
        for other, other_key in self.controls.items():
            if other != action and other_key == key:
                self.controls[other] = old_key
                break
        self.controls[action] = key
        label = CONTROL_LABELS[action]
        self.rebinding_action = None
        self.keys.clear()
        self.say(f"{label} 키를 {self.key_label(key)}로 변경했습니다")

    @staticmethod
    def key_label(key):
        return {"space": "SPACE", "left": "←", "right": "→", "up": "↑", "down": "↓",
                "return": "ENTER"}.get(key, key.upper())

    def draw_settings(self):
        c = self.canvas
        c.create_rectangle(0, 0, self.w, self.h, fill="#070a12", stipple="gray50", outline="")
        row_h = 21
        row_count = len(CONTROL_ORDER) + 3
        panel_h = 106 + row_h * row_count
        panel_w = min(650, self.w - 32)
        left = (self.w - panel_w) / 2
        top = max(10, (self.h - panel_h) / 2)
        c.create_rectangle(left, top, left + panel_w, top + panel_h,
                           fill="#182332", outline="#e5c779", width=3)
        c.create_text(self.w / 2, top + 22, text="설정 · 게임 일시정지",
                      fill="#ffe4a0", font=("TkDefaultFont", 17, "bold"))
        c.create_text(self.w / 2, top + 46, text="M 또는 ESC로 닫기 · ↑↓ 선택 · ENTER 변경",
                      fill="#c8c4bb", font=("TkDefaultFont", 9, "bold"))
        rows_top = top + 62
        for index, action in enumerate(CONTROL_ORDER):
            row_y = rows_top + row_h * index
            if index == self.settings_selection:
                c.create_rectangle(left + 12, row_y - 1, left + panel_w - 12,
                                   row_y + row_h - 2, fill="#344050", outline="#d0ad62")
            c.create_text(left + 26, row_y + 9, anchor="w", text=CONTROL_LABELS[action],
                          fill="#f0eadb", font=("TkDefaultFont", 10))
            value = "누를 키 입력…" if self.rebinding_action == action else self.key_label(self.controls[action])
            c.create_text(left + panel_w - 26, row_y + 9, anchor="e", text=value,
                          fill="#ffe08a" if self.rebinding_action == action else "#a9d9d4",
                          font=("TkDefaultFont", 10, "bold"))
        extra = len(CONTROL_ORDER)
        row_y = rows_top + row_h * extra
        if self.settings_selection == extra:
            c.create_rectangle(left + 12, row_y - 1, left + panel_w - 12,
                               row_y + row_h - 2, fill="#344050", outline="#d0ad62")
        c.create_text(left + 26, row_y + 9, anchor="w", text="배경음악",
                      fill="#f0eadb", font=("TkDefaultFont", 10))
        c.create_text(left + panel_w - 26, row_y + 9, anchor="e",
                      text="켜짐" if self.music_enabled else "꺼짐",
                      fill="#a9d9d4", font=("TkDefaultFont", 10, "bold"))
        row_y = rows_top + row_h * (extra + 1)
        if self.settings_selection == extra + 1:
            c.create_rectangle(left + 12, row_y - 1, left + panel_w - 12,
                               row_y + row_h - 2, fill="#344050", outline="#d0ad62")
        c.create_text(left + 26, row_y + 9, anchor="w", text="음악 음량 · ← → 조절",
                      fill="#f0eadb", font=("TkDefaultFont", 10))
        bar_left, bar_right = left + panel_w - 165, left + panel_w - 54
        c.create_rectangle(bar_left, row_y + 4, bar_right, row_y + 15,
                           fill="#302d3b", outline="#796c6b")
        c.create_rectangle(bar_left + 2, row_y + 6,
                           bar_left + 2 + (bar_right - bar_left - 4) * self.music_volume,
                           row_y + 13, fill="#e7c779", outline="")
        c.create_text(left + panel_w - 24, row_y + 9, anchor="e",
                      text=f"{round(self.music_volume * 100)}%",
                      fill="#a9d9d4", font=("TkDefaultFont", 9, "bold"))
        row_y = rows_top + row_h * (extra + 2)
        if self.settings_selection == extra + 2:
            c.create_rectangle(left + 12, row_y - 1, left + panel_w - 12,
                               row_y + row_h - 2, fill="#493238", outline="#e28b79")
        c.create_text(left + 26, row_y + 9, anchor="w", text="키배치 초기화 · 원래 배치로 복원",
                      fill="#f0eadb", font=("TkDefaultFont", 10))
        footer = "M / ESC 설정 닫기 · F11 전체화면"
        if self.rebinding_action is not None:
            footer = f"{CONTROL_LABELS[self.rebinding_action]}에 사용할 키를 누르세요 · 취소: ESC"
        c.create_text(self.w / 2, top + panel_h - 13, text=footer,
                      fill="#e8d9b4", font=("TkDefaultFont", 9, "bold"))

    def draw_blessing_menu(self):
        room = self.blessing_offer_room
        event = self.blessing_events.get(room)
        if not event:
            return
        spec = BLESSINGS[CHAPTER_BLESSINGS[event["chapter"]]]
        cost = self.blessing_cost()
        c = self.canvas
        left, top = self.w / 2 - 260, self.h / 2 - 100
        c.create_rectangle(0, 0, self.w, self.h, fill="#070a12", stipple="gray50", outline="")
        c.create_rectangle(left, top, left + 520, top + 200,
                           fill="#1c2131", outline="#e4c979", width=3)
        c.create_text(self.w / 2, top + 28, text=f"{spec['figure']}의 가호",
                      fill="#ffe5a0", font=("TkDefaultFont", 18, "bold"))
        c.create_text(self.w / 2, top + 67,
                      text=f"{self.key_label(self.controls['blessing'])} 기술 · {spec['skill']}    ·    대가 {cost} G",
                      fill="#f1ead9", font=("TkDefaultFont", 12, "bold"))
        benefit = ("공격력 +12%" if event["chapter"] == 0 else
                   "이동 속도 +15%" if event["chapter"] == 1 else "최대 체력 +150")
        c.create_text(self.w / 2, top + 96, text=f"가호 효과 · {benefit}",
                      fill="#a9d9d4", font=("TkDefaultFont", 11, "bold"))
        current = "없음" if self.blessing is None else BLESSINGS[self.blessing]["figure"]
        c.create_text(self.w / 2, top + 124, text=f"현재 가호 · {current}  →  새 가호로 변경 가능",
                      fill="#d6c6a4", font=("TkDefaultFont", 10))
        c.create_text(self.w / 2, top + 166,
                      text="1 받기/변경      2 나중에      M 설정",
                      fill="#fff0c9", font=("TkDefaultFont", 11, "bold"))

    def draw_stats(self):
        c = self.canvas
        panel_w, panel_h = min(700, self.w - 28), min(466, self.h - 24)
        left, top = (self.w - panel_w) / 2, (self.h - panel_h) / 2
        c.create_rectangle(0, 0, self.w, self.h, fill="#070a12", stipple="gray50", outline="")
        c.create_rectangle(left, top, left + panel_w, top + panel_h,
                           fill="#182332", outline="#e5c779", width=3)
        c.create_text(self.w / 2, top + 23, text="전투 기록 · 현재 장비와 능력치",
                      fill="#ffe4a0", font=("TkDefaultFont", 17, "bold"))
        c.create_text(self.w / 2, top + 46,
                      text=f"{self.key_label(self.controls['stats'])} 또는 ESC 닫기 · M 설정",
                      fill="#c8c4bb", font=("TkDefaultFont", 9, "bold"))

        inner_left, inner_right = left + 16, left + panel_w - 16
        weapon_top = top + 61
        c.create_rectangle(inner_left, weapon_top, inner_right, weapon_top + 104,
                           fill="#222d3b", outline="#9c8863", width=1)
        weapon_name = "뉴턴의 지팡이" if self.staff_owned else "검과 압축총"
        c.create_text(inner_left + 14, weapon_top + 16, anchor="w",
                      text=f"무기 · {weapon_name}", fill="#ffe6a5",
                      font=("TkDefaultFont", 12, "bold"))
        if self.staff_owned:
            weapon_lines = (
                f"{self.key_label(self.controls['attack'])} 기본 공격 · 가장 가까운 적을 자동 조준해 범위 중력 강타",
                f"{self.key_label(self.controls['ranged'])} 기술 · 가장 먼 적에게 운석 낙하 · 쿨타임 5초 · 점프 높이 +16%",
            )
        else:
            weapon_lines = (
                f"{self.key_label(self.controls['attack'])} 기본 공격 · 검을 휘둘러 전방을 베기",
                f"{self.key_label(self.controls['ranged'])} 원거리 공격 · 상태 효과 없는 직선 압축탄 · 쿨타임 5초",
            )
        for index, line in enumerate(weapon_lines):
            c.create_text(inner_left + 14, weapon_top + 43 + index * 23, anchor="w",
                          text=line, fill="#e8e2d5", font=("TkDefaultFont", 10))

        boon_top = weapon_top + 112
        c.create_rectangle(inner_left, boon_top, inner_right, boon_top + 102,
                           fill="#29263b", outline="#9e8bc4", width=1)
        if self.blessing is None:
            boon_title = "가호 · 보유하지 않음"
            boon_lines = (
                "안전 상점에서만 나타나는 위인에게 동전을 내고 가호를 받을 수 있습니다.",
                f"가호 기술 키 · {self.key_label(self.controls['blessing'])}",
            )
        else:
            spec = BLESSINGS[self.blessing]
            boon_title = f"가호 · {spec['figure']} · {spec['skill']}"
            boon_descriptions = {
                "archimedes": ("전방에 지렛대 파동을 일으켜 적을 띄웁니다.", "공격력 +12%"),
                "galileo": ("관성을 실은 대쉬 참격으로 전방의 적을 벱니다.", "이동 속도 +15%"),
                "newton": ("중력장으로 주변 적을 끌어당겨 강타합니다.", "최대 체력 +150"),
            }
            skill_description, stat_description = boon_descriptions[self.blessing]
            remaining = max(0, self.blessing_cd - self.frame)
            cooldown_text = "준비" if remaining == 0 else f"재사용까지 {remaining / 60:.1f}초"
            boon_lines = (
                f"{self.key_label(self.controls['blessing'])} 기술 · {skill_description}",
                f"가호 능력치 · {stat_description}   ·   기술 {cooldown_text}",
            )
        c.create_text(inner_left + 14, boon_top + 16, anchor="w", text=boon_title,
                      fill="#e8d9ff", font=("TkDefaultFont", 12, "bold"))
        for index, line in enumerate(boon_lines):
            c.create_text(inner_left + 14, boon_top + 44 + index * 24, anchor="w",
                          text=line, fill="#e8e2f0", font=("TkDefaultFont", 10))

        stats_top = boon_top + 110
        c.create_rectangle(inner_left, stats_top, inner_right, top + panel_h - 29,
                           fill="#202c32", outline="#77aaa1", width=1)
        attack_interval = max(6, int((32 if self.staff_owned else 19)
                                     * (1 - self.attack_speed_bonus)))
        stats = (
            f"체력  {self.hp:,} / {self.max_hp:,}       보유 동전  {self.gold:,} G",
            f"공격력  ×{self.player_damage_multiplier + self.damage_bonus + self.blessing_damage_bonus:.2f}"
            f"   · 구매 강화 +{self.damage_bonus:.0%}   · 가호 +{self.blessing_damage_bonus:.0%}",
            f"공격속도  +{self.attack_speed_bonus:.0%}   · 공격 간격 약 {attack_interval / 60:.2f}초",
            f"가호 이동 보너스  +{self.blessing_move_bonus:.0%}   · 점프 보너스  {'+16%' if self.staff_owned else '없음'}",
            f"강화 횟수  체력 {self.stat_purchases.get('health', 0)}   · 공격력 {self.stat_purchases.get('damage', 0)}"
            f"   · 공격속도 {self.stat_purchases.get('attack_speed', 0)}",
        )
        for index, line in enumerate(stats):
            c.create_text(inner_left + 14, stats_top + 17 + index * 24, anchor="w",
                          text=line, fill="#e5eee8", font=("TkDefaultFont", 10, "bold" if index == 0 else "normal"))

    def key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def say(self, text):
        self.notice = text
        self.notice_until = self.frame + 180

    def cooldown_frames(self, frames):
        return max(1, int(frames))

    def attack_cooldown_frames(self, frames):
        return max(6, int(frames * (1 - self.attack_speed_bonus)))

    def stat_cost(self, stat):
        purchase_count = self.stat_purchases.get(stat, 0)
        # Prices rise gently per purchase, with a larger step every fifth stat level.
        base_cost = {"health": 25, "damage": 40, "attack_speed": 40}[stat]
        return base_cost + purchase_count * 5 + (purchase_count // 5) * 25

    def buy_stat(self, stat):
        costs = {"health": "체력", "damage": "공격력", "attack_speed": "공격속도"}
        if stat == "attack_speed" and self.attack_speed_bonus >= .55:
            self.say("공격속도가 이미 최대치입니다")
            return
        cost = self.stat_cost(stat)
        if self.gold < cost:
            self.say(f"동전이 부족합니다 · {costs[stat]} 강화에 {cost} G 필요")
            return
        self.gold -= cost
        self.stat_purchases[stat] = self.stat_purchases.get(stat, 0) + 1
        if stat == "health":
            self.max_hp += 100
            self.hp = min(self.max_hp, self.hp + 100)
            amount = 100
            self.effects.append(["heal", self.player["x"] + PLAYER_W / 2,
                                 self.player["y"] + PLAYER_H / 2, 42, amount])
            detail = "최대 체력 +100"
        elif stat == "damage":
            self.damage_bonus += .05
            detail = f"공격력 +{self.damage_bonus:.0%}"
        else:
            self.attack_speed_bonus = min(.55, self.attack_speed_bonus + .05)
            detail = f"공격속도 +{self.attack_speed_bonus:.0%}"
        self.say(f"{costs[stat]} 강화 · {detail} · -{cost} G")

    def blessing_cost(self):
        return 60 + max(0, self.round_number - 1) * 5

    def try_open_blessing(self):
        room = self.room_wave_index
        event = self.blessing_events.get(room)
        if event and event.get("shop") and not self.midrun_shop_active:
            return False
        if not event or event["used"] or abs(self.player["x"] - event["x"]) >= 112:
            return False
        self.blessing_offer_room = room
        self.blessing_menu = True
        figure = BLESSINGS[CHAPTER_BLESSINGS[event["chapter"]]]["figure"]
        self.say(f"{figure}의 가호 · 1번으로 {self.blessing_cost()} G에 받거나 변경")
        return True

    def apply_blessing(self, blessing_id):
        self.max_hp = max(1, self.max_hp - self.blessing_hp_bonus)
        self.hp = min(self.hp, self.max_hp)
        spec = BLESSINGS[blessing_id]
        self.blessing = blessing_id
        self.blessing_damage_bonus = spec["damage"]
        self.blessing_move_bonus = spec["move"]
        self.blessing_hp_bonus = spec["hp"]
        self.max_hp += self.blessing_hp_bonus
        self.hp = min(self.max_hp, self.hp + self.blessing_hp_bonus)
        self.blessing_cd = 0

    def buy_blessing(self):
        room = self.blessing_offer_room
        event = self.blessing_events.get(room)
        if not event or event["used"]:
            self.blessing_menu = False
            return
        blessing_id = CHAPTER_BLESSINGS[event["chapter"]]
        spec = BLESSINGS[blessing_id]
        if self.blessing == blessing_id:
            event["used"] = True
            self.blessing_menu = False
            self.say(f"이미 {spec['figure']}의 가호를 받고 있습니다")
            return
        cost = self.blessing_cost()
        if self.gold < cost:
            self.say(f"동전이 부족합니다 · 가호에 {cost} G 필요")
            return
        self.gold -= cost
        self.apply_blessing(blessing_id)
        event["used"] = True
        self.blessing_menu = False
        self.say(f"{spec['figure']}의 가호 · {self.key_label(self.controls['blessing'])} {spec['skill']} · -{cost} G")

    def summon_shop_blessing(self):
        if not self.midrun_shop_active or self.shop_room_index is None:
            return
        event = self.blessing_events.get(self.shop_room_index)
        if event and not event["used"]:
            self.say("이미 상점에 위인의 기운이 나타나 있습니다")
            self.shop_bird_menu = False
            return
        if self.blessing == CHAPTER_BLESSINGS[self.chapter]:
            self.say("이미 이 시대의 가호를 받고 있습니다")
            self.shop_bird_menu = False
            return
        if self.gold < SHOP_BLESSING_BRIBE:
            self.say(f"동전이 부족합니다 · 가호를 부르려면 {SHOP_BLESSING_BRIBE} G 필요")
            return
        self.gold -= SHOP_BLESSING_BRIBE
        self.blessing_events[self.shop_room_index] = {
            "x": float(SHOP_BIRD_X + 145),
            "chapter": self.chapter,
            "used": False,
            "clear_offer_shown": False,
            "offer_until": 0,
            "shop": True,
        }
        self.shop_bird_menu = False
        figure = BLESSINGS[CHAPTER_BLESSINGS[self.chapter]]["figure"]
        self.say(f"비둘기에게 500 G를 건넸다 · {figure}의 가호가 상점에 나타났다")

    def use_blessing(self):
        if self.blessing is None:
            self.say("아직 가호가 없습니다 · 안전 상점에서 위인의 기운을 찾아보세요")
            return
        if self.frame < self.blessing_cd or self.game_over or self.finished or self.transition:
            return
        p = self.player
        px, py = p["x"] + PLAYER_W / 2, p["y"] + PLAYER_H / 2
        if self.blessing == "archimedes":
            self.player_action, self.player_action_until = "lever", self.frame + 24
            for enemy in self.enemies:
                if enemy["hp"] > 0 and self.in_front(enemy, 220, 125):
                    self.damage_enemy(enemy, 105 if enemy["rank"] != "boss" else 72)
                    enemy["vy"] = -12
                    enemy["hit"] = 12
            self.effects.append(["lever", px + p["face"] * 90, py - 5, 22])
            cooldown = 300
        elif self.blessing == "galileo":
            direction = p["face"]
            old_x = p["x"]
            p["dash_dir"] = direction
            p["dash_vx"] = direction * 176 / 10
            p["dash_frames"] = 10
            self.dash_until = self.frame + 12
            self.player_action, self.player_action_until = "momentum", self.frame + 22
            for enemy in self.enemies:
                if enemy["hp"] > 0 and self.in_front(enemy, 230, 125):
                    self.damage_enemy(enemy, 92 if enemy["rank"] != "boss" else 62)
                    enemy["vy"] = min(enemy["vy"], -4)
            self.effects.append(["dash", old_x + direction * 176, py, 16, direction])
            cooldown = 330
        else:
            radius = 230
            for enemy in self.enemies:
                if enemy["hp"] <= 0:
                    continue
                ex, ey = enemy["x"] + enemy["w"] / 2, enemy["y"] + enemy["h"] / 2
                distance = math.hypot(ex - px, ey - py)
                if distance <= radius:
                    enemy["x"] += (px - ex) * .34
                    enemy["y"] += (py - ey) * .24
                    self.damage_enemy(enemy, 82 if enemy["rank"] != "boss" else 58)
                    enemy["vy"] = min(enemy["vy"], -5)
            self.effects.append(["gravity", px, py, 30])
            self.effects.append(["gravity_slam", px, py, 22, radius])
            self.player_action, self.player_action_until = "gravity", self.frame + 26
            cooldown = 360
        self.blessing_cd = self.frame + cooldown
        self.say(f"{BLESSINGS[self.blessing]['skill']} · 가호 발동")

    def buy_newton_staff(self):
        if not self.midrun_shop_active:
            return
        if abs(self.player["x"] - NEWTON_STALL_X) >= 150:
            self.say(f"가판대에 가까이 가서 {self.key_label(self.controls['shop_staff'])} 또는 {self.key_label(self.controls['interact'])}를 누르세요")
            return
        if self.staff_owned:
            self.say("뉴턴의 지팡이를 이미 가지고 있습니다")
            return
        cost = 100
        if self.gold < cost:
            self.say(f"동전이 부족합니다 · 뉴턴의 지팡이는 {cost} G")
            return
        self.gold -= cost
        self.staff_owned = True
        self.say(f"뉴턴의 지팡이를 장착했습니다 · {self.key_label(self.controls['attack'])} 중력 강타 · {self.key_label(self.controls['ranged'])} 운석 · 점프력 상승")

    def buy_full_heal(self):
        cost = 50
        if self.hp >= self.max_hp:
            self.say("체력이 이미 최대치입니다")
            return
        if self.gold < cost:
            self.say(f"동전이 부족합니다 · 완전 회복은 {cost} G")
            return
        healed = self.max_hp - self.hp
        self.gold -= cost
        self.hp = self.max_hp
        self.effects.append(["heal", self.player["x"] + PLAYER_W / 2,
                             self.player["y"] + PLAYER_H / 2, 42, healed])
        self.say(f"비둘기의 치유 · 체력 완전 회복 · -{cost} G")

    def buy_healing_potion(self):
        cost, restore = 25, 40
        if self.hp >= self.max_hp:
            self.say("체력이 가득 차 있어 물약을 살 필요가 없습니다")
            return
        if self.gold < cost:
            self.say(f"동전이 부족합니다 · 회복 물약은 {cost} G")
            return
        self.gold -= cost
        healed = min(restore, self.max_hp - self.hp)
        self.hp += healed
        self.effects.append(["heal", self.player["x"] + PLAYER_W / 2,
                             self.player["y"] + PLAYER_H / 2, 42, healed])
        self.say(f"회복 물약 사용 · 체력 +{healed} · -{cost} G")

    def damage_enemy(self, enemy, amount):
        amount = int(amount * (self.player_damage_multiplier + self.damage_bonus
                               + self.blessing_damage_bonus))
        was_alive = enemy["hp"] > 0
        enemy["hp"] -= amount
        enemy["hit"] = 9
        if enemy["rank"] != "dummy" and enemy.get("state") in ("notice", "warning", "locked"):
            player_x = self.player["x"] + PLAYER_W / 2
            enemy_x = enemy["x"] + enemy["w"] / 2
            away = -1 if player_x >= enemy_x else 1
            enemy["state"], enemy["action"], enemy["timer"] = "stagger", "", 12
            enemy["stagger_delay"] = 6
            enemy["stagger_steps"] = 6
            enemy["stagger_vx"] = away * 1.2
        self.shake_strength = max(self.shake_strength, 4 if amount >= 60 else 2.5)
        self.shake_until = max(self.shake_until, self.frame + 8)
        self.effects.append(["impact", enemy["x"] + enemy["w"] / 2, enemy["y"] + enemy["h"] / 2, 12])
        if enemy["rank"] == "dummy":
            self.training_damage += amount
            self.effects.append(["damage_text", enemy["x"] + enemy["w"] / 2,
                                 enemy["y"] + 8, 48, amount])
        if was_alive and enemy["hp"] <= 0 and enemy["rank"] != "dummy":
            base_reward = (random.randint(55, 75) if enemy["rank"] == "boss"
                           else random.randint(24, 34) if enemy["rank"] == "scholar"
                           else random.randint(7, 12))
            reward = int(round(base_reward * (1 + max(0, self.round_number - 1) * .05)))
            self.coin_drops.append({"x": enemy["x"] + enemy["w"] / 2,
                                    "y": enemy["y"] + enemy["h"] * .65,
                                    "vy": -4.0, "value": reward, "age": 0})
        if was_alive and enemy["hp"] <= 0 and enemy["rank"] == "mob" and self.hp < self.max_hp:
            if random.random() < MOB_HEAL_CHANCE:
                healed = min(MOB_HEAL_AMOUNT, self.max_hp - self.hp)
                self.hp += healed
                self.effects.append(["heal", self.player["x"] + PLAYER_W / 2,
                                     self.player["y"] + PLAYER_H / 2, 42, healed])
        if (enemy["rank"] == "boss" and self.chapter == 0 and enemy.get("boss_phase") == "normal"
                and 0 < enemy["hp"] <= enemy["maxhp"] * .5):
            enemy["boss_phase"] = "falling"
            enemy["state"], enemy["timer"] = "falling", 42
            enemy["fall_y"] = enemy["y"]
            self.say("아르키메데스가 바닥 아래로 추락한다!")

    def enter_shop(self):
        self.in_shop = True
        self.round_clear = False
        self.room_waves = []
        self.spawn_queue.clear()
        self.waves_complete = True
        self.room_wave_started = False
        self.gate_obstacle = None
        self.static_obstacles = []
        self.pits = []
        self.tnt_crates = []
        self.exit_door_x = None
        self.transition = 0
        self.platforms = []
        self.obstacles = []
        self.enemy_shots.clear()
        self.spawn_queue.clear()
        self.player_shots.clear()
        self.meteors.clear()
        self.effects.clear()
        self.training_damage = 0
        self.player.update(pit_id=None, pit_damage_at=self.frame + 60)
        self.player.update(x=140.0, y=float(self.ground - PLAYER_H), vx=0, vy=0, face=1, grounded=True, drop=0, jumps_used=0)
        self.player.update(knockback_vx=0.0, knockback_frames=0, dash_vx=0.0, dash_frames=0, dash_dir=1)
        self.enemies = [{"kind": "훈련용 허수아비", "rank": "dummy", "x": 520.0,
                         "y": float(self.ground - 72), "w": 42, "h": 72,
                         "hp": 999999, "maxhp": 999999, "vy": 0.0,
                         "grounded": True, "drop": 0, "jump_cd": 0, "face": -1,
                         "state": "idle", "timer": 0, "action": "", "hit": 0}]
        self.say("준비 중인 상점  /  허수아비 공격 연습 가능")

    def leave_shop(self):
        if not self.in_shop:
            return
        self.collect_all_coins()
        self.in_shop = False
        if self.round_number >= 24:
            self.finished = True
            self.say("세 시대의 여정 완료")
            return
        self.round_number += 1
        self.new_encounter()

    def advance_from_door(self):
        if not self.round_clear:
            return
        self.collect_all_coins()
        self.round_clear = False
        if self.round_number % 4 == 0:
            if self.phase == 2:
                self.skills.append(self.chapter)
            self.enter_shop()
        else:
            self.round_number += 1
            self.new_encounter()

    def collect_all_coins(self):
        if not self.coin_drops:
            return 0
        amount = sum(coin["value"] for coin in self.coin_drops)
        self.gold += amount
        self.coin_drops.clear()
        self.effects.append(["coin", self.player["x"] + PLAYER_W / 2,
                             self.player["y"] + PLAYER_H / 2, 28, amount])
        return amount

    def update_coin_drops(self):
        remaining = []
        px = self.player["x"] + PLAYER_W / 2
        py = self.player["y"] + PLAYER_H / 2
        for coin in self.coin_drops:
            coin["age"] += 1
            coin["vy"] = min(10, coin["vy"] + .42)
            coin["y"] += coin["vy"]
            pit_id, pit = self.pit_at(coin["x"])
            floor = pit["bottom"] - 9 if pit_id is not None else self.ground - 9
            if coin["y"] >= floor:
                coin["y"], coin["vy"] = floor, 0
            if abs(coin["x"] - px) < 36 and abs(coin["y"] - py) < 70:
                self.gold += coin["value"]
                self.effects.append(["coin", coin["x"], coin["y"], 28, coin["value"]])
            else:
                remaining.append(coin)
        self.coin_drops = remaining

    def dash(self):
        if self.frame < self.dash_cd or self.game_over or self.finished or self.transition:
            return
        direction = self.player["face"]
        if self.action_down("move_left"):
            direction = -1
        elif self.action_down("move_right"):
            direction = 1
        p = self.player
        old_x = p["x"]
        p["face"] = direction
        p["dash_dir"] = direction
        p["dash_vx"] = direction * 118 / 8
        p["dash_frames"] = 8
        self.player_action, self.player_action_until = "dash", self.frame + 10
        self.effects.append(["dash", old_x + direction * 118, p["y"] + PLAYER_H / 2, 12, direction])
        self.dash_until = self.frame + 10
        self.dash_cd = self.frame + self.cooldown_frames(24)

    def parry(self):
        if self.frame < self.parry_cd or self.game_over or self.finished or self.transition:
            return
        self.parry_until = self.frame + 30
        self.parry_cd = self.frame + self.cooldown_frames(120)
        self.effects.append(["parry", self.player["x"] + PLAYER_W / 2, self.player["y"] + PLAYER_H / 2, 12])

    def sword(self):
        if self.frame < self.attack_cd or self.game_over or self.finished or self.transition:
            return
        if self.staff_owned:
            self.attack_combo_count = 0
            self.attack_last_frame = None
            self.staff_basic_attack()
            return
        self.attack_until = self.frame + 20
        if self.attack_last_frame is None or self.frame - self.attack_last_frame > 60:
            self.attack_combo_count = 1
        else:
            self.attack_combo_count += 1
        self.attack_last_frame = self.frame
        cooldown = self.attack_cooldown_frames(19)
        if self.attack_combo_count >= 4:
            cooldown += 30
            self.attack_combo_count = 0
        self.attack_cd = self.frame + cooldown
        self.player_action, self.player_action_until = "slash", self.frame + 20
        self.swing_hits.clear()
        self.effects.append(["slash", self.player["x"] + PLAYER_W / 2,
                             self.player["y"] + PLAYER_H * .5, 15,
                             self.player["face"], 150])

    def staff_basic_attack(self):
        p = self.player
        px, py = p["x"] + PLAYER_W / 2, p["y"] + PLAYER_H / 2
        targets = [enemy for enemy in self.enemies if enemy["hp"] > 0
                   and math.hypot(enemy["x"] + enemy["w"] / 2 - px,
                                  enemy["y"] + enemy["h"] / 2 - py) <= 780]
        if not targets:
            self.say("중력 공격 범위 안에 적이 없습니다")
            return
        target = min(targets, key=lambda enemy: math.hypot(
            enemy["x"] + enemy["w"] / 2 - px,
            enemy["y"] + enemy["h"] / 2 - py))
        tx = target["x"] + target["w"] / 2
        ty = target["y"] + target["h"] / 2
        p["face"] = 1 if tx >= px else -1
        self.attack_until = self.frame + 18
        self.attack_cd = self.frame + self.attack_cooldown_frames(32)
        self.player_action, self.player_action_until = "staff", self.frame + 24
        self.effects.append(["gravity", tx, ty, 30])
        self.effects.append(["gravity_slam", tx, ty, 20, 158])
        for enemy in self.enemies:
            if enemy["hp"] <= 0:
                continue
            ex = enemy["x"] + enemy["w"] / 2
            ey = enemy["y"] + enemy["h"] / 2
            if math.hypot(ex - tx, (ey - ty) * .82) <= 158:
                self.damage_enemy(enemy, 42 if enemy["rank"] != "boss" else 34)
                enemy["gravity_boost_until"] = self.frame + 18
                enemy["vy"] = min(TERMINAL_VELOCITY, enemy["vy"] + 7)
                enemy["hit"] = 10
        self.say("뉴턴의 지팡이 · 가장 가까운 적에게 중력 강타")

    def shoot_gun(self):
        if self.frame < self.gun_cd or self.game_over or self.finished or self.transition:
            return
        if self.staff_owned:
            self.cast_meteor()
            return
        p = self.player
        self.player_action, self.player_action_until = "gun", self.frame + 18
        self.gun_until = self.player_action_until
        self.gun_cd = self.frame + self.cooldown_frames(300)
        muzzle_x = p["x"] + (PLAYER_W if p["face"] > 0 else 0)
        muzzle_y = p["y"] + PLAYER_H * .52
        self.player_shots.append([muzzle_x, muzzle_y, p["face"] * 18, 0, 90, 68, "handcannon"])
        self.effects.append(["muzzle", muzzle_x + p["face"] * 8, muzzle_y, 10])

    def cast_meteor(self):
        targets = [enemy for enemy in self.enemies if enemy["hp"] > 0]
        if not targets:
            self.say("운석을 조준할 적이 없습니다")
            return
        px = self.player["x"] + PLAYER_W / 2
        py = self.player["y"] + PLAYER_H / 2
        target = max(targets, key=lambda enemy: math.hypot(
            enemy["x"] + enemy["w"] / 2 - px,
            enemy["y"] + enemy["h"] / 2 - py))
        tx = target["x"] + target["w"] / 2
        ty = target["y"] + target["h"] * .55
        duration = 48
        start_y = max(0, ty - 490)
        self.meteors.append({"x": tx, "target_y": ty, "start_y": start_y,
                             "y": start_y, "timer": duration,
                             "duration": duration, "radius": 190, "damage": 155})
        self.player_action, self.player_action_until = "meteor", self.frame + 24
        self.gun_cd = self.frame + self.cooldown_frames(300)
        self.say("뉴턴의 지팡이 · 가장 먼 적에게 운석 낙하")

    def update_meteors(self):
        remaining = []
        for meteor in self.meteors:
            meteor["timer"] -= 1
            progress = 1 - max(0, meteor["timer"]) / meteor["duration"]
            meteor["y"] = meteor["start_y"] + (meteor["target_y"] - meteor["start_y"]) * progress
            if meteor["timer"] > 0:
                remaining.append(meteor)
                continue
            x, y, radius = meteor["x"], meteor["target_y"], meteor["radius"]
            for enemy in self.enemies:
                if enemy["hp"] <= 0:
                    continue
                ex = enemy["x"] + enemy["w"] / 2
                ey = enemy["y"] + enemy["h"] / 2
                if math.hypot(ex - x, (ey - y) * .82) <= radius:
                    self.damage_enemy(enemy, meteor["damage"] if enemy["rank"] != "boss" else 125)
                    enemy["vy"] = min(enemy["vy"], -8)
                    enemy["hit"] = 16
            self.effects.append(["meteor_blast", x, y, 26, radius])
        self.meteors = remaining

    def use_skill(self, slot):
        if slot >= len(self.skills) or self.frame < self.skill_cd[slot] or self.game_over or self.finished:
            return
        p = self.player
        if slot == 0:
            self.player_action, self.player_action_until = "lever", self.frame + 24
            # Lever principle: a rising sword blow lifts nearby foes.
            for enemy in self.enemies:
                if self.in_front(enemy, 118, 105):
                    self.damage_enemy(enemy, 70 if enemy["rank"] == "boss" else 90)
                    enemy["vy"] = -11
                    enemy["hit"] = 12
            self.effects.append(["lever", p["x"] + p["face"] * 60, p["y"] + PLAYER_H * .38, 20])
            self.skill_cd[slot] = self.frame + self.cooldown_frames(180)
        elif slot == 1:
            self.player_action, self.player_action_until = "momentum", self.frame + 22
            # Galileo: a momentum-rich slash projectile follows a ballistic arc.
            self.player_shots.append([p["x"] + p["face"] * 30, p["y"] + PLAYER_H * .48, p["face"] * 12, -7, 90, 62])
            self.effects.append(["burst", p["x"] + p["face"] * 30, p["y"] + PLAYER_H * .48, 12])
            self.skill_cd[slot] = self.frame + self.cooldown_frames(210)
        else:
            self.player_action, self.player_action_until = "gravity", self.frame + 26
            # Newton: a gravity well pulls nearby targets into a sword slam.
            cx, cy = p["x"] + p["face"] * 70, p["y"] + PLAYER_H * .52
            for enemy in self.enemies:
                ex, ey = enemy["x"] + enemy["w"] / 2, enemy["y"] + enemy["h"] / 2
                if math.hypot(ex - cx, ey - cy) < 190:
                    enemy["x"] += (cx - ex) * .45
                    enemy["y"] += (cy - ey) * .35
                    self.damage_enemy(enemy, 110 if enemy["rank"] == "boss" else 130)
                    enemy["hit"] = 15
            self.effects.append(["gravity", cx, cy, 24])
            self.skill_cd[slot] = self.frame + self.cooldown_frames(240)

    def in_front(self, enemy, reach, vertical):
        p = self.player
        if p["face"] > 0:
            horizontal = enemy["x"] < p["x"] + PLAYER_W + reach and enemy["x"] + enemy["w"] > p["x"] + PLAYER_W * .2
        else:
            horizontal = enemy["x"] + enemy["w"] > p["x"] - reach and enemy["x"] < p["x"] + PLAYER_W * .8
        vertical_overlap = enemy["y"] < p["y"] + PLAYER_H + vertical and enemy["y"] + enemy["h"] > p["y"] - vertical
        return horizontal and vertical_overlap

    def hurt(self, damage):
        if self.game_over:
            return
        if self.frame < self.parry_until:
            self.shake_strength = max(self.shake_strength, 5)
            self.shake_until = max(self.shake_until, self.frame + 9)
            self.effects.append(["parry", self.player["x"] + PLAYER_W / 2, self.player["y"] + PLAYER_H / 2, 16])
            self.say("패링 성공!")
            return
        if self.frame < self.invulnerable or self.frame < self.dash_until:
            return
        self.hp = max(0, self.hp - damage)
        self.hitstop_until = max(self.hitstop_until, self.frame + 4)
        self.shake_strength = max(self.shake_strength, 4)
        self.shake_until = max(self.shake_until, self.frame + 8)
        self.invulnerable = self.frame + 55
        self.player["vy"] = -4
        self.effects.append(["hit", self.player["x"] + 16, self.player["y"] + PLAYER_H * .58, 14])
        if self.hp <= 0:
            self.game_over = True
            self.say("쓰러졌습니다  /  R 키로 처음부터 다시 시작")

    def update_player(self):
        p = self.player
        was_grounded = p["grounded"]
        gravity_slow = self.scholar_gravity_active()
        dx = int(self.action_down("move_right")) - int(self.action_down("move_left"))
        old_x = p["x"]
        old_y = p["y"]
        knockback_dx = 0.0
        if p.get("knockback_frames", 0) > 0:
            knockback_dx = p["knockback_vx"]
            p["knockback_frames"] -= 1
            if p["knockback_frames"] == 0:
                p["knockback_vx"] = 0.0
        dash_dx = 0.0
        dash_active = p.get("dash_frames", 0) > 0
        if dash_active:
            dash_dx = p["dash_vx"]
            p["dash_frames"] -= 1
            if p["dash_frames"] == 0:
                p["dash_vx"] = 0.0
        if dash_active:
            p["face"] = p.get("dash_dir", p["face"])
            p["x"] = max(0, min(WORLD - PLAYER_W, p["x"] + knockback_dx + dash_dx * (.68 if gravity_slow else 1)))
        elif dx:
            p["face"] = dx
            run_speed = ((6.2 if not p["grounded"] else 5.2)
                         * (1 + self.blessing_move_bonus) * (.58 if gravity_slow else 1))
            p["x"] = max(0, min(WORLD - PLAYER_W, p["x"] + dx * run_speed + knockback_dx + dash_dx))
        elif knockback_dx or dash_dx:
            p["x"] = max(0, min(WORLD - PLAYER_W, p["x"] + knockback_dx + dash_dx))
        # Once below the main floor, the pit's stone sides keep horizontal
        # movement inside the trench until a jump clears the floor height.
        pit_id = p.get("pit_id")
        if pit_id is not None and pit_id < len(self.pits) and p["y"] + PLAYER_H >= self.ground:
            pit = self.pits[pit_id]
            p["x"] = max(pit["left"] + 1,
                         min(pit["right"] - PLAYER_W - 1, p["x"]))
        self.resolve_horizontal_obstacles(p, old_x, p["y"], PLAYER_W, PLAYER_H)
        if dash_active and abs(p["x"] - old_x) > .1:
            self.effects.append(["after", old_x, p["y"], 7])
        elif dx and was_grounded and self.frame % 12 == 0:
            self.effects.append(["footstep", p["x"] + PLAYER_W / 2,
                                 p["y"] + PLAYER_H, 10, dx])
        old_bottom = p["y"] + PLAYER_H
        p["vy"] = min(TERMINAL_VELOCITY, p["vy"] + GRAVITY)
        fall_speed = p["vy"]
        p["y"] += p["vy"]
        p["grounded"] = False
        landing = None
        dropping = p["drop"] > 0
        if dropping:
            p["drop"] -= 1
        if not dropping and p["vy"] >= 0:
            for left, right, rise in self.platforms:
                py = self.ground - rise
                if p["x"] + PLAYER_W > left and p["x"] < right and old_bottom <= py <= p["y"] + PLAYER_H:
                    if landing is None or py < landing:
                        landing = py
        obstacle_landing = self.resolve_vertical_obstacles(p, old_y, PLAYER_W, PLAYER_H)
        if obstacle_landing is not None:
            landing = obstacle_landing if landing is None else min(landing, obstacle_landing)
        bottom = p["y"] + PLAYER_H
        if bottom < self.ground - 1:
            p["pit_id"] = None
            p["pit_damage_at"] = self.frame + 60
        elif p.get("pit_id") is None:
            pit_id, _pit = self.pit_at(p["x"] + PLAYER_W / 2)
            if pit_id is not None:
                p["pit_id"] = pit_id
                p["pit_damage_at"] = self.frame + 60

        pit_id = p.get("pit_id")
        if pit_id is not None and pit_id < len(self.pits):
            pit_floor = self.pits[pit_id]["bottom"]
            if old_bottom <= pit_floor <= bottom:
                landing = pit_floor if landing is None else min(landing, pit_floor)
        elif old_bottom <= self.ground <= bottom:
            landing = self.ground if landing is None else min(landing, self.ground)
        if landing is not None:
            p["y"], p["vy"], p["grounded"] = landing - PLAYER_H, 0, True
            p["jumps_used"] = 0
            if (not was_grounded and p.get("pit_id") is not None
                    and abs(landing - self.pits[p["pit_id"]]["bottom"]) < 1):
                p["pit_damage_at"] = self.frame + 60
            if not was_grounded and fall_speed > 7:
                self.effects.append(["landing", p["x"] + PLAYER_W / 2, landing, 16])
                self.player_action, self.player_action_until = "land", self.frame + 7
        p["vx"] = p["x"] - old_x

    def scholar_gravity_active(self):
        px = self.player["x"] + PLAYER_W / 2
        py = self.player["y"] + PLAYER_H / 2
        return any(enemy["rank"] == "scholar" and enemy["hp"] > 0
                   and enemy.get("state") != "stagger"
                   and abs(px - (enemy["x"] + enemy["w"] / 2)) < 250
                   and abs(py - (enemy["y"] + enemy["h"] / 2)) < 145
                   for enemy in self.enemies)

    def update_enemy_physics(self, enemy):
        was_grounded = enemy["grounded"]
        old_bottom = enemy["y"] + enemy["h"]
        pit_id = enemy.get("pit_id")
        if pit_id is not None and pit_id < len(self.pits) and old_bottom >= self.ground:
            pit = self.pits[pit_id]
            enemy["x"] = max(pit["left"] + 1,
                              min(pit["right"] - enemy["w"] - 1, enemy["x"]))
        gravity = GRAVITY * (3.2 if self.frame < enemy.get("gravity_boost_until", 0) else 1.0)
        enemy["vy"] = min(TERMINAL_VELOCITY, enemy["vy"] + gravity)
        fall_speed = enemy["vy"]
        enemy["y"] += enemy["vy"]
        enemy["grounded"] = False
        landing = None
        dropping = enemy["drop"] > 0
        if dropping:
            enemy["drop"] -= 1
        if not dropping and enemy["vy"] >= 0:
            for left, right, rise in self.platforms:
                py = self.ground - rise
                if enemy["x"] + enemy["w"] > left and enemy["x"] < right and old_bottom <= py <= enemy["y"] + enemy["h"]:
                    if landing is None or py < landing:
                        landing = py
        bottom = enemy["y"] + enemy["h"]
        if bottom < self.ground - 1:
            enemy["pit_id"] = None
        elif enemy.get("pit_id") is None:
            pit_id, _pit = self.pit_at(enemy["x"] + enemy["w"] / 2)
            if pit_id is not None:
                enemy["pit_id"] = pit_id
        pit_id = enemy.get("pit_id")
        if pit_id is not None and pit_id < len(self.pits):
            pit_floor = self.pits[pit_id]["bottom"]
            if old_bottom <= pit_floor <= bottom:
                landing = pit_floor if landing is None else min(landing, pit_floor)
        elif old_bottom <= self.ground <= bottom:
            landing = self.ground if landing is None else min(landing, self.ground)
        if landing is not None:
            enemy["y"], enemy["vy"], enemy["grounded"] = landing - enemy["h"], 0, True
            if not was_grounded and fall_speed > 8 and enemy["rank"] != "boss":
                self.effects.append(["landing", enemy["x"] + enemy["w"] / 2, landing, 12])

    def begin_warning(self, enemy, action, frames=35):
        is_gun_aim = action in ("crossbow", "fan", "intercept", "gunshot")
        is_ranged_mob = (enemy["rank"] == "mob" and enemy["kind"] in RANGED_MOBS
                         and is_gun_aim)
        if enemy["rank"] == "mob":
            # Ranged grunts telegraph for 0.7 seconds, aim for 0.3, then fire.
            # Melee grunts keep a short 0.45-second tell.
            enemy["state"], enemy["action"] = "notice", action
            tell_frames = 60 if is_ranged_mob else 27
            enemy["timer"] = 42 if is_ranged_mob else tell_frames
            enemy["telegraph_total"] = tell_frames
            enemy["telegraph_end_frame"] = self.frame + tell_frames
        else:
            if is_gun_aim:
                frames = 60
            enemy["state"], enemy["action"], enemy["timer"] = "warning", action, frames
            enemy["telegraph_total"] = frames + 60 if is_gun_aim else frames
            enemy["telegraph_end_frame"] = self.frame + enemy["telegraph_total"]
        if action in ("mob_swing", "scholar_swing"):
            enemy["attack_face"] = enemy.get("face", 1)
        enemy["target_x"] = self.player["x"] + PLAYER_W / 2
        enemy["target_y"] = self.player["y"] + PLAYER_H / 2
        if action == "catapult":
            player_x = self.player["x"] + PLAYER_W / 2
            boss_x = enemy["x"] + enemy["w"] / 2
            away_side = 1 if boss_x >= player_x else -1
            jump_distance = random.randint(520, 760)
            target = player_x + away_side * jump_distance
            if target < 120 or target > WORLD - 120:
                target = player_x - away_side * jump_distance
            enemy["target_x"] = max(120, min(WORLD - 120, target))
        elif is_gun_aim:
            enemy["target_x"], enemy["target_y"] = self.intercept_point(enemy)

    def warning_color(self, enemy):
        total = max(1, enemy.get("telegraph_total", enemy.get("timer", 1)))
        remaining = max(0, enemy.get("telegraph_end_frame", self.frame) - self.frame)
        progress = 1 - min(1.0, remaining / total)
        return self.color_mix("#f4d98e", "#ff302f", progress)

    def intercept_point(self, enemy, speed=16):
        """Estimate where a straight arrow can meet the player's current motion."""
        p = self.player
        origin_x = enemy["x"] + enemy["w"] / 2
        origin_y = enemy["y"] + enemy["h"] * .48
        player_x = p["x"] + PLAYER_W / 2
        player_y = p["y"] + PLAYER_H * .48
        player_vx = p.get("vx", 0.0)
        player_vy = p["vy"] if not p["grounded"] else 0.0
        flight = max(1.0, math.hypot(player_x - origin_x, player_y - origin_y) / speed)

        # Re-estimate flight time after leading the target. Airborne shots allow
        # for gravity but cap the vertical lead so landing does not over-predict.
        for _ in range(4):
            target_x = player_x + player_vx * flight
            vertical_lead = player_vy * flight
            if not p["grounded"]:
                vertical_lead += .5 * GRAVITY * flight * flight
            vertical_lead = max(-140, min(140, vertical_lead))
            target_y = player_y + vertical_lead
            flight = max(1.0, math.hypot(target_x - origin_x, target_y - origin_y) / speed)

        target_x = max(0.0, min(WORLD, player_x + player_vx * flight))
        vertical_lead = player_vy * flight
        if not p["grounded"]:
            vertical_lead += .5 * GRAVITY * flight * flight
        target_y = player_y + max(-140, min(140, vertical_lead))
        target_y = max(0.0, min(WORLD_H, target_y))
        return target_x, target_y

    def launch_player_knockback(self, distance, direction, frames, upward_speed=-9):
        """Move the player away over several frames so the camera can follow."""
        p = self.player
        p["knockback_vx"] = direction * distance / frames
        p["knockback_frames"] = frames
        p["vy"] = upward_speed

    def launch_enemy_attack(self, enemy):
        kind, rank = enemy["kind"], enemy["rank"]
        ex, ey = enemy["x"] + enemy["w"] / 2, enemy["y"] + enemy["h"] / 2
        p = self.player
        enemy["attack_pose_until"] = self.frame + 14
        if enemy["action"] == "charge":
            enemy["state"], enemy["timer"] = "charge", 22
            enemy["vx"] = enemy["face"] * (12 if rank == "mob" else 9)
        elif enemy["action"] == "wheel_roll":
            enemy["state"], enemy["timer"] = "wheel_roll", 38
            enemy["vx"] = enemy["face"] * 15
            enemy["wheel_hits"] = False
        elif enemy["action"] == "catapult":
            enemy["state"], enemy["timer"] = "catapult_flight", 90
            enemy["flight_total"] = 90
            enemy["flight_start_x"] = enemy["x"]
            enemy["flight_target_x"] = max(0, min(WORLD - enemy["w"], enemy["target_x"] - enemy["w"] / 2))
            enemy["next_reposition"] = self.frame + 900
        elif enemy["action"] == "catapult_rock":
            dx, dy = enemy["target_x"] - ex, enemy["target_y"] - ey
            angle = math.atan2(dy, dx)
            for offset in (-.2, 0, .2):
                a = angle + offset
                self.enemy_shots.append([ex, ey, math.cos(a) * 11, math.sin(a) * 11 - 2, 180, 26, "stone"])
            enemy["state"], enemy["timer"] = "cooldown", 125
        elif enemy["action"] in ("mob_swing", "scholar_swing"):
            swing_face = enemy.get("attack_face", enemy["face"])
            forward = (p["x"] + PLAYER_W / 2 - ex) * swing_face
            vertical = abs(p["y"] + PLAYER_H / 2 - ey)
            reach = 130 if enemy["action"] == "mob_swing" else 165
            vertical_limit = enemy["h"] * .42 if enemy["action"] == "mob_swing" else 92
            if -18 <= forward <= reach and vertical <= vertical_limit:
                before = self.hp
                self.hurt(18 if enemy["action"] == "mob_swing" else 27)
                if self.hp < before:
                    self.launch_player_knockback(72 if enemy["action"] == "mob_swing" else 86,
                                                 swing_face, 10, upward_speed=-4.5)
            self.effects.append(["slash", ex + swing_face * 25, ey - 4, 12, swing_face, reach])
            enemy["attack_pose_until"] = self.frame + 14
            enemy["state"], enemy["timer"] = "cooldown", 62 if enemy["action"] == "mob_swing" else 82
        elif enemy["action"] == "scholar_crush":
            tx, ty = enemy["target_x"], enemy["target_y"]
            if abs(p["x"] + PLAYER_W / 2 - tx) < 92 and abs(p["y"] + PLAYER_H / 2 - ty) < 82:
                before = self.hp
                self.hurt(36)
                if self.hp < before:
                    # Freeze 30 subsequent updates at 60 Hz (about 0.5 seconds).
                    self.hitstop_until = max(self.hitstop_until, self.frame + 31)
            self.effects.append(["gravity", tx, ty, 34])
            enemy["attack_pose_until"] = self.frame + 18
            enemy["state"], enemy["timer"] = "cooldown", 92
        elif enemy["action"] == "slam":
            tx, ty = enemy["target_x"], enemy["target_y"]
            vertical_limit = (enemy["h"] * .42
                             if rank == "mob" and kind in MELEE_MOBS else 105)
            if (abs(p["x"] + PLAYER_W / 2 - tx) < 76
                    and abs(p["y"] + PLAYER_H / 2 - ty) < vertical_limit):
                self.hurt(22)
            self.effects.append(["slam", tx, self.ground, 22])
            enemy["attack_pose_until"] = self.frame + 16
            enemy["state"], enemy["timer"] = "cooldown", 72
        elif enemy["action"] in ("crossbow", "fan", "intercept", "gunshot"):
            target_x = enemy.get("locked_target_x", enemy["target_x"])
            target_y = enemy.get("locked_target_y", enemy["target_y"])
            shot_x, shot_y = ex, enemy["y"] + enemy["h"] * .48
            dx, dy = target_x - shot_x, target_y - shot_y
            length = max(1, math.hypot(dx, dy))
            self.enemy_shots.append([shot_x, shot_y, dx / length * 22, dy / length * 22,
                                     100, 24, "bullet"])
            enemy["attack_pose_until"] = self.frame + 14
            enemy["state"], enemy["timer"] = "cooldown", 100
        elif enemy["action"] in ("column", "pressure"):
            tx = enemy["target_x"]
            self.enemy_shots.append([tx, 60, 0, 0, 30, 18, "column"])
            enemy["state"], enemy["timer"] = "cooldown", 75
        elif enemy["action"] == "lever":
            player_cx = p["x"] + PLAYER_W / 2
            vertical_offset = p["y"] + PLAYER_H / 2 - ey
            close = (abs(player_cx - ex) < (enemy["w"] / 2 + 85)
                     and -155 <= vertical_offset <= 235)
            if close:
                before = self.hp
                self.hurt(30 if rank == "boss" else 32)
                if self.hp < before:
                    knock_dir = 1 if player_cx >= ex else -1
                    # Three dash lengths (118px each), carried over time.
                    self.launch_player_knockback(118 * 3, knock_dir, 24)
            self.effects.append(["lever", ex + enemy["face"] * 145, ey, 22])
            enemy["state"], enemy["timer"] = "cooldown", 90
        elif enemy["action"] == "parabola":
            dx = enemy["target_x"] - ex
            dy = enemy["target_y"] - ey
            angle = math.atan2(dy, dx)
            for offset in ((-.23, 0, .23) if rank != "mob" else (0,)):
                a = angle + offset
                self.enemy_shots.append([ex, ey, math.cos(a) * 7, math.sin(a) * 7 - 2, 170, 16, "stone"])
            enemy["state"], enemy["timer"] = "cooldown", 82
        elif enemy["action"] == "orbit":
            for i in range(8):
                a = math.tau * i / 8
                self.enemy_shots.append([ex, ey, math.cos(a) * 5, math.sin(a) * 5, 140, 12, "stone"])
            enemy["state"], enemy["timer"] = "cooldown", 90
        elif enemy["action"] == "fall":
            tx = enemy["target_x"]
            self.enemy_shots.append([tx, 30, 0, 7, 100, 22, "weight"])
            enemy["state"], enemy["timer"] = "cooldown", 70
        elif enemy["action"] == "gravity":
            # Marked gravity field; the player can dash out before impact.
            tx, ty = enemy["target_x"], enemy["target_y"]
            self.effects.append(["warning", tx, ty, 30])
            enemy["state"], enemy["timer"] = "gravity_wait", 30
        else:
            dx, dy = p["x"] + PLAYER_W / 2 - ex, p["y"] + PLAYER_H / 2 - ey
            length = max(1, math.hypot(dx, dy))
            speed = 7 if rank == "mob" else 9
            self.enemy_shots.append([ex, ey, dx / length * speed, dy / length * speed, 150, 12 if rank == "mob" else 20, "stone"])
            enemy["state"], enemy["timer"] = "cooldown", 70 if rank == "mob" else 85

    def update_archimedes_boss(self, enemy, px, py, dx, dy, dist):
        """Archimedes' attack cycle and slow, staged buoyancy-ship entrance."""
        if enemy.get("boss_phase") == "falling":
            enemy["y"] += 17
            enemy["timer"] -= 1
            if enemy["timer"] <= 0:
                enemy["boss_phase"] = "submerged"
                enemy["state"], enemy["timer"] = "submerged", 100
                side = 1 if px < WORLD / 2 else -1
                enemy["x"] = max(80, min(WORLD - enemy["w"] - 80, px + side * 470 - enemy["w"] / 2))
                enemy["y"] = self.ground + 260
                self.say("수면 아래로 사라졌다…")
            return

        if enemy.get("boss_phase") == "submerged":
            enemy["y"] = self.ground + 260
            enemy["timer"] -= 1
            if enemy["timer"] <= 0:
                enemy["boss_phase"] = "rising"
                enemy["state"], enemy["timer"] = "rising", 96
                enemy["rise_start_y"] = self.ground + 260
                enemy["rise_target_y"] = self.ground - enemy["h"] - 7
                center_x = enemy["x"] + enemy["w"] / 2
                self.effects.append(["whale_breach", center_x, self.ground, 112, 1.0])
                self.effects.append(["whale_breach", center_x - 170, self.ground + 8, 84, .64])
                self.effects.append(["whale_breach", center_x + 170, self.ground + 8, 84, .64])
                self.say("수면 아래의 배가 거대한 물기둥과 함께 솟구친다!")
            return

        if enemy.get("boss_phase") == "rising":
            enemy["timer"] -= 1
            t = 1 - max(0, enemy["timer"]) / 96
            eased = t * t * (3 - 2 * t)
            bob = -math.sin(min(1.0, t * 1.12) * math.pi) * 18
            enemy["y"] = enemy["rise_start_y"] + (enemy["rise_target_y"] - enemy["rise_start_y"]) * eased + bob
            if enemy["timer"] <= 0:
                enemy["boss_phase"] = "ship"
                self.archimedes_ship_active = True
                enemy["y"] = enemy["rise_target_y"]
                enemy["state"], enemy["action"], enemy["timer"] = "idle", "", 100
                enemy["next_reposition"] = self.frame + 900
                for offset in (-210, -105, 0, 105, 210):
                    self.queue_enemy(random.choice(ERAS[0]["mobs"]), enemy["x"] + enemy["w"] / 2 + offset, "mob")
                self.spawn_next_at = min(self.spawn_next_at, self.frame + 20)
                self.say("아르키메데스가 배 위로 떠올랐다! 잔몹 5마리 출현")
            return

        if enemy.get("boss_phase") == "ship":
            enemy["y"] = self.ground - enemy["h"] - 7 + math.sin(self.frame * .055) * 3

        if enemy["state"] == "warning":
            enemy["timer"] -= 1
            if enemy["timer"] <= 0:
                self.launch_enemy_attack(enemy)
            return
        if enemy["state"] == "catapult_flight":
            enemy["timer"] -= 1
            t = 1 - max(0, enemy["timer"]) / enemy["flight_total"]
            enemy["x"] = enemy["flight_start_x"] + (enemy["flight_target_x"] - enemy["flight_start_x"]) * t
            base_y = self.ground - enemy["h"] - (7 if enemy.get("boss_phase") == "ship" else 0)
            enemy["y"] = base_y - math.sin(math.pi * min(1, t)) * 300
            if enemy["timer"] <= 0:
                enemy["y"] = base_y
                target_x = enemy.get("target_x", enemy["x"] + enemy["w"] / 2)
                if abs(px - target_x) < enemy["w"] * .5 + 28 and abs(py - (self.ground - 28)) < 150:
                    before = self.hp
                    self.hurt(56)
                    if self.hp < before:
                        push_dir = 1 if px >= target_x else -1
                        self.launch_player_knockback(118 * 1.5, push_dir, 18, upward_speed=-7)
                self.effects.append(["slam", target_x, self.ground, 24])
                enemy["state"], enemy["timer"] = "cooldown", 115
            return
        if enemy["state"] == "wheel_roll":
            old_x = enemy["x"]
            enemy["x"] = max(0, min(WORLD - enemy["w"], enemy["x"] + enemy.get("vx", 0)))
            enemy["timer"] -= 1
            overlaps = (enemy["x"] < self.player["x"] + PLAYER_W and enemy["x"] + enemy["w"] > self.player["x"]
                        and enemy["y"] < self.player["y"] + PLAYER_H and enemy["y"] + enemy["h"] > self.player["y"])
            if overlaps and not enemy.get("wheel_hits"):
                enemy["wheel_hits"] = True
                self.hurt(38)
                direction = 1 if self.player["x"] > old_x else -1
                self.player["x"] = max(0, min(WORLD - PLAYER_W, self.player["x"] + direction * 90))
            if enemy["timer"] <= 0 or enemy["x"] in (0, WORLD - enemy["w"]):
                enemy["state"], enemy["timer"] = "cooldown", 105
            return
        if enemy["state"] == "cooldown":
            enemy["timer"] -= 1
            if enemy["timer"] <= 0:
                enemy["state"], enemy["timer"] = "idle", random.randint(18, 42)
            return

        # The catapult relocation is a close-range phase event. If its timer
        # expires while the player is far away, keep rolling until they close in.
        if dist < 390 and self.frame >= enemy.get("next_reposition", self.frame + 900):
            self.begin_warning(enemy, "catapult", 54)
            return
        if enemy["timer"] > 0:
            enemy["timer"] -= 1
            return
        if dist < 390:
            action = "lever"
            warning = 27
        else:
            action = "wheel_roll"
            warning = 28
        self.begin_warning(enemy, action, warning)

    def update_enemies(self):
        p = self.player
        px, py = p["x"] + PLAYER_W / 2, p["y"] + PLAYER_H / 2
        for enemy in self.enemies:
            if enemy["rank"] == "dummy":
                continue
            if enemy["hp"] <= 0:
                continue
            if enemy["rank"] != "boss":
                enemy["_wall_old_x"], enemy["_wall_old_y"] = enemy["x"], enemy["y"]
            ex, ey = enemy["x"] + enemy["w"] / 2, enemy["y"] + enemy["h"] / 2
            dx, dy = px - ex, py - ey
            dist = abs(dx)
            enemy["face"] = 1 if dx >= 0 else -1
            if enemy["hit"]:
                enemy["hit"] -= 1
            if enemy.get("state") == "stagger":
                if enemy.get("stagger_delay", 0) > 0:
                    enemy["stagger_delay"] -= 1
                elif enemy.get("stagger_steps", 0) > 0:
                    old_stagger_x = enemy["x"]
                    enemy["x"] = max(0, min(WORLD - enemy["w"],
                                            enemy["x"] + enemy.get("stagger_vx", 0)))
                    enemy["stagger_steps"] -= 1
                    if enemy["rank"] == "boss":
                        self.resolve_horizontal_obstacles(enemy, old_stagger_x,
                                                          enemy["y"], enemy["w"], enemy["h"])
                enemy["timer"] -= 1
                if enemy["timer"] <= 0:
                    enemy["state"], enemy["timer"] = "cooldown", 18
                continue
            if enemy["rank"] == "boss" and self.chapter == 0:
                self.update_archimedes_boss(enemy, px, py, dx, dy, dist)
                continue
            anchored_ranged = enemy["rank"] == "mob" and enemy["kind"] in RANGED_MOBS
            self.update_enemy_physics(enemy)
            pit_id = enemy.get("pit_id")
            if pit_id is not None and pit_id < len(self.pits):
                # Abandon a ranged perch if an enemy falls into a trench. It
                # now prioritizes finding the nearest rim and jumping out.
                enemy["platform_bounds"] = None
                pit = self.pits[pit_id]
                player_left_distance = abs(px - pit["left"])
                player_right_distance = abs(px - pit["right"])
                player_side = -1 if player_left_distance <= player_right_distance else 1
                current_side = enemy.get("pit_escape_side")
                if current_side not in (-1, 1):
                    enemy["pit_escape_side"] = player_side
                else:
                    current_rim = (pit["left"] + 1 if current_side < 0
                                   else pit["right"] - enemy["w"] - 1)
                    if player_side != current_side and abs(current_rim - enemy["x"]) > 36:
                        enemy["pit_escape_side"] = player_side
                side = enemy["pit_escape_side"]
                rim_x = pit["left"] + 1 if side < 0 else pit["right"] - enemy["w"] - 1
                delta_to_rim = rim_x - enemy["x"]
                enemy["face"] = side
                if abs(delta_to_rim) > 4:
                    enemy["x"] += side * min(3.8, abs(delta_to_rim))
                elif enemy["grounded"] and enemy.get("jump_cd", 0) <= self.frame:
                    # The shallow trench is below a normal jump's reachable
                    # height, so trapped grunts can reliably clear its rim.
                    enemy["vy"], enemy["grounded"] = -19.0, False
                    enemy["jump_cd"] = self.frame + 32
                    enemy["state"], enemy["timer"] = "idle", 18
                continue
            enemy["pit_escape_side"] = None
            if enemy["rank"] == "mob" and enemy["kind"] in MELEE_MOBS and enemy["state"] == "idle" and dist > 112:
                enemy["x"] += (1 if dx > 0 else -1) * 2.35
            elif enemy["rank"] == "mob" and enemy["kind"] in RANGED_MOBS and enemy["state"] in ("idle", "cooldown") and abs(dy) < 190:
                toward = 1 if dx > 0 else -1
                if dist < 330:
                    # Archers and crossbowmen retreat when the player closes in.
                    enemy["x"] -= toward * 3.4
                elif dist > 760:
                    enemy["x"] += toward * 1.15
                else:
                    enemy["x"] += math.sin(self.frame * .055 + enemy.get("move_phase", 0)) * .9
                enemy["x"] = max(0, min(WORLD - enemy["w"], enemy["x"]))
            if anchored_ranged and enemy.get("platform_bounds"):
                ledge_left, ledge_right = enemy["platform_bounds"]
                enemy["x"] = max(ledge_left + 8,
                                  min(ledge_right - enemy["w"] - 8, enemy["x"]))
            if (enemy["rank"] != "boss" and not anchored_ranged
                    and enemy["state"] in ("idle", "cooldown") and abs(dy) > 65):
                enemy["x"] += (1 if dx > 10 else -1 if dx < -10 else 0) * 1.8
                if dy < -65 and enemy["grounded"] and enemy.get("jump_cd", 0) <= self.frame:
                    enemy["vy"], enemy["grounded"], enemy["jump_cd"] = -17.2, False, self.frame + 55
                elif dy > 65 and enemy["grounded"]:
                    if any(l < enemy["x"] < r and abs(enemy["y"] + enemy["h"] - (self.ground - rise)) < 2 for l, r, rise in self.platforms):
                        enemy["drop"], enemy["vy"], enemy["grounded"] = 20, 2.5, False

            if enemy["state"] == "notice":
                enemy["timer"] -= 1
                if (enemy["rank"] == "mob" and enemy["kind"] in RANGED_MOBS
                        and enemy["action"] in ("crossbow", "fan", "intercept", "gunshot")):
                    enemy["target_x"], enemy["target_y"] = self.intercept_point(enemy)
                    if enemy["timer"] <= 0:
                        enemy["state"], enemy["timer"] = "warning", 18
                        enemy["telegraph_total"] = 18
                        enemy["telegraph_end_frame"] = self.frame + 18
                elif enemy["timer"] <= 0:
                    self.launch_enemy_attack(enemy)
                continue
            if enemy["state"] == "warning":
                if enemy["action"] in ("crossbow", "fan", "intercept", "gunshot"):
                    enemy["target_x"], enemy["target_y"] = self.intercept_point(enemy)
                enemy["timer"] -= 1
                if enemy["timer"] <= 0:
                    if enemy["action"] in ("crossbow", "fan", "intercept", "gunshot"):
                        # Lock both world coordinates, including the vertical aim.
                        enemy["locked_target_x"] = enemy["target_x"]
                        enemy["locked_target_y"] = enemy["target_y"]
                        enemy["target_x"], enemy["target_y"] = (
                            enemy["locked_target_x"], enemy["locked_target_y"])
                        if enemy["rank"] == "mob" and enemy["kind"] in RANGED_MOBS:
                            self.launch_enemy_attack(enemy)
                        else:
                            enemy["state"], enemy["timer"] = "locked", 60
                    else:
                        self.launch_enemy_attack(enemy)
                continue
            if enemy["state"] == "locked":
                enemy["timer"] -= 1
                if enemy["timer"] <= 0:
                    self.launch_enemy_attack(enemy)
                continue
            if enemy["state"] == "gravity_wait":
                enemy["timer"] -= 1
                if enemy["timer"] <= 0:
                    tx, ty = enemy["target_x"], enemy["target_y"]
                    if math.hypot(px - tx, py - ty) < 135:
                        self.hurt(28)
                    self.effects.append(["gravity", tx, ty, 24])
                    enemy["state"], enemy["timer"] = "cooldown", 100
                continue
            if enemy["state"] == "charge":
                enemy["x"] = max(0, min(WORLD - enemy["w"], enemy["x"] + enemy.get("vx", 0)))
                enemy["timer"] -= 1
                horizontal_hit = (enemy["x"] < p["x"] + PLAYER_W
                                  and enemy["x"] + enemy["w"] > p["x"])
                if enemy["rank"] == "mob" and enemy["kind"] in MELEE_MOBS:
                    vertical_hit = abs(
                        p["y"] + PLAYER_H / 2 - enemy["y"] - enemy["h"] / 2
                    ) <= enemy["h"] * .42
                else:
                    vertical_hit = (enemy["y"] < p["y"] + PLAYER_H
                                    and enemy["y"] + enemy["h"] > p["y"])
                if horizontal_hit and vertical_hit:
                    dash_damage = 26 if self.chapter == 0 and self.phase == 2 and self.archimedes_ship_active else 18
                    self.hurt(dash_damage if enemy["rank"] == "mob" else 28)
                if enemy["timer"] <= 0:
                    enemy["state"], enemy["timer"] = "cooldown", 55
                continue
            if enemy["state"] == "cooldown":
                enemy["timer"] -= 1
                if enemy["timer"] <= 0:
                    enemy["state"] = "idle"
                continue

            if enemy["rank"] == "boss":
                if enemy["timer"] <= 0:
                    if self.chapter == 0:
                        self.begin_warning(enemy, "lever", 42)
                    elif self.chapter == 1:
                        self.begin_warning(enemy, random.choice(("fall", "parabola")), 48)
                    else:
                        self.begin_warning(enemy, random.choice(("gravity", "orbit")), 54)
                else:
                    enemy["timer"] -= 1
            elif enemy["rank"] == "scholar":
                if enemy["timer"] <= 0:
                    if self.frame >= enemy.get("gravity_cd", 0) and dist < 560:
                        self.begin_warning(enemy, "scholar_crush", 48)
                        enemy["gravity_cd"] = self.frame + 240
                    elif dist < 158 and abs(dy) < 150:
                        self.begin_warning(enemy, "scholar_swing", 28)
                    elif dist < 1200 and abs(dy) < 360:
                        action = ("column" if self.chapter == 0 else "pressure" if self.chapter == 1 else "orbit")
                        self.begin_warning(enemy, action, 46)
                    else:
                        enemy["timer"] = 24
                else:
                    enemy["timer"] -= 1
            elif enemy["rank"] == "mob" and enemy["kind"] in MELEE_MOBS:
                if dist < 145 and abs(dy) < 140 and enemy["timer"] <= 0:
                    self.begin_warning(enemy, "mob_swing", random.randint(22, 29))
                elif (self.chapter == 0 and self.phase == 2 and self.archimedes_ship_active
                      and 145 <= dist < 300 and abs(dy) < 135
                      and self.frame >= enemy.get("dash_cd", 0)):
                    self.begin_warning(enemy, "charge", 34)
                    enemy["dash_cd"] = self.frame + 240
                elif dist < 520 and abs(dy) < 160 and enemy["timer"] <= 0:
                    action = random.choice(("slam", "charge"))
                    self.begin_warning(enemy, action, 38 if action == "charge" else 42)
                else:
                    enemy["timer"] -= 1
            elif enemy["rank"] == "mob" and enemy["kind"] in RANGED_MOBS:
                if dist < 1250 and abs(dy) < 360 and enemy["timer"] <= 0:
                    self.begin_warning(enemy, "gunshot", 60)
                else:
                    enemy["timer"] -= 1
            elif dist < 720 and enemy["timer"] <= 0:
                self.begin_warning(enemy, "gunshot", 60)
            else:
                enemy["timer"] -= 1

        for enemy in self.enemies:
            if enemy["hp"] <= 0 or enemy["rank"] in ("boss", "dummy"):
                continue
            old_x = enemy.pop("_wall_old_x", enemy["x"])
            old_y = enemy.pop("_wall_old_y", enemy["y"])
            self.resolve_horizontal_obstacles(enemy, old_x, enemy["y"], enemy["w"], enemy["h"])
            if enemy.get("platform_bounds"):
                ledge_left, ledge_right = enemy["platform_bounds"]
                enemy["x"] = max(ledge_left + 8,
                                  min(ledge_right - enemy["w"] - 8, enemy["x"]))
            obstacle_landing = self.resolve_vertical_obstacles(enemy, old_y, enemy["w"], enemy["h"])
            if obstacle_landing is not None:
                enemy["y"], enemy["vy"], enemy["grounded"] = obstacle_landing - enemy["h"], 0.0, True

        self.enemies = [e for e in self.enemies if e["hp"] > 0]

    def update_combat(self):
        if self.frame < self.attack_until:
            progress = self.frame - (self.attack_until - 20)
            if 6 <= progress <= 15:
                for enemy in self.enemies:
                    # Preserve the established 150px forward / 35px vertical hit range.
                    if id(enemy) not in self.swing_hits and self.in_front(enemy, 150, 35):
                        self.damage_enemy(enemy, 28 if enemy["rank"] != "boss" else 20)
                        enemy["hit"] = 10
                        self.swing_hits.add(id(enemy))

        for shot in self.player_shots:
            old_x, old_y = shot[0], shot[1]
            shot[0] += shot[2]
            shot[1] += shot[3]
            if len(shot) < 7 or shot[6] != "handcannon":
                shot[3] += .25
            shot[4] -= 1
            if self.ignite_tnt(old_x, old_y, shot[0], shot[1]):
                shot[4] = 0
                continue
            if self.shot_hits_wall(old_x, old_y, shot[0], shot[1]):
                shot[4] = 0
                continue
            for enemy in self.enemies:
                if enemy["hp"] > 0 and enemy["x"] < shot[0] < enemy["x"] + enemy["w"] and enemy["y"] < shot[1] < enemy["y"] + enemy["h"]:
                    self.damage_enemy(enemy, shot[5])
                    shot[4] = 0
                    break
        self.player_shots = [s for s in self.player_shots if s[4] > 0]

        for shot in self.enemy_shots:
            if shot[6] == "column":
                if shot[4] > 0:
                    if abs(self.player["x"] + PLAYER_W / 2 - shot[0]) < 24 and self.player["y"] + PLAYER_H >= 70:
                        self.hurt(shot[5])
                    shot[4] -= 1
                continue
            old_x, old_y = shot[0], shot[1]
            shot[0] += shot[2]
            shot[1] += shot[3]
            if shot[6] in ("parabola", "stone"):
                shot[3] += .24
            shot[4] -= 1
            if self.ignite_tnt(old_x, old_y, shot[0], shot[1]):
                shot[4] = 0
                continue
            if self.shot_hits_wall(old_x, old_y, shot[0], shot[1]):
                shot[4] = 0
                continue
            if self.player["x"] < shot[0] < self.player["x"] + PLAYER_W and self.player["y"] < shot[1] < self.player["y"] + PLAYER_H:
                self.hurt(shot[5])
                shot[4] = 0
        self.enemy_shots = [s for s in self.enemy_shots if s[4] > 0 and 0 <= s[0] <= WORLD]

    def progression(self):
        if self.in_shop:
            return
        if (self.waves_complete and not self.round_clear and not self.enemies
                and not self.spawn_queue and not self.game_over and not self.finished):
            self.round_clear = True
            self.exit_door_x = min(max(self.player["x"] + 300, 420), WORLD - 120)
            self.bird_x = max(120, self.exit_door_x - 112)
            self.bird_menu = False
            self.say(f"구역 완수 · 동전 {self.gold} G  /  비둘기에게서 스탯을 강화하세요")

    def tick(self):
        # Accumulate wall-clock time and update only in exact 1/60 s steps.
        # Tk callbacks can arrive late; catch-up steps keep physics and hitstop
        # durations tied to 60 simulation ticks per second rather than render cost.
        now = time.perf_counter()
        elapsed = max(0.0, now - self._last_tick_time)
        self._last_tick_time = now
        self._tick_accumulator += elapsed
        steps = 0
        while (self._tick_accumulator >= FIXED_STEP_SECONDS
               and steps < MAX_CATCH_UP_STEPS):
            self._fixed_update()
            self._tick_accumulator -= FIXED_STEP_SECONDS
            steps += 1

        # Do not let a slow frame trigger an unbounded update loop that makes
        # the next frame even slower. Normal play still advances in 1/60 s steps.
        if steps == MAX_CATCH_UP_STEPS and self._tick_accumulator >= FIXED_STEP_SECONDS:
            self._tick_accumulator %= FIXED_STEP_SECONDS

        delay_ms = max(1, math.ceil((FIXED_STEP_SECONDS - self._tick_accumulator) * 1000))
        # Schedule before drawing so a slow render does not cancel the loop.
        self.root.after(delay_ms, self.tick)
        if steps:
            self.draw()

    def _fixed_update(self):
        if self.settings_open or self.blessing_menu or self.stats_open:
            return
        self.frame += 1
        if not self.game_over and not self.finished:
            if self.transition == 0 and self.frame >= self.hitstop_until:
                self.update_player()
                self.update_spawns()
                self.update_enemies()
                self.update_combat()
                self.update_meteors()
                self.update_hazards()
            self.progression()
        if self.frame >= self.shake_until:
            self.shake_strength = 0
        for effect in self.effects:
            effect[3] -= 1
        self.effects = [e for e in self.effects if e[3] > 0]
        self.update_coin_drops()

    def build_player_images(self):
        """Build shaded 64x64 scholar sprites with hand-authored pixel clusters."""
        palette = {
            "outline": "#292b40", "hood": "#29445f", "hood_hi": "#567d94",
            "hood_shadow": "#1d3048", "skin": "#e8b58f", "skin_hi": "#ffd4ab",
            "skin_shadow": "#ad746b", "steel": "#9eb5b7", "steel_hi": "#e0e4d3",
            "hair": "#795748", "hair_hi": "#b28a67", "robe": "#d5c29d",
            "robe_hi": "#f3e3c2", "robe_shadow": "#9b846d", "sash": "#9c526c",
            "sash_hi": "#df8c91", "leather": "#684a43", "leather_hi": "#bd8b59",
            "trouser": "#54495b", "boot": "#373348", "gold": "#e5c477",
            "teal": "#79b8b2", "garnet": "#ad5266",
        }

        def line(grid, x1, y1, x2, y2, color, thickness=1):
            steps = max(abs(x2 - x1), abs(y2 - y1), 1)
            radius = thickness // 2
            for step in range(steps + 1):
                t = step / steps
                cx, cy = round(x1 + (x2 - x1) * t), round(y1 + (y2 - y1) * t)
                for oy in range(-radius, radius + 1):
                    for ox in range(-radius, radius + 1):
                        if 0 <= cx + ox < 64 and 0 <= cy + oy < 64:
                            grid[cy + oy][cx + ox] = color

        def build_pose(pose):
            g = [[None for _ in range(64)] for _ in range(64)]

            def ellipse(cx, cy, rx, ry, color, border=None):
                for yy in range(max(0, cy - ry), min(64, cy + ry + 1)):
                    for xx in range(max(0, cx - rx), min(64, cx + rx + 1)):
                        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
                        if d <= 1:
                            g[yy][xx] = border if border and d > .78 else color

            # Hood, face, hair, brows and facial highlights.
            ellipse(32, 17, 19, 16, palette["hood"], palette["outline"])
            ellipse(32, 17, 15, 13, palette["hood_hi"], palette["hood_shadow"])
            ellipse(32, 21, 10, 11, palette["skin"], palette["outline"])
            for yy in range(12, 19):
                for xx in range(24, 39):
                    if g[yy][xx] == palette["skin"]:
                        g[yy][xx] = palette["hair"] if yy < 15 else palette["hair_hi"]
            line(g, 24, 28, 40, 28, palette["hair"], 3)
            line(g, 26, 19, 30, 19, palette["outline"], 2)
            line(g, 35, 19, 39, 19, palette["outline"], 2)
            g[20][28], g[20][37] = palette["skin_hi"], palette["skin_hi"]
            line(g, 33, 21, 36, 24, palette["skin_hi"], 1)
            line(g, 29, 26, 35, 26, palette["hair"], 1)
            g[22][26], g[22][27] = palette["skin_shadow"], palette["skin_hi"]
            g[22][38], g[22][39] = palette["skin_hi"], palette["skin_shadow"]
            g[24][32], g[25][33] = palette["skin_shadow"], palette["skin_hi"]
            line(g, 18, 14, 23, 8, palette["hood_hi"], 2)
            line(g, 23, 8, 32, 5, palette["hood_hi"], 2)
            line(g, 32, 5, 42, 8, palette["hood_hi"], 2)
            line(g, 42, 8, 47, 14, palette["hood_hi"], 2)
            line(g, 26, 10, 38, 10, palette["gold"], 1)

            # Satchel behind a layered, tapered robe.
            for yy in range(29, 45):
                for xx in range(43, 55):
                    g[yy][xx] = palette["leather_hi"] if xx == 44 or yy == 30 else palette["leather"]
            line(g, 47, 31, 50, 42, palette["gold"], 1)
            for yy in range(26, 51):
                if yy < 32:
                    half = 13 + (yy - 26)
                elif yy < 42:
                    half = 19
                else:
                    half = 19 - (yy - 42) // 2
                left, right = 32 - half, 32 + half
                for xx in range(left, right + 1):
                    if xx in (left, right):
                        color = palette["outline"]
                    elif xx < 27:
                        color = palette["robe_shadow"]
                    elif 28 <= xx <= 36 and yy < 41:
                        color = palette["robe_hi"] if (xx + yy) % 5 else palette["robe"]
                    else:
                        color = palette["robe"]
                    g[yy][xx] = color

            # Shoulder guards, leather cross-strap, sash, stitching and sigil.
            for yy in range(28, 37):
                for xx in range(13, 23):
                    if (xx - 18) ** 2 / 25 + (yy - 32) ** 2 / 25 <= 1:
                        g[yy][xx] = palette["hood_shadow"] if xx < 16 else palette["robe"]
                for xx in range(41, 51):
                    if (xx - 46) ** 2 / 25 + (yy - 32) ** 2 / 25 <= 1:
                        g[yy][xx] = palette["robe_shadow"] if xx > 48 else palette["robe"]
            line(g, 19, 31, 27, 41, palette["leather"], 4)
            line(g, 20, 30, 28, 40, palette["leather_hi"], 1)
            for xx in range(23, 42):
                g[42][xx] = palette["sash"]
                if xx % 4 != 0:
                    g[41][xx] = palette["sash_hi"]
            for yy in range(30, 49):
                g[yy][15] = palette["gold"] if yy % 4 else palette["robe_hi"]
                g[yy][48] = palette["robe_shadow"]
            g[42][32], g[43][32] = palette["gold"], palette["robe_hi"]
            line(g, 25, 34, 39, 37, palette["robe_shadow"], 1)
            line(g, 27, 37, 38, 40, palette["robe_hi"], 1)

            # Fine tailoring: a reinforced collar, stitched robe panels,
            # brass buckles and a small stitched formula emblem.
            line(g, 25, 29, 32, 34, palette["steel"], 2)
            line(g, 32, 34, 39, 29, palette["steel_hi"], 2)
            for yy in (35, 39, 45):
                g[yy][20] = palette["robe_hi"]
                g[yy][44] = palette["robe_shadow"]
                g[yy][45] = palette["leather_hi"]
            for xx, yy in ((25, 31), (39, 31), (24, 44), (40, 44)):
                g[yy][xx] = palette["gold"]
            line(g, 30, 35, 34, 35, palette["garnet"], 1)
            line(g, 32, 35, 32, 39, palette["gold"], 1)
            g[37][31], g[37][33] = palette["teal"], palette["teal"]
            # The exposed satchel edge has its own stitching and clasp.
            for yy in range(34, 44, 3):
                g[yy][52] = palette["leather_hi"]
            g[37][53], g[38][53] = palette["gold"], palette["gold"]

            # Pose-specific legs and boots add weight to running, jumping and falling.
            legs = {
                "idle": ((27, 47, 23, 57, 19, 60), (37, 47, 41, 57, 46, 60)),
                "run_a": ((27, 47, 19, 53, 13, 56), (37, 47, 44, 53, 51, 55)),
                "run_b": ((27, 47, 20, 53, 14, 55), (37, 47, 45, 53, 52, 56)),
                "jump": ((27, 47, 22, 52, 18, 52), (37, 47, 43, 52, 48, 52)),
                "fall": ((27, 47, 25, 56, 23, 60), (37, 47, 39, 56, 42, 60)),
                "double_jump": ((27, 47, 20, 52, 16, 49), (37, 47, 45, 52, 49, 49)),
                "dash": ((27, 47, 18, 52, 10, 54), (37, 47, 29, 51, 21, 54)),
            }[pose]
            for ax, ay, bx, by, cx, cy in legs:
                line(g, ax, ay, bx, by, palette["trouser"], 6)
                line(g, bx, by, cx, cy, palette["boot"], 6)
                line(g, bx - 2, by, bx + 2, by + 1, palette["steel"], 2)
                line(g, cx - 3, cy - 1, cx + 2, cy - 1, palette["boot"], 2)
                line(g, cx - 2, cy + 2, cx + 3, cy + 2, palette["gold"], 1)
            for xx, yy in ((24, 48), (40, 48), (22, 54), (42, 54)):
                g[yy][xx] = palette["robe_hi"]
            return g

        images = {}
        for pose in ("idle", "run_a", "run_b", "jump", "fall", "double_jump", "dash"):
            detailed = build_pose(pose)
            # Render a coarser 32x32 source grid, then scale it back up so the
            # scholar keeps the same silhouette with fewer fine pixel details.
            reduced = []
            for grid_y in range(32):
                row = []
                for grid_x in range(32):
                    counts = {}
                    for dy in (0, 1):
                        for dx in (0, 1):
                            color = detailed[grid_y * 2 + dy][grid_x * 2 + dx]
                            counts[color] = counts.get(color, 0) + 1
                    row.append(max(counts, key=counts.get))
                reduced.append(row)
            source = [[reduced[y // 2][x // 2] for x in range(64)] for y in range(64)]
            for facing in (1, -1):
                pixels = source if facing > 0 else [row[::-1] for row in source]
                image = tk.PhotoImage(master=self.root, width=PLAYER_SPRITE_W, height=PLAYER_SPRITE_H)
                for out_y in range(PLAYER_SPRITE_H):
                    sy = min(63, round(out_y * 63 / (PLAYER_SPRITE_H - 1)))
                    row_colors, blanks = [], []
                    for out_x in range(PLAYER_SPRITE_W):
                        sx = min(63, round(out_x * 63 / (PLAYER_SPRITE_W - 1)))
                        color = pixels[sy][sx]
                        if color is None:
                            edge = any(0 <= sy + oy < 64 and 0 <= sx + ox < 64
                                       and pixels[sy + oy][sx + ox] is not None
                                       for oy in (-1, 0, 1) for ox in (-1, 0, 1) if ox or oy)
                            if edge:
                                color = palette["outline"]
                            else:
                                color = "#010203"
                                blanks.append(out_x)
                        row_colors.append(color)
                    image.put("{" + " ".join(row_colors) + "}", to=(0, out_y))
                    for out_x in blanks:
                        image.transparency_set(out_x, out_y, True)
                images[(pose, facing)] = image
        return images

    def sx(self, x):
        return x - self.camera

    def world_rect_visible(self, x1, y1, x2, y2, margin=0):
        """Return whether a world-space rectangle can affect the visible view."""
        return not (
            x2 < self.camera - margin
            or x1 > self.camera + self.w + margin
            or y2 < self.camera_y - margin
            or y1 > self.camera_y + self.h + margin
        )

    def rect(self, x1, y1, x2, y2, color, outline=""):
        self.canvas.create_rectangle(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), fill=color, outline=outline)

    @staticmethod
    @lru_cache(maxsize=512)
    def color_mix(first, second, amount):
        a = tuple(int(first[i:i + 2], 16) for i in (1, 3, 5))
        b = tuple(int(second[i:i + 2], 16) for i in (1, 3, 5))
        rgb = tuple(round(x + (y - x) * amount) for x, y in zip(a, b))
        return "#%02x%02x%02x" % rgb

    def draw_cached_background(self, era, cam):
        """Reuse detailed scenery between camera changes to avoid Tk redraw churn."""
        c = self.canvas
        cache_key = (self.chapter, self.w, self.h)
        delta = cam - self._background_camera
        if cache_key == self._background_cache_key and abs(delta) < 320:
            if delta:
                c.move("bg:sun", -delta * .08, 0)
                c.move("bg:far", -delta * .42, 0)
                c.move("bg:room-scroll", -delta, 0)
            self._background_camera = cam
            return

        for tag in ("bg:fixed", "bg:sun", "bg:far", "bg:room-fixed", "bg:room-scroll"):
            c.delete(tag)
        c._physics_draw_tag = "bg:fixed"
        # Soft, multi-stop sky gradient: richer than flat color bands while
        # staying subdued behind combat silhouettes and warning indicators.
        sky_colors = self.sky_gradient_cache[self.chapter]
        band_count = len(sky_colors)
        sky_h = self.h * .68
        for band in range(band_count):
            y1, y2 = sky_h * band / band_count, sky_h * (band + 1) / band_count + 1
            c.create_rectangle(0, y1, self.w, y2, fill=sky_colors[band], outline="")
        c._physics_draw_tag = "bg:sun"
        sun = self.w * .72 - cam * .08
        sun_y = self.h * .18
        for radius, tint in ((100, .18), (76, .32), (56, .58), (40, 1.0)):
            glow = self.color_mix(era["far"], era["accent"], tint)
            c.create_oval(sun - radius, sun_y - radius, sun + radius, sun_y + radius,
                          fill=glow, outline="")
        for ray in range(12):
            angle = math.tau * ray / 12 + self.frame * .001
            c.create_line(sun + math.cos(angle) * 108, sun_y + math.sin(angle) * 108,
                          sun + math.cos(angle) * 138, sun_y + math.sin(angle) * 138,
                          fill=self.color_mix(era["far"], era["accent"], .48), width=2)
        c._physics_draw_tag = "bg:far"
        # Low-contrast distant stonework keeps silhouettes and attack telegraphs clear.
        for i in range(int(cam // 400) - 1, int((cam + self.w) // 400) + 2):
            bx = i * 400 - cam * .42
            bh = 190 + (i * 37 % 80)
            # Background buildings stay anchored to the viewport as the player
            # climbs; only the world geometry and platforms follow the camera.
            bg_ground = int(self.h * .72)
            c.create_rectangle(bx, bg_ground - bh, bx + 360, bg_ground, fill=era["far"], outline="")
            if self.chapter == 0:
                c.create_polygon(bx + 50, bg_ground - bh + 12, bx + 180, bg_ground - bh - 40, bx + 310, bg_ground - bh + 12, fill=era["far"], outline="")
                c.create_rectangle(bx + 64, bg_ground - bh + 8, bx + 78, bg_ground - 22, fill=era["near"], outline="")
                c.create_rectangle(bx + 146, bg_ground - bh + 8, bx + 160, bg_ground - 22, fill=era["near"], outline="")
            elif self.chapter == 1:
                c.create_rectangle(bx + 92, bg_ground - bh - 24, bx + 220, bg_ground, fill=era["far"], outline="")
                c.create_polygon(bx + 84, bg_ground - bh - 24, bx + 156, bg_ground - bh - 74, bx + 228, bg_ground - bh - 24, fill=era["near"], outline="")
            else:
                c.create_rectangle(bx + 86, bg_ground - bh - 40, bx + 242, bg_ground, fill=era["far"], outline="")
                c.create_oval(bx + 126, bg_ground - bh - 82, bx + 202, bg_ground - bh - 8, fill=era["near"], outline="")
            # Architectural ribs, inset windows and stone highlights provide
            # depth without adding high-contrast visual noise.
            for column_x in (bx + 28, bx + 330):
                c.create_rectangle(column_x, bg_ground - bh + 18, column_x + 12, bg_ground - 4,
                                   fill=self.color_mix(era["far"], era["accent"], .12), outline="")
                c.create_rectangle(column_x - 7, bg_ground - bh + 12, column_x + 19, bg_ground - bh + 22,
                                   fill=era["near"], outline="")
            for window_x in (bx + 104, bx + 224):
                c.create_arc(window_x, bg_ground - bh * .62, window_x + 34, bg_ground - bh * .28,
                             start=0, extent=180, style="arc",
                             outline=self.color_mix(era["near"], era["accent"], .18), width=3)
            # Era-specific masonry, windows and carved trim add recognizable
            # architecture while staying muted behind the fighting silhouettes.
            stone_mid = self.color_mix(era["far"], era["near"], .38)
            stone_light = self.color_mix(era["far"], era["accent"], .20)
            if self.chapter == 0:
                # Syracusan portico: fluted columns, capitals and a carved frieze.
                for cx in (bx + 94, bx + 198, bx + 286):
                    c.create_rectangle(cx - 12, bg_ground - bh + 24, cx + 12, bg_ground - 8,
                                       fill=stone_mid, outline="")
                    for flute in (-7, 0, 7):
                        c.create_line(cx + flute, bg_ground - bh + 32, cx + flute, bg_ground - 15,
                                      fill=stone_light, width=1)
                    c.create_rectangle(cx - 20, bg_ground - bh + 16, cx + 20, bg_ground - bh + 28,
                                       fill=era["near"], outline=stone_light, width=1)
                    c.create_rectangle(cx - 17, bg_ground - 13, cx + 17, bg_ground - 3,
                                       fill=era["near"], outline="")
                c.create_rectangle(bx + 76, bg_ground - bh + 35, bx + 316, bg_ground - bh + 43,
                                   fill=stone_mid, outline="")
                for relief_x in range(int(bx + 88), int(bx + 306), 22):
                    c.create_polygon(relief_x, bg_ground - bh + 40, relief_x + 5, bg_ground - bh + 32,
                                     relief_x + 10, bg_ground - bh + 40, fill=stone_light, outline="")
            elif self.chapter == 1:
                # Renaissance palazzo: brick courses, deep arched windows and balconies.
                for row_y in range(int(bg_ground - bh + 28), int(bg_ground - 12), 22):
                    c.create_line(bx + 84, row_y, bx + 234, row_y,
                                  fill=self.color_mix(era["far"], era["accent"], .13), width=1)
                    stagger = 14 if (row_y // 22) % 2 else 0
                    for brick_x in range(int(bx + 84 + stagger), int(bx + 234), 42):
                        c.create_line(brick_x, row_y, brick_x, row_y + 21,
                                      fill=self.color_mix(era["far"], era["accent"], .11), width=1)
                for wx in (bx + 112, bx + 174, bx + 236):
                    c.create_rectangle(wx, bg_ground - bh * .68, wx + 26, bg_ground - bh * .39,
                                       fill=era["sky"], outline=stone_light, width=2)
                    c.create_arc(wx, bg_ground - bh * .78, wx + 26, bg_ground - bh * .56,
                                 start=0, extent=180, style="arc", outline=stone_light, width=3)
                    c.create_line(wx + 13, bg_ground - bh * .68, wx + 13, bg_ground - bh * .39,
                                  fill=stone_mid, width=2)
                    c.create_line(wx - 5, bg_ground - bh * .37, wx + 31, bg_ground - bh * .37,
                                  fill=era["near"], width=3)
            else:
                # English observatory keep: crenellations, mullioned lancets and clockwork.
                for tooth_x in range(int(bx + 84), int(bx + 248), 28):
                    c.create_rectangle(tooth_x, bg_ground - bh - 47, tooth_x + 15, bg_ground - bh - 34,
                                       fill=era["near"], outline="")
                for wx in (bx + 110, bx + 158, bx + 206):
                    c.create_rectangle(wx, bg_ground - bh * .72, wx + 17, bg_ground - bh * .35,
                                       fill=era["sky"], outline=stone_light, width=2)
                    c.create_polygon(wx - 3, bg_ground - bh * .72, wx + 8, bg_ground - bh * .82,
                                     wx + 20, bg_ground - bh * .72, fill=stone_mid, outline="")
                    c.create_line(wx + 8, bg_ground - bh * .70, wx + 8, bg_ground - bh * .37,
                                  fill=stone_light, width=1)
                c.create_oval(bx + 258, bg_ground - bh * .66, bx + 310, bg_ground - bh * .43,
                              outline=stone_light, width=2)
                c.create_line(bx + 284, bg_ground - bh * .65, bx + 284, bg_ground - bh * .44,
                              fill=stone_light, width=1)
        c._physics_draw_tag = "bg:room-fixed"
        # Foreground interior wall: the former skyline now reads as the view
        # outside a built room, with pilasters framing the playable chamber.
        wall_top = int(self.h * .29)
        wall_base = self.h
        wall = self.color_mix(era["far"], era["ground"], .42)
        wall_lit = self.color_mix(wall, era["accent"], .12)
        c.create_rectangle(0, wall_top, self.w, wall_base, fill=wall, outline="")
        c.create_line(0, wall_top, self.w, wall_top, fill=wall_lit, width=5)
        c.create_line(0, wall_base, self.w, wall_base, fill=self.color_mix(wall, era["near"], .35), width=4)
        c._physics_draw_tag = "bg:room-scroll"
        # Large mullioned openings reveal an outdoor landscape beyond the room.
        for wx in range(-int(cam % 620) - 40, self.w + 620, 620):
            wy1, wy2 = wall_top + 52, wall_top + 206
            win_sky = self.color_mix(era["sky"], era["accent"], .18)
            c.create_rectangle(wx, wy1, wx + 204, wy2, fill=win_sky, outline="")
            horizon = wy1 + 92
            c.create_oval(wx + 127, wy1 + 18, wx + 163, wy1 + 54,
                          fill=self.color_mix(era["sky"], era["accent"], .55), outline="")
            # Distant hills and rooftops beyond the window.
            c.create_polygon(wx, horizon + 18, wx + 46, horizon - 12, wx + 94, horizon + 10,
                             wx + 148, horizon - 22, wx + 204, horizon + 5, wx + 204, wy2,
                             wx, wy2, fill=self.color_mix(era["far"], era["sky"], .32), outline="")
            c.create_rectangle(wx, horizon + 22, wx + 204, wy2,
                               fill=self.color_mix(era["far"], era["ground"], .18), outline="")
            for tower_x in (wx + 25, wx + 76, wx + 167):
                c.create_rectangle(tower_x, horizon - 3, tower_x + 22, horizon + 24,
                                   fill=era["far"], outline="")
                c.create_polygon(tower_x - 4, horizon - 3, tower_x + 11, horizon - 18,
                                 tower_x + 26, horizon - 3, fill=era["near"], outline="")
            # Carved stone jambs, lintel and a central mullion make these openings architectural.
            c.create_rectangle(wx - 10, wy1 - 12, wx + 214, wy1 + 2, fill=era["near"], outline=wall_lit, width=2)
            c.create_rectangle(wx - 8, wy1, wx + 4, wy2, fill=era["near"], outline=wall_lit, width=1)
            c.create_rectangle(wx + 200, wy1, wx + 212, wy2, fill=era["near"], outline=wall_lit, width=1)
            c.create_rectangle(wx + 96, wy1, wx + 104, wy2, fill=era["near"], outline="")
            c.create_line(wx - 3, wy2 - 18, wx + 207, wy2 - 18, fill=era["near"], width=5)
        c._physics_draw_tag = "bg:room-fixed"
        # Interior stone joints, pilasters, torch sconces and muted heraldic cloth.
        for seam_y in range(wall_top + 28, wall_base, 48):
            c.create_line(0, seam_y, self.w, seam_y,
                          fill=self.color_mix(wall, era["accent"], .075), width=1)
        c._physics_draw_tag = "bg:room-scroll"
        for px in range(48 - int(cam % 360), self.w + 360, 360):
            c.create_rectangle(px - 12, wall_top + 8, px + 12, wall_base,
                               fill=self.color_mix(wall, era["near"], .45), outline="")
            c.create_line(px - 5, wall_top + 16, px - 5, wall_base - 8,
                          fill=wall_lit, width=2)
            torch_y = wall_top + 236
            c.create_line(px, torch_y, px, torch_y + 22, fill=era["near"], width=4)
            c.create_polygon(px, torch_y - 17, px - 7, torch_y - 5, px, torch_y + 1,
                             px + 7, torch_y - 5, fill=era["accent"], outline="")
            c.create_oval(px - 4, torch_y - 10, px + 4, torch_y - 2,
                          fill=self.color_mix(era["accent"], "#fff3bf", .45), outline="")
        c._physics_draw_tag = "frame"
        self._background_cache_key = cache_key
        self._background_camera = cam

    def draw(self):
        c = self.canvas
        era = ERAS[min(self.chapter, len(ERAS) - 1)]
        ground = self.sy(self.ground)
        cam = self.camera
        c.delete("frame")
        self.draw_cached_background(era, cam)
        # Chamber thresholds make the route feel like connected rooms, not an endless field.
        for boundary in range(ROOM_WIDTH, WORLD, ROOM_WIDTH):
            bx = boundary - cam
            if -80 < bx < self.w + 80:
                c.create_rectangle(bx - 26, ground - 198, bx + 26, ground, fill=era["far"], outline=era["near"], width=3)
                c.create_rectangle(bx - 46, ground - 210, bx + 46, ground - 184, fill=era["near"], outline=era["accent"], width=2)
                c.create_rectangle(bx - 17, ground - 156, bx + 17, ground - 6, fill=era["sky"], outline="")
        if self.round_clear and self.exit_door_x is not None:
            door_x = self.sx(self.exit_door_x)
            self.rect(door_x - 48, ground - 194, door_x + 48, ground, "#72536f", "#ffe0a3")
            c.create_arc(door_x - 48, ground - 238, door_x + 48, ground - 142, start=0, extent=180,
                         fill="#72536f", outline="#ffe0a3", width=3)
            self.rect(door_x - 27, ground - 150, door_x + 27, ground, "#20253a", "#ffd17e")
            c.create_text(door_x, ground - 110, text="↑", fill="#fff0cf", font=("TkDefaultFont", 19, "bold"))
        c.create_rectangle(0, ground, self.w, self.h, fill=era["ground"], outline="")
        c.create_rectangle(0, ground, self.w, ground + 4, fill=era["accent"], outline="")
        # Broad brick courses use only soft seams and shadows, with no tiny
        # pixel chips or individually drawn stone texture.
        floor_height = max(1, self.h - int(ground))
        band_count = 8
        for band in range(band_count):
            top = ground + floor_height * band / band_count
            bottom = ground + floor_height * (band + 1) / band_count
            shade = self.color_mix(era["ground"], "#171724", .025 + band * .012)
            c.create_rectangle(0, top, self.w, bottom, fill=shade, outline="")
        brick_h, brick_w = 48, 190
        for row, seam_y in enumerate(range(int(ground) + brick_h, self.h + brick_h, brick_h)):
            shadow = self.color_mix(era["ground"], "#171724", .11)
            highlight = self.color_mix(era["ground"], era["near"], .055)
            c.create_line(0, seam_y, self.w, seam_y, fill=shadow, width=2)
            c.create_line(0, seam_y - 2, self.w, seam_y - 2, fill=highlight, width=1)
            stagger = brick_w // 2 if row % 2 else 0
            for seam_x in range(-stagger, self.w + brick_w, brick_w):
                c.create_line(seam_x, seam_y - brick_h, seam_x, seam_y,
                              fill=shadow, width=2)

        # Recessed stone trenches: the cavity masks the floor tiles and ends
        # in visible iron-red spikes at the same depth used by collision.
        for pit in self.pits:
            x1, x2 = self.sx(pit["left"]), self.sx(pit["right"])
            y_top, y_bottom = self.sy(self.ground), self.sy(pit["bottom"])
            if x2 < -20 or x1 > self.w + 20 or y_bottom < 0 or y_top > self.h:
                continue
            cavity = self.color_mix(era["ground"], "#171b2b", .78)
            wall = self.color_mix(era["ground"], era["near"], .38)
            c.create_rectangle(x1, y_top, x2, y_bottom, fill=cavity,
                               outline=self.color_mix(wall, era["accent"], .28), width=2)
            c.create_polygon(x1, y_top, x1 + 18, y_top + 20,
                             x1 + 18, y_bottom - 13, x1 + 7, y_bottom,
                             x2 - 7, y_bottom, x2 - 18, y_bottom - 13,
                             x2 - 18, y_top + 20, x2, y_top,
                             fill=self.color_mix(cavity, wall, .20), outline="")
            c.create_line(x1 + 2, y_top + 3, x1 + 18, y_top + 20,
                          fill=self.color_mix(wall, era["accent"], .40), width=3)
            c.create_line(x2 - 2, y_top + 3, x2 - 18, y_top + 20,
                          fill=self.color_mix(wall, era["accent"], .40), width=3)
            for ledge_x in (x1 + 6, x2 - 16):
                c.create_rectangle(ledge_x, y_top + 24, ledge_x + 10, y_bottom - 10,
                                   fill=self.color_mix(wall, era["ground"], .30), outline="")
                for chip_y in range(int(y_top + 38), int(y_bottom - 14), 38):
                    c.create_line(ledge_x + 2, chip_y, ledge_x + 8, chip_y + 4,
                                  fill=self.color_mix(wall, era["near"], .36), width=1)
            c.create_rectangle(x1 + 12, y_bottom - 8, x2 - 12, y_bottom + 1,
                               fill=self.color_mix(wall, era["ground"], .14), outline=era["near"])
            spike_step = 18
            for tip in range(int(x1 + 16), int(x2 - 16), spike_step):
                c.create_polygon(tip, y_bottom - 1, tip + spike_step / 2, y_bottom - 26,
                                 tip + spike_step, y_bottom - 1,
                                 fill="#bd5967", outline="#f0b77f", width=1)
                c.create_line(tip + spike_step / 2, y_bottom - 22,
                              tip + spike_step / 2, y_bottom - 4,
                              fill="#ffe0b0", width=1)
            c.create_line(x1 + 13, y_bottom - 1, x2 - 13, y_bottom - 1,
                          fill="#e78775", width=2)
        for left, right, rise in self.platforms:
            x1, x2 = left - cam, right - cam
            if x2 < 0 or x1 > self.w:
                continue
            py = self.sy(self.ground - rise)
            c.create_rectangle(x1, py, x2, py + 14, fill=era["near"], outline="#f0c68f", width=2)
            c.create_rectangle(x1, py, x2, py + 4, fill=self.color_mix(era["near"], era["accent"], .82), outline="")
            c.create_line(x1 + 3, py + 6, x2 - 3, py + 6,
                          fill=self.color_mix(era["near"], era["ground"], .32), width=2)
            for seam in range(int(x1 + 36), int(x2), 48):
                c.create_line(seam, py + 7, seam, py + 13,
                              fill=self.color_mix(era["near"], era["ground"], .24), width=1)
                c.create_oval(seam - 2, py + 2, seam + 2, py + 5, fill=era["accent"], outline="")
                c.create_line(seam + 3, py + 8, seam + 7, py + 12,
                              fill=self.color_mix(era["near"], era["accent"], .30), width=1)
            for post in range(int(x1 + 12), int(x2), 34):
                c.create_rectangle(post, py + 14, post + 5, py + 26,
                                   fill=self.color_mix(era["ground"], era["near"], .18), outline="")
                c.create_line(post + 1, py + 15, post + 1, py + 24, fill=era["accent"], width=1)

        # Roofs and closed room dividers form one readable indoor route.
        for left, top, right, bottom in self.obstacles:
            x1, y1, x2, y2 = left - cam, self.sy(top), right - cam, self.sy(bottom)
            if x2 < 0 or x1 > self.w or y2 < 0 or y1 > self.h:
                continue
            is_gate = self.gate_obstacle == (left, top, right, bottom)
            wall = self.color_mix(era["ground"], era["near"], .30 if is_gate else .44)
            c.create_rectangle(x1, y1, x2, y2, fill=wall, outline="#292b40", width=2)
            c.create_line(x1 + 3, y1 + 3, x2 - 3, y1 + 3,
                          fill=self.color_mix(wall, era["accent"], .52), width=2)
            for seam_y in range(int(y1 + 26), int(y2), 28):
                c.create_line(x1 + 2, seam_y, x2 - 2, seam_y,
                              fill=self.color_mix(wall, era["ground"], .36), width=1)
            for seam_x in range(int(x1 + 32), int(x2), 42):
                c.create_line(seam_x, y1 + 4, seam_x, y2 - 3,
                              fill=self.color_mix(wall, era["ground"], .28), width=1)
            if is_gate:
                c.create_line((x1 + x2) / 2, y1 + 8, (x1 + x2) / 2, y2 - 4,
                              fill=self.color_mix(wall, era["accent"], .42), width=3)
                for bolt_y in (y1 + 24, (y1 + y2) / 2, y2 - 24):
                    c.create_oval(x1 + 8, bolt_y - 3, x1 + 14, bolt_y + 3,
                                  fill=era["accent"], outline="#30283a")
                    c.create_oval(x2 - 14, bolt_y - 3, x2 - 8, bolt_y + 3,
                                  fill=era["accent"], outline="#30283a")
            elif top == ROOF_TOP and bottom == ROOF_BOTTOM:
                c.create_line(x1 + 3, y2 - 4, x2 - 3, y2 - 4,
                              fill=self.color_mix(wall, era["accent"], .38), width=3)

        for crate in self.tnt_crates:
            if not self.world_rect_visible(
                crate["x"] - 12, crate["y"] - 12,
                crate["x"] + crate["w"] + 12, crate["y"] + crate["h"] + 4,
            ):
                continue
            cx, cy = self.sx(crate["x"]), self.sy(crate["y"])
            lit = crate["fuse"] is not None
            body = "#dc655d" if lit else "#a95152"
            c.create_rectangle(cx, cy, cx + crate["w"], cy + crate["h"],
                               fill=body, outline="#392d3b", width=2)
            c.create_rectangle(cx - 3, cy + 7, cx + crate["w"] + 3, cy + 14,
                               fill="#e5bd7a", outline="#49383c", width=1)
            c.create_rectangle(cx - 3, cy + crate["h"] - 15, cx + crate["w"] + 3,
                               cy + crate["h"] - 8, fill="#e5bd7a", outline="#49383c", width=1)
            c.create_text(cx + crate["w"] / 2, cy + crate["h"] / 2,
                          text="TNT", fill="#fff0cf", font=("TkDefaultFont", 8, "bold"))
            if lit:
                c.create_oval(cx + crate["w"] - 5, cy - 10, cx + crate["w"] + 7, cy + 2,
                              fill="#ffd26c", outline="#fff0cf")

        for room, event in self.blessing_events.items():
            if event.get("shop") and not self.midrun_shop_active:
                continue
            if event["used"] or not self.world_rect_visible(
                    event["x"] - 60, self.ground - 110, event["x"] + 60, self.ground + 8):
                continue
            figure = BLESSINGS[CHAPTER_BLESSINGS[event["chapter"]]]["figure"]
            sx, sy = self.sx(event["x"]), ground
            accent = ERAS[event["chapter"]]["accent"]
            c.create_oval(sx - 28, sy - 82, sx + 28, sy - 25,
                          outline=self.color_mix(accent, "#ffffff", .28), width=2)
            c.create_oval(sx - 20, sy - 73, sx + 20, sy - 33,
                          fill=self.color_mix(ERAS[event["chapter"]]["far"], accent, .36),
                          outline="#292b40", width=2)
            c.create_oval(sx - 9, sy - 104, sx + 9, sy - 86,
                          fill="#e5b895", outline="#403747", width=2)
            c.create_polygon(sx - 13, sy - 90, sx + 13, sy - 90,
                             sx + 21, sy - 30, sx - 21, sy - 30,
                             fill=self.color_mix(ERAS[event["chapter"]]["near"], accent, .2),
                             outline="#43384a", width=2)
            c.create_text(sx, sy - 119, text=figure, fill=accent,
                          font=("TkDefaultFont", 9, "bold"))
            if room == self.room_wave_index and abs(self.player["x"] - event["x"]) < 150:
                c.create_text(sx, sy - 136,
                              text=f"{self.key_label(self.controls['interact'])} 대화",
                              fill="#fff0c9", font=("TkDefaultFont", 9, "bold"))

        if self.midrun_shop_active:
            # A quiet roadside bookstall and healing pigeon sit in the third room.
            for shelf_x in (SHOP_START_X + 840, SHOP_START_X + 1430):
                sx = self.sx(shelf_x)
                self.rect(sx, ground - 140, sx + 178, ground - 14, "#433a32", "#9a8157")
                self.rect(sx + 7, ground - 91, sx + 171, ground - 85, "#b29868")
                self.rect(sx + 7, ground - 43, sx + 171, ground - 37, "#b29868")
                for index, book_x in enumerate(range(int(sx + 15), int(sx + 166), 24)):
                    colors = ("#9b514b", "#64816f", "#b18c53", "#626d91")
                    color = colors[(index + int(shelf_x // 24)) % len(colors)]
                    self.rect(book_x, ground - 133, book_x + 15, ground - 94, color, "#392d35")
                    self.rect(book_x + 3, ground - 81, book_x + 17, ground - 46, color, "#392d35")
                if shelf_x == NEWTON_STALL_X:
                    staff_x = sx + 88
                    c.create_line(staff_x, ground - 128, staff_x + 5, ground - 94,
                                  fill="#805a3e", width=5)
                    c.create_oval(staff_x - 4, ground - 139, staff_x + 8, ground - 127,
                                  fill="#c9b7ff", outline="#fff0c9", width=2)
                    c.create_oval(staff_x - 1, ground - 136, staff_x + 5, ground - 130,
                                  fill="#f4e4ff", outline="")
                    c.create_text(staff_x + 3, ground - 150,
                                  text="뉴턴의 지팡이 · 구매 완료" if self.staff_owned else "뉴턴의 지팡이 · 100 G",
                                  fill="#ffe2a2", font=("TkDefaultFont", 9, "bold"))

            bird_x = self.sx(SHOP_BIRD_X)
            bird_y = ground
            c.create_oval(bird_x - 20, bird_y - 31, bird_x + 18, bird_y - 3,
                          fill="#343647", outline="#aaa0b0", width=2)
            c.create_polygon(bird_x - 11, bird_y - 26, bird_x - 30, bird_y - 18,
                             bird_x - 17, bird_y - 9, bird_x + 3, bird_y - 14,
                             fill="#58596a", outline="#b1a4a7", width=1)
            c.create_oval(bird_x + 5, bird_y - 40, bird_x + 24, bird_y - 21,
                          fill="#303342", outline="#c6b99c", width=2)
            c.create_oval(bird_x + 16, bird_y - 32, bird_x + 19, bird_y - 29,
                          fill="#ffe69a", outline="")
            c.create_polygon(bird_x + 22, bird_y - 32, bird_x + 32, bird_y - 29,
                             bird_x + 22, bird_y - 26, fill="#d59b5c", outline="")
            c.create_text(bird_x, bird_y - 52, text="비둘기 · 회복 50 G · 가호 소환 500 G",
                          fill="#baf2cf", font=("TkDefaultFont", 9, "bold"))

            lever_x = self.sx(SHOP_LEVER_X)
            door_x = self.sx(SHOP_EXIT_X)
            # Keep the sealed exit visible beside its control so the route is
            # clear before the player chooses to leave the safe room.
            door_fill = "#53604f" if self.shop_exit_open else "#393441"
            door_outline = "#9edfd2" if self.shop_exit_open else "#d7b979"
            self.rect(door_x - 68, ground - 181, door_x + 68, ground,
                      door_fill, door_outline)
            c.create_arc(door_x - 68, ground - 238, door_x + 68, ground - 112,
                         start=0, extent=180, style="arc", outline=door_outline, width=4)
            c.create_rectangle(door_x - 39, ground - 144, door_x + 39, ground,
                               fill="#17202c" if self.shop_exit_open else "#51444d",
                               outline=door_outline, width=2)
            if self.shop_exit_open:
                c.create_text(door_x, ground - 110, text="다음 구역 →",
                              fill="#d9fff0", font=("TkDefaultFont", 9, "bold"))
            else:
                c.create_line(door_x - 24, ground - 116, door_x + 24, ground - 116,
                              fill="#9c7d58", width=3)
                c.create_text(door_x, ground - 202, text="닫힌 출구",
                              fill="#e7d6b3", font=("TkDefaultFont", 9, "bold"))
            c.create_rectangle(lever_x - 18, ground - 19, lever_x + 18, ground,
                               fill="#4c4338", outline="#e0c27e", width=2)
            c.create_oval(lever_x - 7, ground - 58, lever_x + 7, ground - 44,
                          fill="#e3c784", outline="#fff0cf", width=2)
            if self.shop_exit_open:
                c.create_line(lever_x, ground - 51, lever_x + 28, ground - 38,
                              fill="#b9d2c1", width=6, capstyle="round")
                c.create_text(lever_x, ground - 82, text="레버 작동 완료",
                              fill="#c7efca", font=("TkDefaultFont", 9, "bold"))
            else:
                c.create_line(lever_x, ground - 51, lever_x - 4, ground - 88,
                              fill="#c6a969", width=6, capstyle="round")
                c.create_text(lever_x, ground - 100,
                              text=f"{self.key_label(self.controls['interact'])} 레버로 출구 열기",
                              fill="#fff0c9", font=("TkDefaultFont", 9, "bold"))

        if self.player["x"] < self.safe_start_end and not self.in_shop:
            safe_x, safe_y = self.sx(245), self.sy(self.ground - 142)
            c.create_rectangle(safe_x - 82, safe_y - 23, safe_x + 82, safe_y + 23,
                               fill="#273b48", outline="#9ac6bb", width=2)
            c.create_text(safe_x, safe_y - 4, text="SAFE START",
                          fill="#d9efd8", font=("TkDefaultFont", 10, "bold"))
            c.create_text(safe_x, safe_y + 11, text="적이 나타나지 않는 준비 구역",
                          fill="#b8d4ca", font=("TkDefaultFont", 7, "bold"))

        # Physical coin drops remain in the room until the player touches them.
        for coin in self.coin_drops:
            if not self.world_rect_visible(coin["x"] - 14, coin["y"] - 12,
                                           coin["x"] + 14, coin["y"] + 12):
                continue
            cx, cy = self.sx(coin["x"]), self.sy(coin["y"] + math.sin(coin["age"] * .16) * 2)
            c.create_oval(cx - 12, cy - 9, cx + 12, cy + 9,
                          fill="#7c532d", outline="#372c34", width=2)
            c.create_oval(cx - 9, cy - 8, cx + 9, cy + 8,
                          fill="#f2b94d", outline="#fff0a8", width=2)
            c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                          fill="#ffd976", outline="#c48438", width=1)
            c.create_line(cx - 1, cy - 4, cx - 1, cy + 4, fill="#fff4c2", width=2)

        for enemy in self.enemies:
            # Keep attack tell animations even when their shooter is just offscreen;
            # hidden idle grunts have no visible pixels and need no Canvas items.
            if (enemy["rank"] == "mob" and enemy["state"] not in ("notice", "warning", "locked")
                    and not self.world_rect_visible(enemy["x"] - 120, enemy["y"] - 120,
                                                    enemy["x"] + enemy["w"] + 120,
                                                    enemy["y"] + enemy["h"] + 120)):
                continue
            self.draw_enemy(enemy)
        if self.round_clear and self.bird_x is not None:
            bx, by = self.sx(self.bird_x), self.sy(self.ground)
            # Cloaked silhouette, shadowed hood and muted metallic details make
            # the familiar pigeon shape feel like a secretive traveling dealer.
            c.create_polygon(bx - 23, by - 29, bx - 13, by - 41, bx + 14, by - 38,
                             bx + 25, by - 21, bx + 19, by - 4, bx - 19, by - 4,
                             fill="#242838", outline="#777286", width=2)
            c.create_oval(bx - 18, by - 29, bx + 17, by - 7,
                          fill="#373849", outline="#171b28", width=2)
            c.create_polygon(bx - 10, by - 25, bx - 25, by - 17, bx - 15, by - 10,
                             bx + 2, by - 14, bx + 8, by - 19,
                             fill="#545567", outline="#92909a", width=1)
            c.create_oval(bx + 4, by - 43, bx + 25, by - 22,
                          fill="#2a2d3e", outline="#a09381", width=2)
            c.create_arc(bx + 2, by - 45, bx + 28, by - 19, start=195, extent=150,
                         style="arc", outline="#777286", width=3)
            c.create_oval(bx + 12, by - 34, bx + 15, by - 31,
                          fill="#f3d37f", outline="#fff3c2")
            c.create_polygon(bx + 23, by - 33, bx + 34, by - 29, bx + 23, by - 26,
                             fill="#bf8855", outline="#f2cc83")
            c.create_line(bx - 7, by - 5, bx - 9, by, fill="#a47b5e", width=2)
            c.create_line(bx + 5, by - 5, bx + 7, by, fill="#a47b5e", width=2)
            c.create_rectangle(bx - 23, by - 20, bx - 14, by - 9,
                               fill="#4c423e", outline="#c7a76e", width=1)
            c.create_line(bx - 21, by - 18, bx - 16, by - 18, fill="#e3ce9e", width=1)
            c.create_text(bx, by - 53, text="회색 망토의 비둘기", fill="#d9d1c2",
                          font=("TkDefaultFont", 9, "bold"))
        for shot in self.enemy_shots:
            if shot[6] == "column":
                sx = self.sx(shot[0])
                if sx < -24 or sx > self.w + 24:
                    continue
                self.rect(sx - 18, self.sy(65), sx + 18, ground, "#756b5d", "#c5a96f")
                self.rect(sx - 10, self.sy(72), sx + 10, ground - 3, "#b9a477", "#e8d3a6")
                self.canvas.create_line(sx - 22, self.sy(78), sx + 22, self.sy(78),
                                        fill="#fff0c9", width=3)
                self.rect(sx - 15, self.sy(68), sx + 15, self.sy(75), "#c5a96f")
            else:
                sx = self.sx(shot[0])
                sy = self.sy(shot[1])
                if sx < -40 or sx > self.w + 40 or sy < -40 or sy > self.h + 40:
                    continue
                if shot[6] == "bullet":
                    length = max(1, math.hypot(shot[2], shot[3]))
                    ux, uy = shot[2] / length, shot[3] / length
                    self.canvas.create_line(sx - ux * 17, sy - uy * 17,
                                            sx + ux * 8, sy + uy * 8,
                                            fill="#d84f3f", width=5, capstyle="round")
                    self.canvas.create_line(sx - ux * 12, sy - uy * 12,
                                            sx + ux * 7, sy + uy * 7,
                                            fill="#ffd68a", width=2, capstyle="round")
                    self.canvas.create_oval(sx - 3, sy - 3, sx + 3, sy + 3,
                                            fill="#fff0c5", outline="")
                elif shot[6] == "arrow":
                    length = max(1, math.hypot(shot[2], shot[3]))
                    ux, uy = shot[2] / length, shot[3] / length
                    px, py = -uy, ux
                    tail_x, tail_y = sx - ux * 18, sy - uy * 18
                    base_x, base_y = sx + ux * 4, sy + uy * 4
                    tip_x, tip_y = sx + ux * 13, sy + uy * 13
                    self.canvas.create_line(tail_x, tail_y, base_x, base_y,
                                            fill="#8b6245", width=3)
                    self.canvas.create_polygon(tip_x, tip_y,
                                               base_x + px * 5, base_y + py * 5,
                                               base_x - px * 5, base_y - py * 5,
                                               fill="#d8d2c1", outline="#fff0cf")
                    self.canvas.create_line(tail_x + ux * 3 + px * 4, tail_y + uy * 3 + py * 4,
                                            tail_x + ux * 9, tail_y + uy * 9,
                                            tail_x + ux * 3 - px * 4, tail_y + uy * 3 - py * 4,
                                            fill="#dfc68c", width=2)
                elif shot[6] == "bolt":
                    length = max(1, math.hypot(shot[2], shot[3]))
                    ux, uy = shot[2] / length, shot[3] / length
                    self.canvas.create_line(sx - ux * 18, sy - uy * 18, sx + ux * 10, sy + uy * 10,
                                            fill="#fff0cf", width=3, arrow="last")
                    self.canvas.create_line(sx - ux * 16 - uy * 2, sy - uy * 16 + ux * 2,
                                            sx + ux * 4 - uy * 2, sy + uy * 4 + ux * 2,
                                            fill="#55c7ce", width=1)
                else:
                    stone = shot[6] == "stone"
                    velocity = max(1, math.hypot(shot[2], shot[3]))
                    ux, uy = shot[2] / velocity, shot[3] / velocity
                    self.canvas.create_line(sx - ux * 22, sy - uy * 22,
                                            sx - ux * 7, sy - uy * 7,
                                            fill="#d5bd8d", width=4)
                    self.canvas.create_oval(sx - 10, sy - 8, sx + 10, sy + 8,
                                            fill="#332f3d", outline="#191925", width=2)
                    self.canvas.create_oval(sx - 8, sy - 7, sx + 8, sy + 6,
                                            fill="#74634b" if stone else "#a58c66",
                                            outline="#d0b98a", width=2)
                    self.canvas.create_oval(sx - 5, sy - 5, sx - 1, sy - 2,
                                            fill="#d8c39b", outline="")
        for shot in self.player_shots:
            sx = self.sx(shot[0])
            sy = self.sy(shot[1])
            trail_margin = 64 if len(shot) > 6 and shot[6] == "handcannon" else 24
            if (sx < -trail_margin or sx > self.w + trail_margin
                    or sy < -trail_margin or sy > self.h + trail_margin):
                continue
            if len(shot) > 6 and shot[6] == "handcannon":
                direction = 1 if shot[2] > 0 else -1
                self.canvas.create_line(sx - direction * 24, sy, sx + direction * 17, sy,
                                        fill="#437e88", width=9)
                self.canvas.create_line(sx - direction * 15, sy, sx + direction * 15, sy, fill="#ffdf9d", width=4, arrow="last")
                self.canvas.create_oval(sx - 7, sy - 7, sx + 7, sy + 7, fill="#6de0d5", outline="#d8fff1", width=2)
                for trail in range(3):
                    self.canvas.create_line(sx - direction * (22 + trail * 8), sy - 5 + trail * 5,
                                            sx - direction * (32 + trail * 8), sy - 5 + trail * 5,
                                            fill="#e5be72", width=1)
            else:
                self.canvas.create_oval(sx - 15, sy - 9, sx + 15, sy + 9,
                                        fill="#c9a864", outline="")
                self.canvas.create_line(sx - 17, sy, sx + 18, sy,
                                        fill="#fff4cc", width=4, arrow="last")
                self.canvas.create_oval(sx - 4, sy - 4, sx + 4, sy + 4,
                                        fill="#fffef0", outline="#e9c975", width=1)
        if self.in_shop:
            # Temporary study-shop: bookshelves and a practice corner; no economy yet.
            for shelf_x in (180, 700):
                sx = self.sx(shelf_x)
                self.rect(sx, ground - 176, sx + 170, ground - 18, "#433a32", "#8c7552")
                self.rect(sx + 8, ground - 124, sx + 162, ground - 118, "#a0875e")
                self.rect(sx + 8, ground - 70, sx + 162, ground - 64, "#a0875e")
                for book_x in range(int(sx + 14), int(sx + 158), 22):
                    color = ("#8e5147", "#647969", "#b18c53")[(book_x // 22) % 3]
                    self.rect(book_x, ground - 166, book_x + 12, ground - 126, color)
                    self.rect(book_x + 3, ground - 113, book_x + 16, ground - 72, color)
            door_x = self.sx(1080)
            self.rect(door_x - 54, ground - 220, door_x + 54, ground, "#4c4338", "#e0c27e")
            self.canvas.create_arc(door_x - 54, ground - 268, door_x + 54, ground - 150, start=0, extent=180, fill="#4c4338", outline="#e0c27e", width=3)
            self.rect(door_x - 32, ground - 176, door_x + 32, ground, "#17202c", "#c5ad79")
            self.canvas.create_text(door_x, ground - 136, text="↑", fill="#fff0cf", font=("TkDefaultFont", 20, "bold"))
        for meteor in self.meteors:
            mx, my = self.sx(meteor["x"]), self.sy(meteor["y"])
            tx, ty = self.sx(meteor["x"]), self.sy(meteor["target_y"])
            if mx < -220 or mx > self.w + 220 or my < -540 or my > self.h + 80:
                continue
            c.create_oval(tx - meteor["radius"], ty - 18,
                          tx + meteor["radius"], ty + 18,
                          outline="#ff9c71", width=3, dash=(8, 5))
            c.create_text(tx, ty - 30, text=f"운석 낙하 {meteor['timer'] / 60:.1f}",
                          fill="#ffe0a3", font=("TkDefaultFont", 10, "bold"))
            c.create_line(mx - 5, my - 44, mx + 5, my - 18,
                          fill="#ff6c46", width=14, capstyle="round")
            c.create_line(mx - 2, my - 38, mx + 2, my - 18,
                          fill="#ffd274", width=7, capstyle="round")
            c.create_oval(mx - 13, my - 22, mx + 13, my + 4,
                          fill="#8e4b43", outline="#ffe5aa", width=2)
            c.create_oval(mx - 5, my - 16, mx + 2, my - 9,
                          fill="#fff0ba", outline="")

        for effect in self.effects:
            # Every effect fits inside this generous envelope, including the
            # oversized whale-breach splash. Skip only effects fully outside it.
            ex, ey = effect[1], effect[2]
            if not self.world_rect_visible(ex - 500, ey - 500, ex + 500, ey + 500):
                continue
            self.draw_effect(effect)
        self.draw_player()
        self.draw_hud()
        self.draw_minimap()
        if self.blessing_menu:
            self.draw_blessing_menu()
        if self.stats_open:
            self.draw_stats()
        if self.settings_open:
            self.draw_settings()

    def draw_minimap(self):
        c = self.canvas
        left, top, width, height = self.w - 226, 72, 210, 112
        c.create_rectangle(left - 4, top - 4, left + width + 4, top + height + 4,
                           fill="#131725", outline="#f2ce83", width=2)
        c.create_rectangle(left, top, left + width, top + height,
                           fill="#24283d", outline="#827b8b", width=1)
        for grid_x in range(left + 16, left + width, 32):
            c.create_line(grid_x, top + 20, grid_x, top + height - 5,
                          fill="#41455a", dash=(2, 5))
        for grid_y in range(top + 28, top + height, 24):
            c.create_line(left + 5, grid_y, left + width - 5, grid_y,
                          fill="#41455a", dash=(2, 5))
        c.create_text(left + 8, top + 7, anchor="nw", text="FIELD MAP",
                      fill="#fff0cf", font=("TkDefaultFont", 8, "bold"))
        x0, y0 = left + 8, top + 24
        map_w, map_h = width - 16, height - 32

        def point(wx, wy):
            return x0 + wx / WORLD * map_w, y0 + wy / WORLD_H * map_h

        ground_x1, ground_y = point(0, self.ground)
        ground_x2, _ = point(WORLD, self.ground)
        cursor = 0
        for pit in self.pits:
            pit_left, _ = point(pit["left"], self.ground)
            pit_right, _ = point(pit["right"], self.ground)
            c.create_line(point(cursor, self.ground)[0], ground_y,
                          pit_left, ground_y, fill="#d39a91", width=2)
            _px1, pit_bottom = point(pit["left"], pit["bottom"])
            _px2, _ = point(pit["right"], pit["bottom"])
            c.create_rectangle(pit_left, ground_y, pit_right, pit_bottom,
                               fill="#171b2b", outline="#bf6a78", width=1)
            c.create_line(pit_left + 1, pit_bottom - 1,
                          pit_right - 1, pit_bottom - 1, fill="#f17876", width=2)
            cursor = pit["right"]
        c.create_line(point(cursor, self.ground)[0], ground_y,
                      ground_x2, ground_y, fill="#d39a91", width=2)
        for a, b, rise in self.platforms:
            px1, py = point(a, self.ground - rise)
            px2, _ = point(b, self.ground - rise)
            c.create_line(px1, py, px2, py, fill="#f4c78f", width=2)
        for wx1, wy1, wx2, wy2 in self.obstacles:
            px1, py1 = point(wx1, wy1)
            px2, py2 = point(wx2, wy2)
            c.create_rectangle(px1, py1, px2, py2, fill="#777186", outline="#d1b68f", width=1)
        for crate in self.tnt_crates:
            cx, cy = point(crate["x"] + crate["w"] / 2,
                           crate["y"] + crate["h"] / 2)
            c.create_rectangle(cx - 2, cy - 3, cx + 2, cy + 3,
                               fill="#ff7769", outline="#ffe1ae")
        room_left, _ = point(self.room_wave_index * ROOM_WIDTH, 0)
        room_right, _ = point((self.room_wave_index + 1) * ROOM_WIDTH, 0)
        c.create_rectangle(room_left, y0, room_right, y0 + map_h,
                           outline="#ffe293", width=2)
        for boundary in range(ROOM_WIDTH, WORLD, ROOM_WIDTH):
            bx, _ = point(boundary, 0)
            c.create_line(bx, y0, bx, y0 + map_h, fill="#6e6e91", dash=(2, 3))
        for enemy in self.enemies:
            color = "#f2a0a5" if enemy["rank"] in ("boss", "scholar") else "#62d4cf" if enemy["kind"] in RANGED_MOBS else "#ff987f"
            ex, ey = point(enemy["x"] + enemy["w"] / 2, enemy["y"] + enemy["h"] / 2)
            c.create_oval(ex - 3, ey - 3, ex + 3, ey + 3, fill=color, outline="")
        for _kind, wx, _rank in self.spawn_queue:
            ex, ey = point(wx, self.ground - 36)
            c.create_oval(ex - 2, ey - 2, ex + 2, ey + 2, outline="#ffe0a3", width=1)
        px, py = point(self.player["x"] + PLAYER_W / 2, self.player["y"] + PLAYER_H / 2)
        c.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#fff17a", outline="#fff8d9")
        view_left, view_top = point(self.camera, self.camera_y)
        view_right, view_bottom = point(self.camera + self.w, self.camera_y + self.h)
        c.create_rectangle(view_left, view_top, view_right, view_bottom, outline="#ffffff", width=1)
        if self.round_clear and self.exit_door_x is not None:
            dx, dy = point(self.exit_door_x, self.ground - 100)
            c.create_polygon(dx, dy - 5, dx + 5, dy, dx, dy + 5, dx - 5, dy, fill="#ffe17c", outline="#fff8d9")

    def draw_player(self):
        p = self.player
        c = self.canvas
        x, y = self.sx(p["x"]), self.sy(p["y"])
        running = (self.action_down("move_left") or self.action_down("move_right")) and p["grounded"]
        action = self.player_action if self.frame < self.player_action_until else ""
        if self.frame < self.dash_until:
            pose = "dash"
        elif action == "double_jump":
            pose = "double_jump"
        elif not p["grounded"]:
            pose = "jump" if p["vy"] < 0 else "fall"
        else:
            pose = ("run_a" if self.frame // 3 % 2 == 0 else "run_b") if running else "idle"
        pit_id = p.get("pit_id")
        shadow_floor = (self.pits[pit_id]["bottom"]
                        if pit_id is not None and pit_id < len(self.pits) else self.ground)
        shadow_y = self.sy(p["y"] + PLAYER_H) if p["grounded"] else self.sy(shadow_floor)
        shadow_x = x - (PLAYER_SPRITE_W - PLAYER_W) / 2
        c.create_oval(shadow_x + 2, shadow_y - 3, shadow_x + PLAYER_SPRITE_W - 2,
                      shadow_y + 2, fill="#2e2b43", outline="")
        run_phase = self.frame // 4 % 2
        body_bob = (2 if run_phase == 0 else -2) if running else round(math.sin(self.frame * .075))
        body_bob = -3 if not p["grounded"] and p["vy"] < 0 else 2 if not p["grounded"] else body_bob
        if pose == "dash":
            body_bob = 0
        y += body_bob
        sprite_x, sprite_y = x - (PLAYER_SPRITE_W - PLAYER_W) / 2, y - 2
        c.create_image(sprite_x, sprite_y, image=self.player_images[(pose, p["face"])], anchor="nw")
        if self.frame < self.dash_until:
            direction = p.get("dash_dir", p["face"])
            for streak in range(4):
                sy = y + 14 + streak * 9
                c.create_line(x - direction * (12 + streak * 5), sy,
                              x - direction * (52 + streak * 7), sy - 2,
                              fill="#9dece5" if streak % 2 == 0 else "#e6d79e", width=2)
            c.create_rectangle(sprite_x - 1, sprite_y + 3,
                               sprite_x + PLAYER_SPRITE_W + 1, sprite_y + PLAYER_SPRITE_H - 2,
                               outline="#a8fff0", width=2)
        face_x = x + (27 if p["face"] > 0 else 5)
        # Keep only a small facing cue over the simplified sprite.
        self.rect(face_x - 1, y + 11, face_x + 2, y + 14, "#fff0c9")
        if pose == "idle":
            self.rect(x + 6, y + 51, x + 14, y + 54, "#65546a")
            self.rect(x + 19, y + 51, x + 27, y + 54, "#65546a")
        # Distinct poses for gun, formula skills, and sword attacks.
        sx, sy = x + PLAYER_W / 2 + p["face"] * 2, y + 31
        if action == "double_jump":
            self.pixel_line(sx - p["face"] * 4, sy + 1, sx - p["face"] * 9, sy - 7, "#bf8067")
            self.pixel_line(sx + p["face"] * 4, sy + 1, sx + p["face"] * 9, sy - 8, "#bf8067")
            self.pixel_line(sx + p["face"] * 9, sy - 8, sx + p["face"] * 13, sy - 12, "#f6e9cb")
        elif action == "dash":
            self.pixel_line(sx - p["face"] * 5, sy, sx - p["face"] * 14, sy + 8, "#bf8067")
            self.pixel_line(sx + p["face"] * 2, sy - 2, sx + p["face"] * 14, sy - 9, "#bf8067")
            self.pixel_line(sx + p["face"] * 14, sy - 9, sx + p["face"] * 26, sy - 14, "#fff0cf")
        elif action == "land":
            self.pixel_line(sx - 5, sy, sx - 13, sy + 8, "#bf8067")
            self.pixel_line(sx + 5, sy, sx + 13, sy + 8, "#bf8067")
        elif action == "gun":
            gun_x = sx + p["face"] * 15
            self.pixel_line(sx, sy, sx + p["face"] * 8, sy - 2, "#bf8067")
            self.rect(gun_x - 2, sy - 5, gun_x + 9 * p["face"], sy + 1, "#a87958", "#ffe0a3")
            self.pixel_line(gun_x + p["face"] * 8, sy - 2, gun_x + p["face"] * 14, sy - 2, "#66d8d1")
        elif action == "lever":
            hand_x, hand_y = sx + p["face"] * 7, sy - 9
            self.pixel_line(sx, sy, hand_x, hand_y, "#bf8067")
            self.pixel_line(hand_x, hand_y, hand_x + p["face"] * 7, hand_y - 14, "#f6e9cb")
        elif action == "momentum":
            hand_x, hand_y = sx + p["face"] * 10, sy + 1
            self.pixel_line(sx, sy, hand_x, hand_y, "#bf8067")
            self.pixel_line(hand_x, hand_y, hand_x + p["face"] * 22, hand_y - 8, "#fff0cf")
        elif action == "gravity":
            hand_x, hand_y = sx + p["face"] * 8, sy + 9
            self.pixel_line(sx, sy, hand_x, hand_y, "#bf8067")
            self.pixel_line(hand_x, hand_y, hand_x + p["face"] * 8, hand_y + 15, "#f6e9cb")
        elif action in ("staff", "meteor"):
            hand_x, hand_y = sx + p["face"] * 9, sy - 7
            self.pixel_line(sx, sy, hand_x, hand_y, "#bf8067")
            self.pixel_line(hand_x, hand_y, hand_x + p["face"] * 8, hand_y - 12, "#f6e9cb")
        elif action == "slash":
            progress = min(1, max(0, (self.frame - (self.attack_until - 20)) / 19))
            blade_len = 47
            # Familiar one-handed side slash: chamber the hand beside the
            # shoulder, then sweep it across the torso and slightly downward.
            swing = min(1, max(0, (progress - .12) / .68))
            eased = swing * swing * (3 - 2 * swing)
            shoulder_x, shoulder_y = sx + p["face"] * 6, sy - 4
            elbow_x = sx + p["face"] * (1 + eased * 11)
            elbow_y = sy - 10 + eased * 9
            hand_x = sx + p["face"] * (-1 + eased * 21)
            hand_y = sy - 20 + eased * 18
            self.canvas.create_line(shoulder_x, shoulder_y, elbow_x, elbow_y,
                                    fill="#7f4c4b", width=7, capstyle="round")
            self.canvas.create_line(shoulder_x, shoulder_y, elbow_x, elbow_y,
                                    fill="#bf8067", width=4, capstyle="round")
            self.canvas.create_line(elbow_x, elbow_y, hand_x, hand_y,
                                    fill="#7f4c4b", width=6, capstyle="round")
            self.canvas.create_line(elbow_x, elbow_y, hand_x, hand_y,
                                    fill="#d99177", width=3, capstyle="round")
            self.canvas.create_oval(hand_x - 4, hand_y - 4, hand_x + 4, hand_y + 4,
                                    fill="#e8b58f", outline="#70464a", width=1)
            blade_angle = -2.15 + eased * 2.48
            guard_x = hand_x + p["face"] * math.cos(blade_angle) * 3
            guard_y = hand_y + math.sin(blade_angle) * 3
            tip_x = guard_x + p["face"] * math.cos(blade_angle) * blade_len
            tip_y = guard_y + math.sin(blade_angle) * blade_len
            self.canvas.create_line(hand_x, hand_y, guard_x, guard_y,
                                    fill="#d3ad66", width=4, capstyle="round")
            # All blade layers share the same straight endpoints and fixed length.
            self.canvas.create_line(guard_x, guard_y, tip_x, tip_y,
                                    fill="#344252", width=8, capstyle="round")
            self.canvas.create_line(guard_x, guard_y, tip_x, tip_y,
                                    fill="#b7cbd1", width=5, capstyle="round")
            nx, ny = -math.sin(blade_angle), math.cos(blade_angle)
            self.canvas.create_line(guard_x + nx, guard_y + ny, tip_x + nx, tip_y + ny,
                                    fill="#f4fff2", width=1, capstyle="round")
            self.canvas.create_line(guard_x - p["face"] * 4, guard_y - 4,
                                    guard_x + p["face"] * 4, guard_y + 4,
                                    fill="#d3ad66", width=3, capstyle="round")
        elif not p["grounded"]:
            # Arms counter-swing in the air, changing from tucked on ascent to
            # spread for balance while descending.
            if p["vy"] < 0:
                self.pixel_line(sx - p["face"] * 3, sy, sx - p["face"] * 12, sy - 13, "#bf8067")
                self.pixel_line(sx + p["face"] * 3, sy, sx + p["face"] * 10, sy - 16, "#bf8067")
            else:
                self.pixel_line(sx - p["face"] * 2, sy, sx - p["face"] * 12, sy - 7, "#bf8067")
                self.pixel_line(sx + p["face"] * 2, sy, sx + p["face"] * 13, sy - 9, "#bf8067")
        else:
            swing = math.sin(self.frame * .48) * (10 if running else 2)
            self.pixel_line(sx, sy, sx - p["face"] * 5 - swing * .25, sy + 8 + swing * .3, "#bf8067")
            ex, ey, hx, hy = sx + p["face"] * 5 + swing * .2, sy + 5, sx + p["face"] * 10 + swing, sy + 8 + swing * .5
            if self.frame < self.attack_until:
                progress = 1 - (self.attack_until - self.frame) / 15
                if progress < .3:
                    hx, hy = sx - p["face"] * 10, sy - 4
                else:
                    a = min(1, (progress - .3) / .7)
                    ex, ey = sx + p["face"] * (6 + a * 3), sy - a * 3
                    hx, hy = sx + p["face"] * (10 + a * 12), sy - 6 + a * 17
            self.pixel_line(sx, sy, ex, ey, "#e88d91")
            self.pixel_line(ex, ey, hx, hy, "#fff0cf")
            for k in range(4):
                self.rect(hx + p["face"] * k * 3, hy - 7 - k * 1.5, hx + p["face"] * (k * 3 + 3), hy - 4 - k * 1.5, "#fff0cf" if k < 3 else "#ffd17e")
        if self.staff_owned:
            hand_x, hand_y = sx + p["face"] * 12, sy + 7
            staff_x = hand_x + p["face"] * 5
            self.canvas.create_line(hand_x, hand_y, staff_x, hand_y - 38,
                                    fill="#493646", width=7, capstyle="round")
            self.canvas.create_line(hand_x, hand_y, staff_x, hand_y - 38,
                                    fill="#c09a62", width=3, capstyle="round")
            self.canvas.create_oval(staff_x - 7, hand_y - 48, staff_x + 7, hand_y - 34,
                                    fill="#9682cf", outline="#f3e1b0", width=2)
            self.canvas.create_oval(staff_x - 3, hand_y - 45, staff_x + 3, hand_y - 39,
                                    fill="#f5eaff", outline="")
        if self.frame < self.parry_until:
            self.rect(sprite_x - 3, sprite_y - 3,
                      sprite_x + PLAYER_SPRITE_W + 3, sprite_y + PLAYER_SPRITE_H + 3,
                      "", "#b7f2ce")

    def pixel_line(self, x1, y1, x2, y2, color):
        steps = max(1, int(max(abs(x2 - x1), abs(y2 - y1)) / PX))
        for i in range(steps + 1):
            t = i / steps
            x = round((x1 + (x2 - x1) * t) / PX) * PX
            y = round((y1 + (y2 - y1) * t) / PX) * PX
            self.rect(x - 2, y - 2, x + 2, y + 2, color)

    def nearest_floor_under(self, x1, x2, y_bottom):
        """Find the closest floor surface below a melee telegraph's low edge."""
        ground_spans = [(0.0, float(WORLD))]
        for pit in self.pits:
            remaining = []
            for left, right in ground_spans:
                if pit["right"] <= left or pit["left"] >= right:
                    remaining.append((left, right))
                    continue
                if pit["left"] > left:
                    remaining.append((left, pit["left"]))
                if pit["right"] < right:
                    remaining.append((pit["right"], right))
            ground_spans = remaining

        surfaces = [(self.ground, left, right) for left, right in ground_spans]
        surfaces.extend((self.ground - rise, left, right)
                        for left, right, rise in self.platforms)
        overlapping = []
        for floor_y, left, right in surfaces:
            visible_left, visible_right = max(x1, left), min(x2, right)
            if visible_right > visible_left:
                overlapping.append((floor_y, visible_left, visible_right))
        if not overlapping:
            return None

        below = [surface for surface in overlapping if surface[0] >= y_bottom]
        choices = below or overlapping
        floor_y, left, right = min(
            choices,
            key=lambda surface: (surface[0] - y_bottom) if below else abs(surface[0] - y_bottom),
        )
        return left, right, floor_y

    def draw_floor_warning_stripe(self, x1, x2, y_bottom, alert, direction=None):
        lane = self.nearest_floor_under(x1, x2, y_bottom)
        if lane is None:
            return None
        floor_left, floor_right, floor_y = lane
        stripe_x1, stripe_x2 = self.sx(floor_left), self.sx(floor_right)
        stripe_y = self.sy(floor_y) - 5
        self.canvas.create_line(stripe_x1, stripe_y, stripe_x2, stripe_y,
                                fill="#c51d35", width=10, capstyle="butt")
        if direction is None:
            self.canvas.create_line(stripe_x1, stripe_y, stripe_x2, stripe_y,
                                    fill="#ff968c", width=2, dash=(6, 4))
        else:
            self.canvas.create_line(stripe_x1, stripe_y, stripe_x2, stripe_y,
                                    fill=alert, width=2,
                                    arrow="last" if direction > 0 else "first")
        return stripe_x1, stripe_x2, stripe_y

    def draw_enemy(self, enemy):
        x, y = self.sx(enemy["x"]), self.sy(enemy["y"])
        w, h = enemy["w"], enemy["h"]
        rank = enemy["rank"]
        if rank == "boss" and enemy.get("boss_phase") == "normal":
            y -= math.sin(self.frame * .045) * 1.5
        elif rank != "boss" and enemy.get("grounded") and enemy["state"] in ("idle", "cooldown"):
            y -= math.sin(self.frame * .13 + enemy.get("move_phase", 0)) * 1.2
        c = self.canvas
        accent = ERAS[self.chapter]["accent"]
        # Contact shadow anchors airborne and grounded silhouettes to their lane.
        shadow_color = self.color_mix(ERAS[self.chapter]["ground"], "#171724", .32)
        shadow_y = min(self.sy(self.ground), y + h + 7)
        c.create_oval(x + w * .12, shadow_y - 4, x + w * .88, shadow_y + 3,
                      fill=shadow_color, outline="")
        if rank == "mob" and enemy["state"] in ("notice", "warning", "locked"):
            mark_x, mark_y = x + w / 2, y - 25
            c.create_oval(mark_x - 16, mark_y - 16, mark_x + 16, mark_y + 16,
                          fill="#fa263a", outline="#fff1e4", width=2)
            c.create_text(mark_x, mark_y - 1, text="!", fill="#fffaf2",
                          font=("TkDefaultFont", 24, "bold"))
        if enemy["state"] == "charge":
            direction = enemy.get("face", 1)
            for streak in range(2 if rank == "mob" else 4):
                trail_y = y + h * (.35 + streak * .12)
                c.create_line(x + w / 2 - direction * 12, trail_y,
                              x + w / 2 - direction * (34 + streak * 13), trail_y - 3,
                              fill="#ffd49a" if streak % 2 else "#e9a69c", width=2)
        if rank == "scholar":
            aura_x, aura_y = x + w / 2, y + h / 2
            aura_r = 238
            c.create_oval(aura_x - aura_r, aura_y - aura_r * .62,
                          aura_x + aura_r, aura_y + aura_r * .62,
                          outline="#8d8bd2", dash=(3, 8), width=2)
            c.create_oval(aura_x - aura_r * .72, aura_y - aura_r * .44,
                          aura_x + aura_r * .72, aura_y + aura_r * .44,
                          outline="#b3a5e2", dash=(2, 10), width=1)
        if rank == "boss" and enemy["state"] == "catapult_flight":
            direction = 1 if enemy.get("flight_target_x", 0) >= enemy.get("flight_start_x", 0) else -1
            for streak in range(5):
                trail_y = y + 66 + streak * 29
                c.create_line(x + w / 2 - direction * 34, trail_y,
                              x + w / 2 - direction * (92 + streak * 13), trail_y - 8,
                              fill="#f3dda1" if streak % 2 else "#c5e7df",
                              width=3 if streak == 0 else 2)
        if enemy["state"] in ("notice", "warning", "locked"):
            alert = self.warning_color(enemy)
            danger = "#c51d35"
            if enemy["action"] in ("crossbow", "fan", "intercept", "gunshot"):
                tx, ty = self.sx(enemy.get("target_x", 0)), self.sy(enemy.get("target_y", 0))
                origin_x, origin_y = x + w / 2, y + h * .48
                self.canvas.create_line(origin_x, origin_y, tx, ty,
                                        fill="#ef9299", width=4, dash=(10, 8),
                                        arrow="last")
                aim_label = (f"공격까지 {(enemy['timer'] + 18) / 60:.1f}"
                             if enemy["state"] == "notice"
                             else f"조준 {enemy['timer'] / 60:.1f}")
                self.canvas.create_text(tx, ty - 18,
                                        text=(f"발사까지 {enemy['timer'] / 60:.1f}"
                                              if enemy["state"] == "locked"
                                              else aim_label),
                                        fill=alert, font=("TkDefaultFont", 9, "bold"))
            elif enemy["action"] == "slam":
                target_x = enemy.get("target_x", 0)
                target_y = enemy.get("target_y", self.ground)
                if rank == "mob" and enemy["kind"] in MELEE_MOBS:
                    vertical_limit = h * .42
                    lane = self.draw_floor_warning_stripe(
                        target_x - 76, target_x + 76,
                        target_y + vertical_limit, alert)
                    label_x = self.sx(target_x) if lane is None else (lane[0] + lane[1]) / 2
                    label_y = self.sy(target_y) - 24 if lane is None else lane[2] - 20
                    c.create_text(label_x, label_y, text=f"{enemy['timer'] / 60:.1f}",
                                  fill=alert, font=("TkDefaultFont", 10, "bold"))
                else:
                    tx, hit_y = self.sx(target_x), self.sy(target_y)
                    self.canvas.create_rectangle(tx - 76, hit_y - 105, tx + 76, hit_y + 105,
                                                 fill=danger, stipple="gray12", outline=alert, width=2)
                    self.canvas.create_text(tx, hit_y - 24, text=f"{enemy['timer'] / 60:.1f}", fill=alert, font=("TkDefaultFont", 10, "bold"))
            elif enemy["action"] in ("scholar_crush", "scholar_swing", "mob_swing"):
                tx, ty = self.sx(enemy.get("target_x", 0)), self.sy(enemy.get("target_y", 0))
                if enemy["action"] == "scholar_crush":
                    c.create_oval(tx - 92, ty - 82, tx + 92, ty + 82,
                                  fill=danger, stipple="gray12", outline=alert, width=3)
                    c.create_line(tx, ty - 100, tx, ty - 63, fill=alert, width=4, arrow="last")
                else:
                    swing_face = enemy.get("attack_face", enemy["face"])
                    swing_reach = 130 if enemy["action"] == "mob_swing" else 165
                    center_world = enemy["x"] + w / 2
                    zone_world_x1 = center_world - (18 if swing_face > 0 else swing_reach)
                    zone_world_x2 = center_world + (swing_reach if swing_face > 0 else 18)
                    vertical_limit = enemy["h"] * .42 if enemy["action"] == "mob_swing" else 92
                    attack_low_y = enemy["y"] + h / 2 + vertical_limit
                    lane = self.draw_floor_warning_stripe(
                        zone_world_x1, zone_world_x2, attack_low_y,
                        alert, swing_face)
                timer_label = (f"공격까지 {enemy['timer'] / 60:.1f}"
                               if enemy["state"] == "notice"
                               else f"{enemy['timer'] / 60:.1f}")
                c.create_text(tx, ty - 90, text=timer_label,
                              fill=alert, font=("TkDefaultFont", 10, "bold"))
            elif enemy["action"] in ("column", "fall", "gravity"):
                tx, ty = self.sx(enemy.get("target_x", 0)), self.sy(enemy.get("target_y", 120))
                if enemy["action"] == "gravity":
                    c.create_oval(tx - 135, ty - 135, tx + 135, ty + 135,
                                  fill=danger, stipple="gray12", outline=alert, width=3)
                else:
                    lane_width = 24 if enemy["action"] == "column" else 34
                    c.create_rectangle(tx - lane_width, 0, tx + lane_width,
                                       self.sy(self.ground), fill=danger,
                                       stipple="gray12", outline=alert, width=2)
                c.create_text(tx, ty - 38, text=f"{enemy['timer'] / 60:.1f}", fill=alert, font=("TkDefaultFont", 12, "bold"))
            elif enemy["action"] == "catapult":
                tx = self.sx(enemy.get("target_x", 0))
                floor_y = self.sy(self.ground)
                c.create_rectangle(tx - 128, floor_y - 20, tx + 128, floor_y + 4,
                                   fill=danger, stipple="gray12", outline=alert, width=3)
                c.create_line(x + w / 2, y + h * .35, tx, floor_y - 22,
                              fill="#ef9299", width=3, dash=(10, 8), smooth=True)
                c.create_text(tx, floor_y - 40, text=f"착지 {enemy['timer'] / 60:.1f}",
                              fill=alert, font=("TkDefaultFont", 12, "bold"))
            elif enemy["action"] == "catapult_rock":
                tx, ty = self.sx(enemy.get("target_x", 0)), self.sy(enemy.get("target_y", 0))
                c.create_line(x + w / 2, y + h * .35, tx, ty,
                              fill="#ef9299", width=4, dash=(10, 8))
                c.create_oval(tx - 46, ty - 38, tx + 46, ty + 38,
                              fill=danger, stipple="gray12", outline=alert, width=2)
                c.create_text(tx, ty - 24, text=f"{enemy['timer'] / 60:.1f}", fill=alert, font=("TkDefaultFont", 10, "bold"))
            elif enemy["action"] in ("charge", "wheel_roll"):
                direction = enemy.get("face", 1)
                if enemy["action"] == "charge" and rank == "mob" and enemy["kind"] in MELEE_MOBS:
                    travel = 12 * 22
                    zone_world_x1 = (enemy["x"] - travel if direction < 0
                                     else enemy["x"])
                    zone_world_x2 = (enemy["x"] + w if direction < 0
                                     else enemy["x"] + w + travel)
                    attack_low_y = enemy["y"] + h / 2 + h * .42
                    lane = self.draw_floor_warning_stripe(
                        zone_world_x1, zone_world_x2, attack_low_y,
                        alert, direction)
                    if lane:
                        c.create_text((lane[0] + lane[1]) / 2, lane[2] - 20,
                                      text=f"{enemy['timer'] / 60:.1f}",
                                      fill=alert, font=("TkDefaultFont", 10, "bold"))
                else:
                    reach = (570 if enemy["action"] == "wheel_roll" else 264) + w / 2
                    start_x = x + w / 2
                    end_x = start_x + direction * reach
                    c.create_rectangle(min(start_x, end_x), y + h * .15,
                                       max(start_x, end_x), y + h * .85,
                                       fill=danger, stipple="gray12", outline=alert, width=2)
            elif enemy["action"] == "lever":
                cx, cy = x + w / 2, y + h / 2
                radius_x = w / 2 + 85
                c.create_oval(cx - radius_x, cy - 155,
                              cx + radius_x, cy + 235,
                              fill=danger, stipple="gray12", outline=alert, width=2)
            elif enemy["action"] == "parabola":
                tx, ty = self.sx(enemy.get("target_x", 0)), self.sy(enemy.get("target_y", 0))
                c.create_line(x + w / 2, y + h / 2, tx, ty,
                              fill="#ef9299", width=4, dash=(10, 8))
                c.create_oval(tx - 42, ty - 32, tx + 42, ty + 32,
                              fill=danger, stipple="gray12", outline=alert, width=2)
            elif enemy["action"] == "orbit":
                cx, cy = x + w / 2, y + h / 2
                for ray in range(8):
                    angle = math.tau * ray / 8
                    c.create_line(cx, cy, cx + math.cos(angle) * 260,
                                  cy + math.sin(angle) * 260,
                                  fill="#ef9299", width=4, dash=(10, 8))
            else:
                px = self.sx(self.player["x"] + PLAYER_W / 2)
                py = self.sy(self.player["y"] + PLAYER_H / 2)
                self.canvas.create_oval(px - 42, py - 42, px + 42, py + 42,
                                        fill=danger, stipple="gray12", outline=alert, width=2)
                self.pixel_line(x + w / 2, y + h / 2, px, py, danger)
                self.canvas.create_text(x + w / 2, y - 15, text=f"{enemy['timer'] / 60:.1f}", fill=alert, font=("TkDefaultFont", 9, "bold"))
        # Linen tunics, leather, mail and era-colored heraldry give every foe
        # a medieval silhouette instead of the old generic sci-fi look.
        mob_colors = {
            "지렛대 병사": "#bd7167", "부력 장치병": "#4c9aa4", "투석기 수호병": "#b79b69",
            "경사면 기사": "#d28b61", "낙하 장치병": "#729b83", "화승총 사수": "#a675a1",
            "중력 기사": "#657daf", "궤도 관측자": "#789bc1", "반작용 수호병": "#b86b79",
        }
        role_color = mob_colors.get(enemy["kind"],
                                    SUNSET_PALETTE["ranged"] if enemy["kind"] in RANGED_MOBS
                                    else SUNSET_PALETTE["melee"])
        base = role_color if rank == "mob" else SUNSET_PALETTE["scholar"] if rank == "scholar" else SUNSET_PALETTE["boss"]
        if enemy["hit"]:
            base = SUNSET_PALETTE["hit"]
        if rank == "dummy":
            wood = "#fff0d0" if enemy["hit"] else "#9a7046"
            self.rect(x + w * .42, y + 12, x + w * .58, y + h, "#69513a", "#3c332a")
            self.canvas.create_oval(x + w * .25, y, x + w * .75, y + 27, fill=wood, outline="#3c332a", width=3)
            self.rect(x + 2, y + 30, x + w - 2, y + 39, wood, "#3c332a")
            self.rect(x + w * .43, y + 19, x + w * .57, y + 22, "#4a3b2d")
            self.canvas.create_text(x + w / 2, y - 30, text="허수아비", fill="#f0d69e", font=("TkDefaultFont", 10, "bold"))
        elif enemy["kind"] == "부력 구체":
            self.rect(x + 4, y + 4, x + w - 4, y + h - 4, base, "#e6d18c")
            self.rect(x + 13, y + 12, x + 21, y + 20, "#f6e9bb")
        elif rank == "boss":
            # Large, portrait-like historical figure with a distinct face and regalia.
            face_fill = "#fff1d8" if enemy["hit"] else "#d8a27e"
            robes = (("#80414d", "#513344"), ("#71527d", "#403655"), ("#405b82", "#2d3b5d"))[self.chapter]
            hair = ("#ded0b6", "#c6c0b1", "#d4c5ae")[self.chapter]
            on_ship = enemy.get("boss_phase") in ("rising", "ship")
            if on_ship:
                # The hull wraps around his lower body and rises with him.
                hull_y = y + h - 98
                c.create_polygon(x - 126, hull_y + 10, x + w + 126, hull_y + 10,
                                 x + w + 88, hull_y + 106, x + w / 2, hull_y + 132,
                                 x - 88, hull_y + 106, fill="#714936", outline="#e6c57d", width=6)
                c.create_polygon(x - 59, hull_y + 17, x + w + 59, hull_y + 17,
                                 x + w + 42, hull_y + 34, x - 42, hull_y + 34,
                                 fill="#bb8b56", outline="#f1d69a", width=3)
                c.create_line(x + w / 2, y + h - 198, x + w / 2, hull_y + 26,
                              fill="#533c32", width=10)
                c.create_polygon(x + w / 2 + 9, y + h - 238, x + w / 2 + 117, y + h - 126,
                                 x + w / 2 + 9, y + h - 96,
                                 fill="#efe1bd", outline="#d7b971", width=4)
                c.create_line(x + w / 2 + 24, y + h - 178, x + w / 2 + 96, y + h - 111,
                              fill="#c49b68", width=3)
                c.create_line(x + w / 2 + 18, y + h - 208, x + 8, hull_y + 26,
                              fill="#9a7556", width=2)
                c.create_line(x + w / 2 + 18, y + h - 208, x + w + 104, hull_y + 26,
                              fill="#9a7556", width=2)
                c.create_line(x + w / 2 + 12, y + h - 205, x + w / 2 + 112, y + h - 115,
                              fill="#b68f65", width=2)
                c.create_polygon(x + w / 2 - 9, y + h - 218,
                                 x + w / 2 + 22, y + h - 208,
                                 x + w / 2 - 7, y + h - 195,
                                 fill="#e2c77f", outline="#755c47", width=2)
                for port_x in (x + 20, x + 70, x + w + 110, x + w + 60):
                    c.create_oval(port_x - 7, hull_y + 54, port_x + 7, hull_y + 68,
                                  fill="#392c35", outline="#d2a761", width=2)
                c.create_polygon(x - 108, hull_y + 24, x - 68, hull_y + 13,
                                 x - 78, hull_y + 61, fill="#e5c778", outline="#604b3e", width=2)
                c.create_text(x + w / 2, hull_y + 57, text="ἀρχιμήδης", fill="#ffe1ad", font=("TkDefaultFont", 10, "bold"))
            if enemy["state"] == "wheel_roll":
                c.create_oval(x - 38, y + 99, x + w + 38, y + h + 7, outline="#d3a953", width=8)
                for spoke in range(8):
                    angle = math.tau * spoke / 8 + self.frame * .12
                    c.create_line(x + w / 2, y + h * .55,
                                  x + w / 2 + math.cos(angle) * (w * .58),
                                  y + h * .55 + math.sin(angle) * (h * .38), fill="#f1cf7a", width=4)
            c.create_polygon(x + 24, y + 100, x + 52, y + 69, x + w - 52, y + 69,
                             x + w - 24, y + 100, x + w - 4, y + h, x + 4, y + h,
                             fill=robes[0], outline="#f4d18a", width=4)
            c.create_polygon(x + 20, y + 113, x + w / 2, y + h - 5, x + w - 20, y + 113,
                             x + w - 52, y + 91, x + w / 2, y + 109, x + 52, y + 91,
                             fill=robes[1], outline="#d6b979", width=3)
            # Linen layers, leather straps and folds add volume to the robe.
            c.create_polygon(x + 83, y + 112, x + 167, y + 112, x + 143, y + 211,
                             x + 125, y + 241, x + 107, y + 211,
                             fill="#d9c7a6", outline="#f2dfbc", width=2)
            c.create_line(x + 68, y + 128, x + 120, y + 180, x + 160, y + 211,
                          fill="#d2ad72", width=8, smooth=True)
            c.create_line(x + 74, y + 124, x + 124, y + 176, x + 164, y + 207,
                          fill="#f1d797", width=2, smooth=True)
            for fold in (94, 106, 145, 157):
                c.create_line(x + fold, y + 235, x + 125 + (fold - 125) * .48, y + h - 12,
                              fill="#9a6570" if fold < 125 else "#b88b7e", width=3, smooth=True)
            # Neck, ears and oversized head.
            c.create_rectangle(x + 99, y + 55, x + 151, y + 103, fill=face_fill, outline="#684851", width=3)
            c.create_oval(x + 63, y + 20, x + 187, y + 125, fill=face_fill, outline="#493849", width=4)
            c.create_oval(x + 76, y + 44, x + 111, y + 104, fill="#e9b995", outline="")
            c.create_polygon(x + 143, y + 32, x + 177, y + 48, x + 179, y + 91,
                             x + 155, y + 112, x + 142, y + 90,
                             fill="#bd806d", outline="")
            c.create_oval(x + 51, y + 38, x + 77, y + 78, fill=hair, outline="#6d5960", width=3)
            c.create_oval(x + 173, y + 38, x + 199, y + 78, fill=hair, outline="#6d5960", width=3)
            # Era-specific hair shapes: Archimedes' laurel, Galileo's curls, Newton's wig.
            if self.chapter == 0:
                c.create_oval(x + 67, y + 8, x + 183, y + 53, fill=hair, outline="#756457", width=3)
                for leaf in range(5):
                    lx = x + 78 + leaf * 19
                    c.create_oval(lx, y + 8 - (leaf % 2) * 5, lx + 21, y + 20,
                                  fill="#84a66d", outline="#d5c77f", width=2)
                c.create_line(x + 75, y + 26, x + 108, y + 8, x + 145, y + 8, x + 177, y + 25,
                              fill="#59794e", width=3, smooth=True)
            else:
                c.create_oval(x + 59, y + 5, x + 103, y + 55, fill=hair, outline="#756457", width=3)
                c.create_oval(x + 147, y + 5, x + 191, y + 55, fill=hair, outline="#756457", width=3)
                c.create_oval(x + 65, y + 78, x + 90, y + 105, fill=hair, outline="#756457", width=2)
                c.create_oval(x + 160, y + 78, x + 185, y + 105, fill=hair, outline="#756457", width=2)
            # Brow, eyes, nose and moustache make the face legible at gameplay scale.
            eye_y = y + 63
            for eye_x in (x + 91, x + 149):
                c.create_line(eye_x - 13, eye_y - 10, eye_x - 3, eye_y - 14,
                              eye_x + 10, eye_y - 11, fill="#594148", width=5, smooth=True)
                c.create_oval(eye_x - 8, eye_y - 4, eye_x + 8, eye_y + 7, fill="#f4dfc7", outline="#9b6b5e", width=1)
                c.create_oval(eye_x - 4, eye_y - 3, eye_x + 4, eye_y + 5, fill="#493b37", outline="")
                c.create_oval(eye_x - 2, eye_y - 2, eye_x, eye_y, fill="#fff8e8", outline="")
                c.create_line(eye_x - 7, eye_y + 10, eye_x + 7, eye_y + 11, fill="#bd806d", width=2, smooth=True)
            c.create_line(x + 122, y + 66, x + 115, y + 84, x + 119, y + 91,
                          x + 130, y + 91, fill="#ad705f", width=4, smooth=True)
            c.create_oval(x + 116, y + 87, x + 120, y + 91, fill="#805348", outline="")
            c.create_oval(x + 128, y + 87, x + 132, y + 91, fill="#805348", outline="")
            c.create_oval(x + 91, y + 93, x + 124, y + 108, fill=hair, outline="#79665b", width=2)
            c.create_oval(x + 124, y + 93, x + 157, y + 108, fill=hair, outline="#79665b", width=2)
            beard_end = y + (164 if self.chapter != 0 else 143)
            c.create_polygon(x + 91, y + 106, x + 154, y + 106, x + 145, beard_end,
                             x + 122, beard_end + 13, x + 100, beard_end,
                             fill=hair, outline="#756457", width=3)
            for strand in range(7):
                sx = x + 99 + strand * 7
                c.create_line(sx, y + 113, sx + (strand - 3) * 1.5, beard_end - 8,
                              sx + (strand - 3) * 2, beard_end + 5,
                              fill="#b7aa91" if strand % 2 else "#f5ead6", width=2, smooth=True)
            c.create_line(x + 108, y + 102, x + 121, y + 105, x + 137, y + 101,
                          fill="#877a6c", width=2, smooth=True)
            if self.chapter == 1:
                # Galileo's spectacles are a recognizable portrait cue.
                for gx in (x + 91, x + 139):
                    c.create_oval(gx - 15, y + 52, gx + 15, y + 78, outline="#e4c77c", width=3)
                c.create_line(x + 106, y + 65, x + 139, y + 65, fill="#e4c77c", width=3)
            # Broad cuffs and a large gold formula medallion.
            c.create_oval(x + 101, y + 181, x + 149, y + 229, fill="#d6ad61", outline="#fff0c9", width=3)
            c.create_text(x + 125, y + 205, text=("⚖", "↗", "g")[self.chapter], fill="#453851", font=("TkDefaultFont", 19, "bold"))
            # Warning pose lifts both arms so the windup reads at a glance.
            arm_raise = (enemy["state"] == "warning"
                         or enemy["state"] == "catapult_flight"
                         or self.frame < enemy.get("attack_pose_until", 0))
            action = enemy.get("action", "")
            shoulder_y = y + 111
            if arm_raise:
                if enemy["state"] == "catapult_flight":
                    flight_bob = math.sin(self.frame * .35) * 7
                    self.pixel_line(x + 56, shoulder_y, x + 16, y + 82 + flight_bob, face_fill)
                    self.pixel_line(x + w - 56, shoulder_y, x + w - 12, y + 105 - flight_bob, face_fill)
                    c.create_line(x + 24, y + 92 + flight_bob, x + w - 20, y + 114 - flight_bob,
                                  fill="#e7d2a8", width=5, dash=(8, 5))
                elif action == "lever":
                    self.pixel_line(x + 56, shoulder_y, x + 28, y + 145, face_fill)
                    self.pixel_line(x + w - 56, shoulder_y, x + w - 28, y + 145, face_fill)
                    c.create_line(x + 28, y + 145, x + w - 28, y + 145, fill="#e5c36d", width=9)
                    c.create_line(x + 28, y + 136, x + w - 28, y + 136, fill="#fff0c9", width=2)
                elif action == "wheel_roll":
                    self.pixel_line(x + 56, shoulder_y, x + 91, y + 145, face_fill)
                    self.pixel_line(x + w - 56, shoulder_y, x + w - 91, y + 145, face_fill)
                    c.create_oval(x + 31, y + 118, x + w - 31, y + h - 5, outline="#d3a953", width=6, dash=(10, 5))
                elif action == "catapult_rock":
                    self.pixel_line(x + 56, shoulder_y, x + 35, y + 75, face_fill)
                    self.pixel_line(x + 35, y + 75, x + 35, y + 22, face_fill)
                    c.create_oval(x + 17, y + 2, x + 53, y + 34, fill="#74634b", outline="#e1c184", width=3)
                    self.pixel_line(x + w - 56, shoulder_y, x + w - 28, y + 78, face_fill)
                elif action == "catapult":
                    self.pixel_line(x + 56, shoulder_y, x + 25, y + 34, face_fill)
                    self.pixel_line(x + w - 56, shoulder_y, x + w - 25, y + 34, face_fill)
                    self.pixel_line(x + 25, y + 34, x + w - 25, y + 34, "#e5c36d")
                elif action in ("gravity", "fall"):
                    self.pixel_line(x + 56, shoulder_y, x + 24, y + 160, face_fill)
                    self.pixel_line(x + w - 56, shoulder_y, x + w - 24, y + 160, face_fill)
                    c.create_line(x + 22, y + 174, x + w - 22, y + 174, fill="#b8c9ed", width=4, dash=(8, 4))
                elif action in ("parabola", "orbit"):
                    self.pixel_line(x + 56, shoulder_y, x + 28, y + 50, face_fill)
                    self.pixel_line(x + 28, y + 50, x + 15, y + 18, face_fill)
                    self.pixel_line(x + w - 56, shoulder_y, x + w - 18, y + 80, face_fill)
                    if action == "orbit":
                        c.create_oval(x + 4, y + 10, x + w - 4, y + 205, outline="#aebae2", width=3, dash=(7, 5))
                else:
                    self.pixel_line(x + 56, shoulder_y, x + 18, y + 48, face_fill)
                    self.pixel_line(x + w - 56, shoulder_y, x + w - 18, y + 48, face_fill)
            else:
                self.pixel_line(x + 58, shoulder_y, x + 24, y + 164, face_fill)
                self.pixel_line(x + w - 58, shoulder_y, x + w - 24, y + 164, face_fill)
            # Rounded, jointed arms replace the thin stick-like forearms. Hand
            # positions change with each warning so the action reads in silhouette.
            if enemy.get("boss_phase") == "ship":
                left_hand, right_hand = (x + 28, y + h - 129), (x + w - 28, y + h - 129)
            elif action == "lever":
                left_hand, right_hand = (x + 28, y + 145), (x + w - 28, y + 145)
            elif action == "wheel_roll":
                left_hand, right_hand = (x + 88, y + 152), (x + w - 88, y + 152)
            elif action == "catapult_rock":
                left_hand, right_hand = (x + 35, y + 20), (x + w - 28, y + 78)
            elif action == "catapult":
                left_hand, right_hand = (x + 25, y + 34), (x + w - 25, y + 34)
            elif action in ("gravity", "fall"):
                left_hand, right_hand = (x + 24, y + 160), (x + w - 24, y + 160)
            elif action in ("parabola", "orbit"):
                left_hand, right_hand = (x + 15, y + 18), (x + w - 18, y + 80)
            else:
                left_hand, right_hand = (x + 24, y + 164), (x + w - 24, y + 164)
            for shoulder_x, hand in ((x + 57, left_hand), (x + w - 57, right_hand)):
                elbow = ((shoulder_x + hand[0]) / 2, max(y + 50, min(shoulder_y + 34, hand[1] - 8)))
                c.create_line(shoulder_x, shoulder_y, elbow[0], elbow[1],
                              fill=robes[0], width=27, smooth=True, capstyle="round")
                c.create_oval(elbow[0] - 13, elbow[1] - 13, elbow[0] + 13, elbow[1] + 13,
                              fill=robes[1], outline="#d7b979", width=2)
                c.create_line(elbow[0], elbow[1], hand[0], hand[1],
                              fill=face_fill, width=15, smooth=True, capstyle="round")
                c.create_line(elbow[0] + 1, elbow[1] - 3, hand[0], hand[1] - 3,
                              fill="#efc3a1", width=3, smooth=True, capstyle="round")
                c.create_oval(hand[0] - 8, hand[1] - 8, hand[0] + 8, hand[1] + 8,
                              fill=face_fill, outline="#9a6157", width=2)
            if enemy.get("boss_phase") == "ship":
                # Bow, deck and rail overlap his legs so his stance reads aboard.
                rail_y = y + h - 112
                c.create_polygon(x - 112, rail_y, x + w + 112, rail_y,
                                 x + w + 76, rail_y + 72, x + w / 2, rail_y + 96,
                                 x - 76, rail_y + 72, fill="#80533a", outline="#f0cf81", width=6)
                for plank in range(5):
                    py = rail_y + 18 + plank * 11
                    c.create_line(x - 68, py, x + w + 68, py - 2,
                                  fill="#b47c4d" if plank % 2 else "#d09a5d", width=3)
                for rivet_x in range(int(x - 62), int(x + w + 64), 32):
                    c.create_oval(rivet_x - 2, rail_y + 28, rivet_x + 2, rail_y + 32,
                                  fill="#f4d797", outline="#5e4034")
                c.create_line(x - 91, rail_y + 8, x + w + 91, rail_y + 8,
                              fill="#ffe1a0", width=6)
                c.create_line(x - 91, rail_y + 8, x - 76, rail_y + 40,
                              fill="#f1cf81", width=5)
                c.create_line(x + w + 91, rail_y + 8, x + w + 76, rail_y + 40,
                              fill="#f1cf81", width=5)
            self.rect(x + 5, y + 132, x + 22, y + 153, "#caa35f", "#fff0c9")
            self.rect(x + w - 22, y + 132, x + w - 5, y + 153, "#caa35f", "#fff0c9")
        elif rank == "mob":
            # Small grunts appear in groups, so use a compact silhouette with
            # only the role cues needed to read them during combat.
            armor_shadow = self.color_mix(base, "#171b2a", .36)
            armor_light = self.color_mix(base, "#fff0cf", .26)
            head_w = 17
            hx = x + (w - head_w) / 2
            head_y = y + 3
            torso_y = y + h * .22
            c.create_polygon(x + w * .23, torso_y, x + w * .77, torso_y,
                             x + w * .86, y + h * .68, x + w * .68, y + h * .75,
                             x + w * .32, y + h * .75, x + w * .14, y + h * .68,
                             fill=base, outline=armor_shadow, width=1)
            c.create_line(x + w * .3, torso_y + 4, x + w * .7, torso_y + 4,
                          fill=armor_light, width=2)
            self.rect(x + w * .34, y + h * .62, x + w * .66, y + h * .68,
                      "#d1bd8b")
            # Simple separated legs preserve the running silhouette.
            for leg_x in (x + w * .27, x + w * .56):
                self.rect(leg_x, y + h * .72, leg_x + w * .17, y + h * .94,
                          armor_shadow)
                self.rect(leg_x - 2, y + h * .92, leg_x + w * .2, y + h,
                          "#413943", armor_light)
            # One clean helmet/hood shape and a directional eye retain facing.
            c.create_oval(hx, head_y, hx + head_w, head_y + 20,
                          fill="#d8a27e" if not enemy["hit"] else "#fff1d8",
                          outline=armor_shadow, width=1)
            if enemy["kind"] in MELEE_MOBS:
                c.create_polygon(hx - 1, head_y + 9, hx + 2, head_y + 1,
                                 hx + head_w - 2, head_y + 1, hx + head_w + 1, head_y + 9,
                                 fill="#a88a5f", outline=armor_light, width=1)
            else:
                c.create_arc(hx - 1, head_y - 2, hx + head_w + 1, head_y + 18,
                             start=0, extent=180, style="pieslice",
                             fill="#554c5c", outline=armor_light, width=1)
            eye_x = hx + (head_w - 5 if enemy["face"] > 0 else 2)
            self.rect(eye_x, head_y + 11, eye_x + 3, head_y + 13, "#382c35")

            shoulder_x = x + w / 2
            shoulder_y = torso_y + 10
            hand_x = shoulder_x + enemy["face"] * w * .43
            hand_y = y + h * .52
            c.create_line(shoulder_x, shoulder_y, hand_x, hand_y,
                          fill=armor_shadow, width=5, capstyle="round")
            if enemy["kind"] in RANGED_MOBS:
                gun_end_x = hand_x + enemy["face"] * 25
                gun_end_y = hand_y - 2
                c.create_line(hand_x - enemy["face"] * 5, hand_y + 2,
                              gun_end_x, gun_end_y,
                              fill="#42383c", width=7, capstyle="round")
                c.create_line(hand_x, hand_y, gun_end_x - enemy["face"] * 2,
                              gun_end_y, fill="#b17b4e", width=3, capstyle="round")
                c.create_oval(gun_end_x - 2, gun_end_y - 2,
                              gun_end_x + 2, gun_end_y + 2,
                              fill="#ffe0a3", outline="#fff0cf")
                pack_x = x + (w * .08 if enemy["face"] > 0 else w * .72)
                self.rect(pack_x, torso_y + 7, pack_x + w * .2, torso_y + 22,
                          "#765448", "#d5b579")
                if enemy["kind"] == "부력 장치병":
                    c.create_oval(x + w * .72, y + 8, x + w * .94, y + 23,
                                  fill="#4f9aa1", outline="#bde8d7", width=1)
            else:
                swinging = (enemy["action"] == "mob_swing"
                            and (enemy["state"] == "warning"
                                 or self.frame < enemy.get("attack_pose_until", 0)))
                if swinging:
                    swing_face = enemy.get("attack_face", enemy["face"])
                    hand_x = shoulder_x + swing_face * 9
                    hand_y = shoulder_y - 5
                    c.create_line(shoulder_x, shoulder_y, hand_x, hand_y,
                                  fill="#d9aa8b", width=4, capstyle="round")
                    c.create_line(hand_x, hand_y, hand_x + swing_face * 35, hand_y - 10,
                                  fill="#4a3d47", width=5, capstyle="round")
                    c.create_line(hand_x, hand_y, hand_x + swing_face * 35, hand_y - 10,
                                  fill="#e0d3bd", width=2, capstyle="round")
                else:
                    c.create_line(hand_x, hand_y, hand_x + enemy["face"] * 17,
                                  hand_y - 12, fill="#e0d3bd", width=3,
                                  capstyle="round")
                shield_x = x + (w * .16 if enemy["face"] > 0 else w * .62)
                shield_y = torso_y + 11
                c.create_polygon(shield_x, shield_y, shield_x + w * .21, shield_y + 2,
                                 shield_x + w * .17, shield_y + 22,
                                 shield_x + w * .08, shield_y + 27,
                                 fill=armor_shadow, outline=armor_light, width=1)
                c.create_line(shield_x + w * .1, shield_y + 5,
                              shield_x + w * .1, shield_y + 21,
                              fill=accent, width=1)
        else:
            scale = 6 if rank == "boss" else 4
            head_w = scale * 5
            hx = x + w / 2 - head_w / 2
            skin = "#fff1d8" if enemy["hit"] else "#d8a27e"
            c.create_oval(hx, y, hx + head_w, y + scale * 5, fill=skin, outline="#493849", width=2)
            # Hood/cap, brows, eyes, nose and beard distinguish the human faces.
            c.create_arc(hx - 2, y - 3, hx + head_w + 2, y + scale * 4,
                         start=0, extent=180, style="pieslice", fill="#75634f" if enemy["kind"] in RANGED_MOBS else "#594a58", outline=accent, width=2)
            eye = hx + (head_w - 8 if enemy["face"] > 0 else 3)
            self.rect(eye, y + 8, eye + 3, y + 10, "#382c35")
            self.pixel_line(hx + head_w / 2, y + 10, hx + head_w / 2 - enemy["face"] * 2, y + 15, "#a86860")
            if rank == "scholar" or enemy["kind"] in MELEE_MOBS:
                c.create_polygon(hx + 4, y + 16, hx + head_w - 4, y + 16,
                                 hx + head_w / 2, y + scale * 8,
                                 fill="#c9c0ae", outline="#76685d", width=1)
            torso_y = y + scale * 5
            armor_shadow = self.color_mix(base, "#171b2a", .36)
            armor_light = self.color_mix(base, "#fff0cf", .26)
            c.create_polygon(x + w * .2, torso_y, x + w * .8, torso_y,
                             x + w * .88, y + h * .68, x + w * .68, y + h * .77,
                             x + w * .32, y + h * .77, x + w * .12, y + h * .68,
                             fill=base, outline=armor_shadow, width=2)
            c.create_line(x + w * .24, torso_y + 4, x + w * .76, torso_y + 4,
                          fill=armor_light, width=2)
            self.rect(x + w * .27, torso_y + 6, x + w * .73, torso_y + 10, "#d1bd8b")
            c.create_line(x + w * .34, torso_y + 16, x + w * .42, y + h * .68,
                          fill=armor_light, width=1)
            c.create_line(x + w * .66, torso_y + 16, x + w * .58, y + h * .68,
                          fill=armor_shadow, width=2)
            # Tiny stitched seams and engraved plate marks add readable pixels
            # without changing the body's combat silhouette.
            for seam in range(3):
                sx = x + w * (.39 + seam * .08)
                sy = torso_y + 20 + (seam % 2) * 5
                c.create_rectangle(sx, sy, sx + 2, sy + 2,
                                   fill=armor_light if seam % 2 else accent, outline="")
            c.create_line(x + w * .42, y + h * .64, x + w * .58, y + h * .64,
                          fill=armor_light, width=2)
            # Layered shoulder guards, cross-straps and a small heraldic clasp.
            self.rect(x + w * .12, torso_y + 3, x + w * .34, torso_y + 13, "#80776c", "#d2bd89")
            self.rect(x + w * .66, torso_y + 3, x + w * .88, torso_y + 13, "#80776c", "#d2bd89")
            self.pixel_line(x + w * .3, torso_y + 14, x + w * .7, torso_y + h * .25, "#d9c18b")
            c.create_oval(x + w * .45, torso_y + 12, x + w * .55, torso_y + 21, fill=accent, outline="#fff0c9")
            # Layered cuirass, riveted collar and era-colored heraldry give
            # the small bodies more depth without increasing their footprint.
            plate_top = torso_y + 12
            plate_bottom = min(y + h * .61, torso_y + 37)
            c.create_polygon(x + w * .37, plate_top, x + w * .63, plate_top,
                             x + w * .68, plate_bottom - 5, x + w * .5, plate_bottom,
                             x + w * .32, plate_bottom - 5,
                             fill=self.color_mix(base, "#202331", .16),
                             outline=armor_light, width=1)
            c.create_line(x + w * .4, plate_top + 5, x + w * .5, plate_bottom - 5,
                          fill=self.color_mix(base, "#fff1cf", .42), width=1)
            c.create_line(x + w * .6, plate_top + 5, x + w * .5, plate_bottom - 5,
                          fill=armor_shadow, width=1)
            for rivet_y in (plate_top + 5, plate_bottom - 7):
                for rivet_x in (x + w * .39, x + w * .61):
                    c.create_oval(rivet_x - 1.5, rivet_y - 1.5, rivet_x + 1.5, rivet_y + 1.5,
                                  fill="#fff0c9", outline="#78634e")
            crest_color = "#73d1c6" if enemy["kind"] in RANGED_MOBS else accent
            c.create_polygon(x + w * .47, plate_top + 7, x + w * .53, plate_top + 7,
                             x + w * .5, plate_top + 15,
                             fill=crest_color, outline="#fff0c9", width=1)
            # A distinct helmet silhouette and cheek guards separate armored
            # melee foes from the hooded or padded ranged silhouettes.
            if enemy["kind"] in MELEE_MOBS:
                c.create_rectangle(hx + 2, y + 1, hx + head_w - 2, y + 5,
                                   fill="#b99962", outline="#f2d79c", width=1)
                c.create_polygon(hx + 2, y + 6, hx + 7, y + 13,
                                 hx + 5, y + 20, hx, y + 16,
                                 fill="#82756a", outline="#ded0ae", width=1)
                c.create_polygon(hx + head_w - 2, y + 6, hx + head_w - 7, y + 13,
                                 hx + head_w - 5, y + 20, hx + head_w, y + 16,
                                 fill="#82756a", outline="#ded0ae", width=1)
            else:
                # Quilted hood seams and a small side satchel are visible on
                # ranged units, including their elevated-platform silhouettes.
                for seam_y in (y + 5, y + 9, y + 13):
                    c.create_line(hx + 2, seam_y, hx + head_w - 2, seam_y + 1,
                                  fill="#bfa477", width=1)
            if enemy["kind"] in RANGED_MOBS:
                self.rect(x + w * .38, y + h * .74, x + w * .62, y + h * .79, "#8a5a45", "#dec591")
                pack_x = x + (w * .07 if enemy["face"] > 0 else w * .72)
                self.rect(pack_x, torso_y + 7, pack_x + w * .2, torso_y + 25,
                          "#765448", "#d5b579")
                c.create_line(pack_x + w * .05, torso_y + 11,
                              pack_x + w * .16, torso_y + 11, fill="#e3c78f", width=1)
                if enemy["kind"] == "부력 장치병":
                    c.create_oval(x + w * .7, y + 7, x + w * .98, y + 24,
                                  fill="#4f9aa1", outline="#bde8d7", width=2)
                    c.create_oval(x + w * .78, y + 10, x + w * .9, y + 20,
                                  fill="#b9eee0", outline="#6fc1bc", width=1)
                elif enemy["kind"] == "투석기 수호병":
                    c.create_oval(pack_x + w * .02, y + h * .78,
                                  pack_x + w * .2, y + h * .93,
                                  fill="#74634b", outline="#e0c58a", width=2)
            self.rect(x + w * .25, y + h * .72, x + w * .43, y + h, "#504a45")
            self.rect(x + w * .57, y + h * .72, x + w * .75, y + h, "#504a45")
            for leg_index, leg_x in enumerate((x + w * .25, x + w * .57)):
                knee_y = y + h * .82
                c.create_oval(leg_x - 1, knee_y - 4, leg_x + w * .18 + 1, knee_y + 4,
                              fill=armor_shadow, outline=armor_light, width=1)
                c.create_line(leg_x + 3, y + h * .76, leg_x + 4, knee_y - 1,
                              fill=armor_light, width=1)
                c.create_line(leg_x + 2, y + h * .78, leg_x + 2, y + h - 4,
                              fill="#b6a888", width=1)
                boot_y = y + h - 9
                c.create_polygon(leg_x - 2, boot_y - 3, leg_x + w * .18 + 4, boot_y - 3,
                                 leg_x + w * .2 + 7, y + h - 2,
                                 leg_x - 3, y + h - 2,
                                 fill="#413943", outline="#cfb47e", width=1)
                c.create_line(leg_x + 2, boot_y, leg_x + w * .16,
                              boot_y + (1 if leg_index else 0), fill="#ead4a2", width=1)
                c.create_line(leg_x, y + h - 3, leg_x + w * .18, y + h - 3,
                              fill="#d9c18b", width=2)
            for rivet_x in (x + w * .2, x + w * .8):
                c.create_oval(rivet_x - 2, torso_y + 4, rivet_x + 2, torso_y + 8,
                              fill="#fff0c9", outline="#927c57")
            self.pixel_line(x + w / 2, torso_y + 7, x + w / 2 + enemy["face"] * w * .45, torso_y + 13, "#d2c6a6")
            # Weapon silhouettes communicate role before the telegraphed attack.
            weapon = "#ffe0a3" if enemy["kind"] in RANGED_MOBS else "#f8d7ae"
            shoulder_x = x + w / 2
            shoulder_y = torso_y + 12
            if enemy["kind"] in RANGED_MOBS:
                target_x = (enemy.get("locked_target_x", enemy.get("target_x", 0))
                            if enemy["state"] in ("warning", "locked") else None)
                target_y = (enemy.get("locked_target_y", enemy.get("target_y", 0))
                            if enemy["state"] in ("warning", "locked") else None)
                if target_x is not None:
                    aim_angle = math.atan2(self.sy(target_y) - shoulder_y,
                                           self.sx(target_x) - shoulder_x)
                else:
                    aim_angle = 0 if enemy["face"] > 0 else math.pi
                ux, uy = math.cos(aim_angle), math.sin(aim_angle)
                muzzle_x, muzzle_y = shoulder_x + ux * 31, shoulder_y + uy * 31
                stock_x, stock_y = shoulder_x - ux * 10, shoulder_y - uy * 10
                c.create_line(stock_x, stock_y, muzzle_x, muzzle_y,
                              fill="#42383c", width=8, capstyle="round")
                c.create_line(stock_x + 1, stock_y - 1, muzzle_x - ux * 2, muzzle_y - uy * 2,
                              fill="#b17b4e", width=4, capstyle="round")
                c.create_line(shoulder_x + ux * 5, shoulder_y + uy * 5,
                              muzzle_x, muzzle_y, fill="#51535d", width=4)
                c.create_line(shoulder_x + ux * 8, shoulder_y + uy * 8,
                              muzzle_x - ux * 2, muzzle_y - uy * 2,
                              fill="#d9c18b", width=1)
                grip_x, grip_y = shoulder_x + ux * 3 - uy * 7, shoulder_y + uy * 3 + ux * 7
                c.create_line(grip_x, grip_y, grip_x + uy * 10, grip_y - ux * 10,
                              fill="#684a43", width=5, capstyle="round")
                c.create_oval(muzzle_x - 3, muzzle_y - 3, muzzle_x + 3, muzzle_y + 3,
                              fill="#e7c77e", outline="#fff0cf", width=1)
            elif enemy["action"] in ("mob_swing", "scholar_swing") and (enemy["state"] in ("notice", "warning") or self.frame < enemy.get("attack_pose_until", 0)):
                shoulder_x, shoulder_y = x + w / 2, torso_y + 12
                swing_face = enemy.get("attack_face", enemy["face"])
                if enemy["state"] in ("notice", "warning"):
                    hand_x, hand_y = shoulder_x - swing_face * 14, shoulder_y - 12
                    blade_angle = -2.05
                else:
                    swing = min(1, max(0, (14 - (enemy.get("attack_pose_until", 0) - self.frame)) / 14))
                    hand_x = shoulder_x + swing_face * (6 + swing * 17)
                    hand_y = shoulder_y - 8 + swing * 10
                    blade_angle = -2.05 + swing * 2.35
                c.create_line(shoulder_x, shoulder_y, hand_x, hand_y,
                              fill="#d9aa8b", width=5, capstyle="round")
                tip_x = hand_x + swing_face * math.cos(blade_angle) * 43
                tip_y = hand_y + math.sin(blade_angle) * 43
                c.create_line(hand_x, hand_y, tip_x, tip_y,
                              fill="#4a3d47", width=7, capstyle="round")
                c.create_line(hand_x, hand_y, tip_x, tip_y,
                              fill="#e0d3bd", width=3, capstyle="round")
            elif enemy["action"] == "slam" and (enemy["state"] in ("notice", "warning") or self.frame < enemy.get("attack_pose_until", 0)):
                self.pixel_line(shoulder_x, shoulder_y, shoulder_x + enemy["face"] * 4, y - 21, weapon)
                self.pixel_line(shoulder_x + enemy["face"] * 4, y - 21, shoulder_x + enemy["face"] * 14, y - 14, weapon)
            elif enemy["state"] in ("notice", "warning") or self.frame < enemy.get("attack_pose_until", 0):
                windup = math.sin(self.frame * .55) * 4
                self.pixel_line(shoulder_x, shoulder_y, shoulder_x - enemy["face"] * (5 + windup), y - 15, weapon)
                self.pixel_line(shoulder_x - enemy["face"] * (5 + windup), y - 15,
                                shoulder_x + enemy["face"] * 13, y - 22 + windup, weapon)
            elif self.frame < enemy.get("attack_pose_until", 0):
                self.pixel_line(shoulder_x, shoulder_y, shoulder_x + enemy["face"] * 12, y + h - 3, weapon)
            else:
                self.pixel_line(shoulder_x, shoulder_y, shoulder_x + enemy["face"] * (w * .65), torso_y + h * .38, weapon)
            if enemy["kind"] in MELEE_MOBS:
                shield_x = x + (w * .18 if enemy["face"] > 0 else w * .58)
                shield_y = torso_y + 12
                c.create_polygon(shield_x, shield_y, shield_x + w * .24, shield_y + 2,
                                 shield_x + w * .2, shield_y + 24, shield_x + w * .12, shield_y + 31,
                                 shield_x + w * .04, shield_y + 24,
                                 fill=armor_shadow, outline=armor_light, width=2)
                c.create_line(shield_x + w * .12, shield_y + 5,
                              shield_x + w * .12, shield_y + 25, fill=accent, width=2)
                c.create_line(shield_x + 3, shield_y + 15,
                              shield_x + w * .21, shield_y + 15,
                              fill="#d9c38b", width=2)
                c.create_polygon(shield_x + w * .12, shield_y + 9,
                                 shield_x + w * .17, shield_y + 15,
                                 shield_x + w * .12, shield_y + 22,
                                 shield_x + w * .07, shield_y + 15,
                                 fill=accent, outline="#fff0c9", width=1)
                c.create_oval(shield_x + w * .09, shield_y + 13,
                              shield_x + w * .15, shield_y + 19,
                              fill="#fff0c9", outline="#927c57")
            self.rect(hx - 2, y - 2, hx + head_w + 2, y + 3, "#71664e", accent)
            if rank == "boss":
                self.rect(x, y + h * .4, x + w, y + h * .47, accent)
        if rank != "boss":
            bar_y = y - 12
            self.rect(x + w / 2 - max(w, 44) / 2, bar_y, x + w / 2 + max(w, 44) / 2, bar_y + 5, "#34272a")
            self.rect(x + w / 2 - max(w, 44) / 2, bar_y, x + w / 2 - max(w, 44) / 2 + max(w, 44) * max(0, enemy["hp"] / enemy["maxhp"]), bar_y + 5, "#ca554e")
        if rank not in ("mob", "dummy", "boss"):
            c.create_text(x + w / 2, y - 25, text=enemy["kind"], fill=accent, font=("TkDefaultFont", 9, "bold"))

    def draw_effect(self, effect):
        kind, wx, wy, life = effect[:4]
        x = self.sx(wx)
        y = self.sy(wy)
        color = {"slash": "#fff0c8", "double_jump": "#e5cf8e", "dash": "#e7c171", "after": "#728e96", "hit": "#f47969", "lever": "#f0cf7d", "burst": "#e5cf8e", "gravity": "#9fadd9", "gravity_slam": "#b9a9ed", "meteor_blast": "#ffad55", "warning": "#e95e61", "parry": "#b7f2ce", "muzzle": "#ffd37e", "slam": "#ff9b8f", "spawn": "#8ce0d1", "impact": "#fff0c9", "heal": "#9cf2a1", "landing": "#d8c19a", "footstep": "#d1c3a4", "water_splash": "#8fe5e4", "tnt_blast": "#ffad55"}.get(kind, "#eee")
        if kind in ("water_splash", "whale_breach"):
            age = effect[3] - life
            spread = 22 + age * 3.2
            water_y = self.sy(self.ground)
            if kind == "whale_breach":
                scale = effect[4] if len(effect) > 4 else 1.0
                progress = min(1.0, age / 34)
                fade = min(1.0, life / 24)
                width = (150 + progress * 300) * scale
                height = (24 + math.sin(progress * math.pi * .72) * 230) * scale
                self.canvas.create_arc(x - width, water_y - height * .75,
                                       x + width, water_y + height * .28,
                                       start=8, extent=164, style="arc",
                                       outline="#a9f5ed", width=max(3, int(12 * scale * fade)))
                self.canvas.create_arc(x - width * .72, water_y - height * .52,
                                       x + width * .72, water_y + height * .2,
                                       start=10, extent=160, style="arc",
                                       outline="#e0fff4", width=max(2, int(5 * scale * fade)))
                for side in (-1, 1):
                    jet_x = x + side * width * .76
                    jet_h = height * (.78 + .12 * math.sin(age * .18))
                    self.canvas.create_line(jet_x, water_y + 8, jet_x + side * 24 * scale,
                                            water_y - jet_h, jet_x + side * 48 * scale,
                                            water_y - jet_h * .76, fill="#baf9ef",
                                            width=max(3, int(10 * scale * fade)), smooth=True)
                for drop in range(18):
                    phase = age * .17 + drop * math.tau / 18
                    dx = math.cos(phase) * (width * .62 + (drop % 4) * 12)
                    dy = abs(math.sin(phase)) * (height * .68 + (drop % 5) * 9)
                    radius = (3 + drop % 5) * scale
                    self.canvas.create_oval(x + dx - radius, water_y - dy - radius,
                                            x + dx + radius, water_y - dy + radius,
                                            fill="#e0fff4" if drop % 2 else "#62d5d6", outline="")
                return
            self.canvas.create_line(x - spread, water_y + 4, x - spread * .5, water_y - 5,
                                    x, water_y + 1, x + spread * .5, water_y - 6,
                                    x + spread, water_y + 4, fill="#59b9c8", width=5, smooth=True)
            self.canvas.create_arc(x - spread * .72, water_y - age * 1.1 - 18,
                                   x + spread * .72, water_y + 22, start=5, extent=170,
                                   style="arc", outline="#b7f3e8", width=3)
            for drop in range(8):
                phase = age * .22 + drop * math.tau / 8
                dx = math.cos(phase) * (16 + age * 1.45)
                dy = abs(math.sin(phase)) * (20 + age * .75)
                radius = 2 + (drop % 3)
                self.canvas.create_oval(x + dx - radius, water_y - dy - radius,
                                        x + dx + radius, water_y - dy + radius,
                                        fill="#d4fff3" if drop % 2 else "#66cbd0", outline="")
        elif kind == "heal":
            rise = (42 - life) * .65
            self.canvas.create_oval(x - 14, y - rise - 14, x + 14, y - rise + 14, fill="#244d3a", outline="#9cf2a1", width=2)
            self.canvas.create_line(x, y - rise - 8, x, y - rise + 8, fill="#e3ffe4", width=4)
            self.canvas.create_line(x - 8, y - rise, x + 8, y - rise, fill="#e3ffe4", width=4)
            self.canvas.create_text(x, y - rise - 25, text=f"+{effect[4]} HP", fill="#b9ffbd", font=("TkDefaultFont", 11, "bold"))
        elif kind == "damage_text":
            rise = (48 - life) * .72
            color = "#fff2b0" if life > 12 else "#ffd6a2"
            self.canvas.create_text(x + 1, y - rise + 1, text=f"-{effect[4]}", fill="#392836",
                                    font=("TkDefaultFont", 16, "bold"))
            self.canvas.create_text(x, y - rise, text=f"-{effect[4]}", fill=color,
                                    font=("TkDefaultFont", 16, "bold"))
        elif kind == "coin":
            rise = (28 - life) * .8
            self.canvas.create_text(x + 1, y - rise + 1, text=f"+{effect[4]} 동전",
                                    fill="#493322", font=("TkDefaultFont", 12, "bold"))
            self.canvas.create_text(x, y - rise, text=f"+{effect[4]} 동전",
                                    fill="#ffe17c", font=("TkDefaultFont", 12, "bold"))
        elif kind == "landing":
            age = effect[3] - life
            r = 12 + age * 4
            floor_y = self.sy(wy)
            self.canvas.create_arc(x - r, floor_y - r * .35, x + r, floor_y + r * .45,
                                   start=0, extent=180, style="arc", outline="#f4e0b7", width=2)
            for side in (-1, 1):
                self.canvas.create_line(x, floor_y - 2, x + side * (r + 12), floor_y - 8 - (age % 4),
                                        fill="#d7bd8e", width=2)
                for mote in range(3):
                    mx = x + side * (r * .35 + mote * 7)
                    my = floor_y - 4 - ((age + mote * 3) % 10)
                    self.canvas.create_rectangle(mx, my, mx + 3, my + 3,
                                                 fill="#e9d8b1", outline="")
        elif kind == "footstep":
            age = effect[3] - life
            direction = effect[4] if len(effect) > 4 else 1
            floor_y = self.sy(wy)
            width = 5 + age * 2
            self.canvas.create_arc(x - width, floor_y - 6 - age * .4,
                                   x + width, floor_y + 3, start=0 if direction > 0 else 180,
                                   extent=145, style="arc", outline=color, width=2)
            for mote in range(3):
                mx = x - direction * (age * 1.6 + mote * 5)
                my = floor_y - 3 - (age + mote * 3) % 7
                self.canvas.create_rectangle(mx, my, mx + 2, my + 2, fill="#f0dfbb", outline="")
        elif kind == "double_jump":
            age = effect[3] - life
            radius = 8 + age * 1.5
            self.canvas.create_oval(x - radius, y - radius * .48, x + radius, y + radius * .48,
                                    outline="#f2dfae", width=2)
            for shard in range(5):
                angle = math.tau * shard / 5 + age * .12
                inner, outer = radius * .55, radius * .95
                self.canvas.create_line(x + math.cos(angle) * inner, y + math.sin(angle) * inner,
                                        x + math.cos(angle) * outer, y + math.sin(angle) * outer,
                                        fill="#fff2cd", width=2)
        elif kind == "slash":
            direction = effect[4] if len(effect) > 4 else 1
            age = effect[3] - life
            progress = min(1, max(0, age / 8))
            # A broad crescent of compressed air, revealed as the blade cuts
            # through the space. The warm glint and cyan edge make it readable
            # over both dark rooms and bright outdoor windows.
            keys = ((0.0, -28), (.18, -48), (.42, -52), (.65, -42), (.84, -18), (1.0, 12))
            samples = []
            for index in range(25):
                t = index / 24
                if t > progress:
                    break
                for pair in range(len(keys) - 1):
                    if keys[pair][0] <= t <= keys[pair + 1][0]:
                        ratio = (t - keys[pair][0]) / (keys[pair + 1][0] - keys[pair][0])
                        curve_y = keys[pair][1] + (keys[pair + 1][1] - keys[pair][1]) * ratio
                        samples.append((x + direction * (12 + 138 * t), y + curve_y))
                        break
            if len(samples) >= 2:
                coords = [value for point in samples for value in point]
                fade = max(.35, min(1, life / 6))
                # Layered tapered streaks read as wind splitting around the sword.
                self.canvas.create_line(*coords, fill="#36546b", width=15 * fade,
                                        smooth=True, splinesteps=18, capstyle="round")
                self.canvas.create_line(*coords, fill="#70d8df", width=9 * fade,
                                        smooth=True, splinesteps=18, capstyle="round")
                self.canvas.create_line(*coords, fill="#e5fbef", width=3 * fade,
                                        smooth=True, splinesteps=18, capstyle="round")
                if len(samples) > 5:
                    upper = [value for index, point in enumerate(samples) for value in
                             (point[0] - direction * 7, point[1] - 8 - math.sin(index * .35) * 3)]
                    lower = [value for index, point in enumerate(samples) for value in
                             (point[0] + direction * 3, point[1] + 9 + math.sin(index * .4) * 3)]
                    self.canvas.create_line(*upper, fill="#c3f6ed", width=2,
                                            smooth=True, splinesteps=14, capstyle="round")
                    self.canvas.create_line(*lower, fill="#91c7d5", width=2,
                                            smooth=True, splinesteps=14, capstyle="round")
                # Air flecks peel off the wind's leading edge.
                tip_x, tip_y = samples[-1]
                for mote in range(4):
                    mx = tip_x - direction * (mote * 13 + age * .8)
                    my = tip_y + (mote - 1.5) * 8 + math.sin(age * .5 + mote) * 3
                    self.canvas.create_line(mx, my, mx + direction * 7, my - 4,
                                            fill="#f5fff0", width=2, capstyle="round")
        elif kind == "gravity":
            age = effect[3] - life
            r = (24 - life) * 6
            pulse = 8 * math.sin(age * .42)
            for ring, width in ((1.0, 3), (.68, 2), (.34, 1)):
                radius = max(5, r * ring + pulse)
                self.canvas.create_oval(x - radius, y - radius * .72,
                                        x + radius, y + radius * .72,
                                        outline=color if width > 1 else "#f4e4bd", width=width)
            for shard in range(8):
                angle = math.tau * shard / 8 - age * .18
                inner, outer = r * .76, r * .98
                self.canvas.create_line(x + math.cos(angle) * inner, y + math.sin(angle) * inner,
                                        x + math.cos(angle) * outer, y + math.sin(angle) * outer,
                                        fill="#e8e4ff", width=2)
        elif kind == "gravity_slam":
            age = effect[3] - life
            radius = effect[4] * min(1, age / 7)
            self.canvas.create_oval(x - radius, y - radius * .68,
                                    x + radius, y + radius * .68,
                                    outline="#c7b5ff", width=4)
            for offset in (-.55, 0, .55):
                ax = x + radius * offset
                self.canvas.create_line(ax, y - 42, ax, y - 8,
                                        fill="#f4eaff", width=4, arrow="last")
        elif kind == "meteor_blast":
            age = effect[3] - life
            radius = effect[4] * min(1, age / 12)
            self.canvas.create_oval(x - radius, y - radius * .7,
                                    x + radius, y + radius * .7,
                                    outline="#ffdf9c", width=5)
            self.canvas.create_oval(x - radius * .62, y - radius * .44,
                                    x + radius * .62, y + radius * .44,
                                    outline="#ff8b55", width=4)
            for shard in range(8):
                angle = math.tau * shard / 8 + age * .12
                self.canvas.create_line(x + math.cos(angle) * radius * .48,
                                        y + math.sin(angle) * radius * .32,
                                        x + math.cos(angle) * radius * 1.08,
                                        y + math.sin(angle) * radius * .78,
                                        fill="#fff0c9", width=3)
        elif kind == "slam":
            r = (22 - life) * 7 + 8
            ground_y = self.sy(self.ground) - 3
            self.canvas.create_line(x - r, ground_y, x + r, ground_y, fill=color, width=4)
            self.canvas.create_line(x - r * .6, ground_y - 7, x - r, ground_y, fill="#ffe0a3", width=2)
            self.canvas.create_line(x + r * .6, ground_y - 7, x + r, ground_y, fill="#ffe0a3", width=2)
        elif kind == "tnt_blast":
            age = 22 - life
            max_radius = effect[4] if len(effect) > 4 else 164
            radius = max_radius * min(1, age / 16)
            self.canvas.create_oval(x - radius, y - radius * .72,
                                    x + radius, y + radius * .72,
                                    fill="#db624d", outline="#ffe1a0", width=4)
            self.canvas.create_oval(x - radius * .63, y - radius * .46,
                                    x + radius * .63, y + radius * .46,
                                    fill="#ffbe5c", outline="#fff0c9", width=3)
            for shard in range(10):
                angle = math.tau * shard / 10 + age * .12
                self.canvas.create_line(x + math.cos(angle) * radius * .45,
                                        y + math.sin(angle) * radius * .35,
                                        x + math.cos(angle) * radius * 1.1,
                                        y + math.sin(angle) * radius * .9,
                                        fill="#fff2c7", width=3)
        elif kind == "impact":
            radius = (12 - life) * 2 + 4
            for spoke in range(8):
                angle = math.tau * spoke / 8
                inner = radius * .45
                outer = radius * (1.35 if spoke % 2 == 0 else .9)
                self.canvas.create_line(x + math.cos(angle) * inner, y + math.sin(angle) * inner,
                                        x + math.cos(angle) * outer, y + math.sin(angle) * outer,
                                        fill="#fff0c9" if spoke % 2 == 0 else "#ff9b8f", width=2)
        elif kind in ("dash", "lever", "burst", "hit", "warning", "parry", "muzzle", "spawn"):
            r = (24 - life) * 4 + 8
            if kind == "muzzle":
                self.canvas.create_polygon(x, y - r, x + r, y, x, y + r, x - r, y, fill=color, outline="#fff0cf")
            elif kind == "spawn":
                self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=color, width=3)
                self.canvas.create_oval(x - r * .55, y - r * .55, x + r * .55, y + r * .55,
                                        outline="#f5ffe2", width=2)
            elif kind == "hit":
                for spoke in range(12):
                    angle = math.tau * spoke / 12
                    inner, outer = r * .2, r * (1.0 if spoke % 2 == 0 else .62)
                    self.canvas.create_line(x + math.cos(angle) * inner, y + math.sin(angle) * inner,
                                            x + math.cos(angle) * outer, y + math.sin(angle) * outer,
                                            fill="#fff1d8" if spoke % 2 == 0 else color,
                                            width=3 if spoke % 2 == 0 else 2)
            elif kind == "parry":
                self.canvas.create_arc(x - r, y - r, x + r, y + r, start=25, extent=130,
                                       style="arc", outline="#d6fff0", width=5)
                self.canvas.create_arc(x - r * .7, y - r * .7, x + r * .7, y + r * .7,
                                       start=25, extent=130, style="arc", outline=color, width=3)
                for angle in (30, 72, 114, 156):
                    a = math.radians(angle)
                    self.canvas.create_line(x + math.cos(a) * r * .82, y - math.sin(a) * r * .82,
                                            x + math.cos(a) * r * 1.18, y - math.sin(a) * r * 1.18,
                                            fill="#fff0c9", width=2)
            elif kind == "dash":
                direction = effect[4] if len(effect) > 4 else 1
                self.canvas.create_oval(x - r, y - r * .5, x + r, y + r * .5,
                                        outline="#aafff1", width=3)
                for streak in range(5):
                    sy = y - r * .45 + streak * r * .22
                    self.canvas.create_line(x - direction * r * .45, sy,
                                            x - direction * (r + 24 + streak * 4), sy - 2,
                                            fill="#f2dfa5" if streak % 2 else color, width=2)
            elif kind == "burst":
                for shard in range(12):
                    angle = math.tau * shard / 12 + self.frame * .04
                    inner, outer = r * .3, r * (1.15 if shard % 2 == 0 else .8)
                    self.canvas.create_line(x + math.cos(angle) * inner, y + math.sin(angle) * inner,
                                            x + math.cos(angle) * outer, y + math.sin(angle) * outer,
                                            fill="#fff5d6" if shard % 2 == 0 else color, width=2)
            else:
                self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                        outline=self.color_mix(color, "#ffffff", .45), width=3)
                self.canvas.create_oval(x - r * .62, y - r * .62, x + r * .62, y + r * .62,
                                        outline=color, width=2)
        elif kind == "after":
            self.canvas.create_rectangle(x - (PLAYER_SPRITE_W - PLAYER_W) / 2, y - 2,
                                         x + PLAYER_SPRITE_W - (PLAYER_SPRITE_W - PLAYER_W) / 2,
                                         y + PLAYER_SPRITE_H - 2,
                                         fill="#78d5cf", stipple="gray50", outline="#d3fff2", width=1)

    def draw_hud(self):
        era = ERAS[min(self.chapter, len(ERAS) - 1)]
        c = self.canvas
        c.create_rectangle(0, 0, self.w, 60, fill="#121822", outline="#726c5b", width=2)
        c.create_text(20, 15, anchor="nw", text=f"ROUND {self.round_number:02d}  /  PART {self.chapter + 1}", fill=era["accent"], font=("TkDefaultFont", 15, "bold"))
        local_round = (self.round_number - 1) % 8 + 1
        phase_name = ("SHOP · SAFE ROOM" if self.midrun_shop_active else
                      "SHOP · TRAINING ROOM" if self.in_shop else
                      f"ZONE {min(self.room_wave_index + 1, ROOM_COUNT)}/{ROOM_COUNT} · ROUND {local_round}/8"
                      if self.phase == 0 else
                      f"SCHOLAR MIDBOSS · ZONE {min(self.room_wave_index + 1, ROOM_COUNT)}/{ROOM_COUNT}"
                      if self.phase == 1 else
                      "BOSS ARENA · SOLO" if self.boss_only_round else
                      f"FORMULA BOSS · ZONE {min(self.room_wave_index + 1, ROOM_COUNT)}/{ROOM_COUNT}")
        c.create_text(20, 42, anchor="nw", text=f"{era['place']}  ·  {era['age']}  ·  {phase_name}", fill="#c3bdab", font=("TkDefaultFont", 9, "bold"))
        weapon_name = "뉴턴의 지팡이" if self.staff_owned else "검"
        c.create_text(self.w - 20, 18, anchor="ne", text=f"{weapon_name}   HP {self.hp:03d}", fill="#f1e9d4", font=("TkDefaultFont", 13, "bold"))
        c.create_text(self.w - 215, 20, anchor="e", text=f"GOLD {self.gold} G",
                      fill="#ffd879", font=("TkDefaultFont", 12, "bold"))
        c.create_rectangle(self.w - 194, 34, self.w - 16, 51, fill="#24202d", outline="#796c6b", width=1)
        c.create_rectangle(self.w - 190, 37, self.w - 20, 48, fill="#3c3031", outline="#1b1a24")
        hp_width = 170 * max(0, self.hp) / self.max_hp
        c.create_rectangle(self.w - 190, 37, self.w - 190 + hp_width, 48, fill="#d46a59", outline="")
        if hp_width > 6:
            c.create_line(self.w - 187, 39, self.w - 190 + hp_width - 2, 39,
                          fill="#ffc2a0", width=1)
        c.create_line(self.w - 190, 50, self.w - 20, 50, fill="#161821", width=1)
        near_shop_bird = (self.midrun_shop_active
                          and abs(self.player["x"] - SHOP_BIRD_X) < 155)
        near_staff_stall = (self.midrun_shop_active
                            and abs(self.player["x"] - NEWTON_STALL_X) < 155)
        ability_text = (f"비둘기 · {self.key_label(self.controls['interact'])} 메뉴 · 1 회복 50 G / 2 가호 소환 500 G" if near_shop_bird else
                        f"뉴턴의 지팡이 · {self.key_label(self.controls['shop_staff'])}/{self.key_label(self.controls['interact'])} 구매 100 G" if near_staff_stall and not self.staff_owned else
                        f"지팡이 보유 · {self.key_label(self.controls['attack'])} 중력 강타 · {self.key_label(self.controls['ranged'])} 운석" if near_staff_stall and self.staff_owned else
                        f"안전 상점 · 지팡이 100 G · 완전 회복 50 G · {self.key_label(self.controls['interact'])} 레버" if self.midrun_shop_active and not self.shop_exit_open else
                        "상점 출구 개방 · 오른쪽으로 이동해 다음 구역으로" if self.midrun_shop_active else
                        f"허수아비 누적 피해 {self.training_damage}  ·  출구에서 {self.key_label(self.controls['interact'])}" if self.in_shop else
                        "  ".join(f"{self.key_label(self.controls[action])}:{ERAS[idx]['skill']}"
                                  for action, idx in zip(("skill_q", "skill_w", "skill_e"), self.skills))
                        or "아직 배운 기술 없음  ·  검과 대쉬로 싸우세요")
        x_action = "중력 강타" if self.staff_owned else "검"
        f_action = "운석" if self.staff_owned else "압축총"
        blessing_action = "미획득" if self.blessing is None else BLESSINGS[self.blessing]["skill"]
        c.create_text(self.w / 2, 24,
                      text=(f"{self.key_label(self.controls['move_left'])}/{self.key_label(self.controls['move_right'])} 이동  "
                            f"{self.key_label(self.controls['jump'])} 점프  {self.key_label(self.controls['dash'])} 대쉬  "
                            f"{self.key_label(self.controls['attack'])} {x_action}  {self.key_label(self.controls['ranged'])} {f_action}  "
                            f"{self.key_label(self.controls['parry'])} 패링  {self.key_label(self.controls['blessing'])} {blessing_action}  M 설정"),
                      fill="#fff0cf", font=("TkDefaultFont", 9, "bold"))
        gun_status = "준비" if self.frame >= self.gun_cd else f"{(self.gun_cd - self.frame) / 60:.1f}초"
        blessing_status = ("가호 없음" if self.blessing is None else "준비" if self.frame >= self.blessing_cd
                           else f"{(self.blessing_cd - self.frame) / 60:.1f}초")
        c.create_text(self.w / 2, 47,
                      text=f"{self.key_label(self.controls['ranged'])} {f_action} {gun_status}   ·   {self.key_label(self.controls['blessing'])} 가호 {blessing_status}   ·   {self.key_label(self.controls['stats'])} 스탯",
                      fill="#74d8cf" if self.blessing is None or self.frame >= self.blessing_cd else "#c4b5a5",
                      font=("TkDefaultFont", 9, "bold"))
        if self.skills:
            skill_status = []
            skill_actions = ("skill_q", "skill_w", "skill_e")
            for skill_index, (action, chapter) in enumerate(zip(skill_actions, self.skills)):
                key = self.key_label(self.controls[action])
                remaining = max(0, self.skill_cd[skill_index] - self.frame)
                status = "준비" if remaining == 0 else f"{remaining / 60:.1f}초"
                skill_status.append(f"{key} {ERAS[chapter]['skill']} · {status}")
            c.create_text(self.w / 2, self.h - 50, text="   |   ".join(skill_status),
                          fill="#a9f0ce", font=("TkDefaultFont", 10, "bold"))
        boss = next((enemy for enemy in self.enemies if enemy["rank"] == "boss" and enemy["hp"] > 0), None)
        if boss:
            bx1, bx2 = self.w * .29, self.w * .71
            c.create_rectangle(bx1 - 10, 67, bx2 + 10, 108, fill="#211b2b", outline="#d6ad61", width=2)
            c.create_text(self.w / 2, 74, text=f"{ERAS[self.chapter]['place']}  ·  {ERAS[self.chapter]['boss']}", fill="#ffe4a2", font=("TkDefaultFont", 12, "bold"))
            c.create_rectangle(bx1, 91, bx2, 103, fill="#4b3038", outline="#9e725e")
            c.create_rectangle(bx1, 91, bx1 + (bx2 - bx1) * max(0, boss["hp"] / boss["maxhp"]), 103,
                               fill="#df6d61", outline="")
            c.create_text(bx2 - 4, 97, anchor="e", text=f"{max(0, int(boss['hp']))} / {boss['maxhp']}",
                           fill="#fff0cf", font=("TkDefaultFont", 8, "bold"))
            boss_actions = {
                "lever": "지렛대 반격 · 가까우면 튕겨냅니다",
                "wheel_roll": "도르래 바퀴 돌진 · 접촉 피해 주의",
                "catapult_rock": "투석기 발사 · 날아오는 돌을 피하세요",
                "catapult": "투석기 도약 · 표시된 착지 지점에서 벗어나세요",
                "fall": "낙하 추 투척 · 바닥 표시를 피하세요",
                "parabola": "포물선 연속 투척 · 탄도 방향을 살피세요",
                "gravity": "중력장 생성 · 표시된 범위에서 벗어나세요",
                "orbit": "궤도탄 방출 · 여러 방향의 탄환을 피하세요",
            }
            if boss["state"] == "warning":
                label = boss_actions.get(boss.get("action", ""), "공격 준비 중")
                alert = self.warning_color(boss)
                c.create_rectangle(self.w * .22, 112, self.w * .78, 148,
                                   fill=self.color_mix("#2d202b", alert, .2), outline=alert, width=2)
                c.create_text(self.w / 2, 130,
                              text=f"⚠ {label}   ·   {boss['timer'] / 60:.1f}초",
                              fill=alert, font=("TkDefaultFont", 12, "bold"))
        scholar = next((enemy for enemy in self.enemies
                        if enemy["rank"] == "scholar" and enemy["hp"] > 0), None)
        if scholar:
            bx1, bx2 = self.w * .32, self.w * .68
            c.create_rectangle(bx1 - 9, 67, bx2 + 9, 108,
                               fill="#211b2b", outline="#b8a5df", width=2)
            c.create_text(self.w / 2, 74,
                          text=f"중간보스  ·  {scholar['kind']}  ·  중력장",
                          fill="#e5d7ff", font=("TkDefaultFont", 12, "bold"))
            c.create_rectangle(bx1, 91, bx2, 103, fill="#352c49", outline="#8974b5")
            c.create_rectangle(bx1, 91,
                               bx1 + (bx2 - bx1) * max(0, scholar["hp"] / scholar["maxhp"]), 103,
                               fill="#9d82d5", outline="")
            c.create_text(bx2 - 4, 97, anchor="e",
                          text=f"{max(0, int(scholar['hp']))} / {scholar['maxhp']}",
                          fill="#fff0cf", font=("TkDefaultFont", 8, "bold"))
            if scholar["state"] == "warning":
                warnings = {
                    "scholar_crush": "중력 강타 · 표시된 원을 벗어나세요",
                    "scholar_swing": "근접 검격 · 뒤로 물러나세요",
                    "column": "중력 기둥 · 표시된 위치를 피하세요",
                    "pressure": "압력파 · 예고선을 피하세요",
                    "orbit": "궤도탄 · 탄도 사이로 피하세요",
                }
                warning_text = warnings.get(scholar.get("action", ""), "공격 준비 중")
                alert = self.warning_color(scholar)
                c.create_rectangle(self.w * .25, 112, self.w * .75, 146,
                                   fill=self.color_mix("#292438", alert, .2), outline=alert, width=2)
                c.create_text(self.w / 2, 129,
                              text=f"⚠ {warning_text} · {scholar['timer'] / 60:.1f}초",
                              fill=alert, font=("TkDefaultFont", 11, "bold"))
        parry_status = "PARRY READY" if self.frame >= self.parry_cd else f"PARRY {((self.parry_cd - self.frame) / 60):.1f}s"
        c.create_text(self.w - 20, 56, anchor="se", text=parry_status, fill="#b7f2ce", font=("TkDefaultFont", 8, "bold"))
        if self.scholar_gravity_active():
            c.create_text(self.w / 2, 66, text="중력장에 붙잡힘 · 이동 속도 감소",
                          fill="#d9c5ff", font=("TkDefaultFont", 10, "bold"))
        c.create_text(self.w / 2, self.h - 28, text=ability_text, fill="#e6d49d", font=("TkDefaultFont", 10, "bold"))
        if self.frame < self.notice_until:
            c.create_text(self.w / 2, 84, text=self.notice, fill="#fff3d2", font=("TkDefaultFont", 13, "bold"))
        if self.round_clear and self.exit_door_x is not None and abs(self.player["x"] - self.exit_door_x) < 180:
            c.create_text(self.w / 2, 84, text=f"{self.key_label(self.controls['interact'])} 문으로 들어가 다음 방으로", fill="#fff3d2", font=("TkDefaultFont", 13, "bold"))
        if self.round_clear and self.bird_x is not None and abs(self.player["x"] - self.bird_x) < 140:
            c.create_text(self.w / 2, 110, text=f"{self.key_label(self.controls['interact'])} 비둘기와 대화 · 1 체력  2 공격력  3 공격속도  5 회복 물약",
                          fill="#fff0c9", font=("TkDefaultFont", 11, "bold"))
        if self.bird_menu:
            panel_left, panel_top = self.w / 2 - 245, self.h - 152
            c.create_rectangle(panel_left, panel_top, panel_left + 490, panel_top + 142,
                               fill="#182332", outline="#f1cc76", width=3)
            c.create_text(self.w / 2, panel_top + 22, text=f"비둘기 · 보유 동전 {self.gold} G",
                          fill="#ffe5a0", font=("TkDefaultFont", 14, "bold"))
            c.create_text(self.w / 2, panel_top + 53,
                          text=f"1 체력 +100 · {self.stat_cost('health')} G     2 공격력 +5% · {self.stat_cost('damage')} G",
                          fill="#f1ead9", font=("TkDefaultFont", 11, "bold"))
            c.create_text(self.w / 2, panel_top + 79,
                          text=f"3 공격속도 +5% · {self.stat_cost('attack_speed')} G",
                          fill="#f1ead9", font=("TkDefaultFont", 11, "bold"))
            c.create_text(self.w / 2, panel_top + 111,
                          text=f"5 회복 물약 +40 HP · 25 G     ·     {self.key_label(self.controls['interact'])}/ESC 닫기",
                          fill="#a9d9d4", font=("TkDefaultFont", 10, "bold"))
        if self.shop_bird_menu:
            panel_left, panel_top = self.w / 2 - 265, self.h - 132
            c.create_rectangle(panel_left, panel_top, panel_left + 530, panel_top + 112,
                               fill="#182332", outline="#9da8c8", width=3)
            c.create_text(self.w / 2, panel_top + 22,
                          text=f"망토 비둘기 · 보유 동전 {self.gold} G",
                          fill="#e2d5ff", font=("TkDefaultFont", 14, "bold"))
            c.create_text(self.w / 2, panel_top + 52,
                          text="1 완전 회복 · 50 G     2 위인의 가호 소환 · 500 G",
                          fill="#f1ead9", font=("TkDefaultFont", 11, "bold"))
            c.create_text(self.w / 2, panel_top + 84,
                          text=f"{self.key_label(self.controls['interact'])}/ESC 닫기",
                          fill="#a9d9d4", font=("TkDefaultFont", 10, "bold"))
        elif self.in_shop and abs(self.player["x"] - 1080) < 180:
            c.create_text(self.w / 2, 84,
                          text=f"{self.key_label(self.controls['interact'])} 출구로 나가기",
                          fill="#fff3d2", font=("TkDefaultFont", 13, "bold"))
        if self.transition:
            c.create_text(self.w / 2, self.h * .32, text="FORMULA MASTERED" if self.phase == 2 else "AREA CLEARED", fill=era["accent"], font=("TkDefaultFont", 26, "bold"))
        if self.game_over or self.finished:
            c.create_rectangle(0, 0, self.w, self.h, fill="#080a11", stipple="gray50", outline="")
            title = "CHRONICLE COMPLETE" if self.finished else "FALLEN IN THE EXPERIMENT"
            c.create_text(self.w / 2, self.h / 2 - 25, text=title, fill="#f0d28a" if self.finished else "#e87568", font=("TkDefaultFont", 28, "bold"))
            c.create_text(self.w / 2, self.h / 2 + 24, text="R 키로 다시 시작", fill="#eee3cc", font=("TkDefaultFont", 13))



class BossDemo(PhysicsChronicles):
    """Skip every ordinary room and cycle directly through the three bosses."""

    def __init__(self, root):
        self.demo_round = 8
        self.max_hp = 200
        self.player_damage_multiplier = 3
        super().__init__(root)
        root.title("PHYSICS CHRONICLES · BOSS DEMO")
        self.say("보스 시연 1/3 · 아르키메데스")

    def new_encounter(self):
        # The base game maps rounds 8, 16 and 24 to its three historical bosses.
        self.round_number = self.demo_round
        super().new_encounter()
        self.hp = self.max_hp
        self.player.update(x=380.0, y=float(self.ground - PLAYER_H), vx=0, vy=0,
                           face=1, grounded=True, drop=0, jumps_used=0)
        if self.spawn_queue:
            kind, _x, rank = self.spawn_queue[0]
            self.spawn_queue[0] = (kind, 820, rank)
        self.spawn_next_at = self.frame + 15
        self.gun_cd = self.dash_cd = self.attack_cd = 0
        self.skill_cd = [0, 0, 0]

    def key_down(self, event):
        if event.keysym.lower() == "r" and (self.game_over or self.finished):
            self.demo_round = 8
            self.skills = []
        super().key_down(event)

    def advance_from_door(self):
        if not self.round_clear:
            return
        self.round_clear = False
        defeated_chapter = self.demo_round // 8 - 1
        if defeated_chapter not in self.skills:
            self.skills.append(defeated_chapter)
        if self.demo_round < 24:
            self.demo_round += 8
            self.round_number = self.demo_round
            self.new_encounter()
            boss_index = self.demo_round // 8
            self.say(f"보스 시연 {boss_index}/3 · {ERAS[boss_index - 1]['boss']}")
        else:
            self.finished = True
            self.say("세 보스 시연 완료 · R 키로 다시 시작")

    def draw_hud(self):
        super().draw_hud()
        boss_index = self.demo_round // 8
        era = ERAS[boss_index - 1]
        boss_warning = any(e["rank"] == "boss" and e["state"] == "warning" for e in self.enemies)
        demo_label_y = 166 if boss_warning else 126
        self.canvas.create_text(self.w / 2, demo_label_y,
                                text=f"BOSS DEMO  {boss_index}/3   ·   {era['place']} / {era['boss']}",
                                fill="#ffe4a2", font=("TkDefaultFont", 11, "bold"))


def main():
    root = tk.Tk()
    error_path = Path.home() / "Physics Chronicles_error.log"
    error_dialog_shown = False

    def report_error(exc_type, exc_value, exc_traceback):
        nonlocal error_dialog_shown
        try:
            with error_path.open("a", encoding="utf-8") as log:
                log.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=log)
        except OSError:
            traceback.print_exception(exc_type, exc_value, exc_traceback)
        if not error_dialog_shown:
            error_dialog_shown = True
            try:
                from tkinter import messagebox
                messagebox.showerror(
                    "Physics Chronicles 오류",
                    f"문제가 발생해 기록했습니다.\n오류 기록 파일: {error_path}",
                    parent=root,
                )
            except Exception:
                pass

    root.report_callback_exception = report_error
    try:
        PhysicsChronicles(root)
        root.mainloop()
    except Exception:
        report_error(*sys.exc_info())
        try:
            root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    main()
