"""Regression checks for the Python game rules (no browser required)."""
import json
import random
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

frames = []
js_module = types.ModuleType("js")
js_module.window = SimpleNamespace(gameBridge=SimpleNamespace(draw=frames.append))
sys.modules.setdefault("js", js_module)
import game


class GameRegressionTests(unittest.TestCase):
    def new_game(self, seed=7):
        random.seed(seed)
        g = game.Game()
        g.start("검증용")
        return g

    def test_random_starts_never_send_beastkin_to_royal_city(self):
        royal_areas = {"왕실 상점가", "왕국 기사단", "왕국 안", "왕의 방"}
        for seed in range(100):
            g = self.new_game(seed)
            self.assertFalse(g.player["race"] == "수인" and g.area in royal_areas)

    def test_religion_is_assigned_from_the_random_start(self):
        g = game.Game()
        with patch("game.random.choice", side_effect=["인간", "여성", "교회 밖"]):
            g.start("신앙 검증")
        self.assertEqual(g.player["religion"], "교회 신앙")

    def test_all_area_scenes_render(self):
        g = self.new_game()
        for area, (width, height) in game.MAP_SIZE.items():
            g.area = area
            g.player.update(area=area, x=width // 2, y=height // 2)
            g.spawn_enemies()
            g.draw()
        self.assertTrue(frames)
        self.assertIsInstance(json.loads(frames[-1]), list)

    def test_save_and_resume_preserve_player_area_quest_and_battle(self):
        g = self.new_game()
        g.area = "숲"
        g.player.update(area="숲", x=1234, y=765, gold=137,
                        quest={"title":"숲의 마물 퇴치","source":"church","goal":1,"count":0})
        g.enemies = [{"name":"늑대","x":1200,"y":740,"hp":20,"maxhp":40,
                      "atk":6,"level":1,"alive":True}]
        g.start_battle(0)
        g.battle["submenu"] = "attack"
        restored = game.Game()
        self.assertTrue(restored.load_snapshot(g.save_snapshot()))
        self.assertEqual(restored.player["gold"], 137)
        self.assertEqual(restored.area, "숲")
        self.assertEqual(restored.player["quest"]["title"], "숲의 마물 퇴치")
        self.assertEqual(restored.mode, "battle")
        self.assertEqual(restored.battle["submenu"], "attack")

    def test_corrupt_save_is_rejected_without_starting_game(self):
        g = game.Game()
        self.assertFalse(g.load_snapshot("not valid json"))
        self.assertFalse(g.started)

    def test_game_autosaves_after_start_and_during_play(self):
        g = game.Game()
        with patch.object(game.window.gameBridge, "save", create=True) as save:
            g.start("저장 검증")
            save.assert_called_once()
            save.reset_mock()
            g.tick(1.6, "[]", "[]", "null")
            save.assert_called_once()

    def test_prayer_is_limited_by_completed_church_quests(self):
        g = self.new_game()
        p = g.player
        p.update(faction="교회", job="전사", area="교회 안", prayer_count=0,
                 church_quests_completed=1, prayer_due=True, x=480, y=130)
        g.area = "교회 안"
        g.interact()
        self.assertEqual(p["prayer_count"], 1)
        self.assertFalse(p["prayer_due"])
        g.interact()
        self.assertEqual(p["prayer_count"], 1)

    def test_church_faith_restores_mp_when_praying(self):
        g = self.new_game()
        p = g.player
        p.update(faction="교회", job="신자", religion="교회 신앙", area="교회 안",
                 prayer_count=0, church_quests_completed=1, mp=0, x=480, y=130)
        g.area = "교회 안"
        g.interact()
        self.assertEqual(p["mp"], 3)

    def test_kingdom_faith_adds_gold_to_royal_quest_reward(self):
        g = self.new_game()
        p = g.player
        p.update(faction="왕실", religion="왕실 신앙", job="전사", gold=0,
                 quest={"title":"왕실 토벌","source":"kingdom","goal":1,"count":1})
        g.complete_monster_quest()
        self.assertEqual(p["gold"], 30)

    def test_forest_faith_improves_flee_odds(self):
        g = self.new_game()
        g.player["religion"] = "숲의 신앙"
        g.enemies = [{"name":"늑대","x":400,"y":300,"hp":90,"maxhp":90,
                      "atk":1,"level":1,"alive":True}]
        g.start_battle(0)
        with patch("game.random.random", return_value=0.52):
            g.battle_action("flee")
        self.assertEqual(g.mode, "world")

    def test_successful_priest_quest_grants_one_prayer(self):
        g = self.new_game()
        p = g.player
        p.update(faction="교회", job="전사")
        g.after_church_quest("church")
        self.assertEqual(p["church_quests_completed"], 1)
        self.assertTrue(p["prayer_due"])

    def test_ten_church_quests_and_prayers_finish_chapter_as_crusader(self):
        g = self.new_game()
        p = g.player
        p.update(faction="교회", job="전사", religion="교회 신앙", area="교회 안",
                 prayer_count=0, church_quests_completed=0, priest_refusals=0, prayer_due=False)
        g.area = "교회 안"
        p.update(x=480, y=130)
        for _ in range(10):
            p["quest"]={"title":"숲의 마물 퇴치","source":"church","goal":1,"count":1}
            g.complete_monster_quest()
            g.dialog=None
            g.interact()
        self.assertEqual(p["prayer_count"], 10)
        self.assertEqual(p["job"], "성전사")
        self.assertTrue(p["promoted"])
        self.assertEqual(g.dialog["title"], "직업 승급")

    def test_ten_royal_quests_finish_chapter_as_knight(self):
        g = self.new_game()
        p = g.player
        p.update(faction="왕실", job="전사", religion="왕실 신앙", king_quests=0)
        for _ in range(10):
            p["quest"]={"title":"왕실 토벌","source":"kingdom","goal":1,"count":1}
            g.complete_monster_quest()
        self.assertEqual(p["king_quests"], 10)
        self.assertEqual(p["job"], "기사")
        self.assertEqual(g.dialog["title"], "직업 승급")

    def test_exiled_church_warrior_can_leave_village_but_not_reenter_church(self):
        g = self.new_game()
        p = g.player
        p.update(faction="교회", area="교회 안", prayer_due=True)
        g.area = "교회 안"
        g.move_area("마을")
        self.assertEqual(g.area, "마을")
        self.assertEqual(p["faction"], "방랑자")
        self.assertFalse(p["prayer_due"])
        g.move_area("숲")
        self.assertEqual(g.area, "숲")
        g.move_area("교회 밖")
        self.assertEqual(g.area, "숲")

    def test_active_quest_cannot_be_overwritten(self):
        g = self.new_game()
        g.accept_quest("첫 의뢰", "church")
        g.accept_quest("두 번째 의뢰", "kingdom")
        self.assertEqual(g.player["quest"]["title"], "첫 의뢰")

    def test_player_must_leave_current_faction_before_taking_a_new_job(self):
        g = self.new_game()
        p = g.player
        g.area = "왕국 기사단"
        p.update(area="왕국 기사단", faction="교회", job="전사", x=500, y=330)
        g.interact()
        self.assertNotIn("전사로 수련 시작", g.dialog["options"])
        g.choose(0)
        self.assertEqual(p["faction"], "무소속")
        self.assertEqual(p["job"], "전사")

    def test_killing_a_human_does_not_complete_monster_quest(self):
        g = self.new_game()
        p = g.player
        p.update(atk=50, quest={"title":"숲의 마물 퇴치","source":"church","goal":1,"count":0})
        g.enemies = [{"name":"상점 주인","x":400,"y":300,"hp":1,"maxhp":1,
                      "atk":1,"level":1,"alive":True,"human":True}]
        g.start_battle(0)
        g.battle_action("basic")
        self.assertEqual(g.mode, "battle")
        self.assertEqual(g.battle["effect"], "slash")
        g.tick(0.6, "[]", "[]", "null")
        self.assertEqual(p["quest"]["count"], 0)
        self.assertIsNotNone(p["quest"])

    def test_thief_becomes_bandit_after_killing_a_human(self):
        g = self.new_game()
        p = g.player
        p.update(job="도둑", faction="방랑자", atk=50)
        g.enemies = [{"name":"상점 주인","x":400,"y":300,"hp":1,"maxhp":1,
                      "atk":1,"level":1,"alive":True,"human":True}]
        g.start_battle(0)
        g.battle_action("basic")
        g.tick(0.6, "[]", "[]", "null")
        self.assertEqual(p["job"], "도적")
        self.assertEqual(g.dialog["title"], "직업 승급")

    def test_repeat_equipment_purchase_does_not_stack_stats(self):
        g = self.new_game()
        p = g.player
        p["gold"] = 500
        g.open_shop()
        g.choose(1)
        self.assertEqual(g.dialog["title"], "무기 진열장")
        g.choose(0)
        attack_after_purchase = p["atk"]
        gold_after_purchase = p["gold"]
        g.open_shop()
        g.choose(1)
        g.choose(0)
        self.assertEqual(p["atk"], attack_after_purchase)
        self.assertEqual(p["gold"], gold_after_purchase)

    def test_beastkin_pays_five_percent_more_for_equipment(self):
        g = self.new_game()
        g.player["race"] = "수인"
        self.assertEqual(g.shop_price(20), 21)
        self.assertEqual(g.shop_price(60), 63)
        self.assertEqual(g.shop_price(55), 58)

    def test_owned_weapons_can_be_swapped_without_losing_level_stats(self):
        g = self.new_game()
        p = g.player
        p["gold"] = 500
        g.gain_xp(35)
        level_attack = p["atk"]
        g.buy_weapon("철검", 60)
        iron_attack = p["atk"]
        g.buy_weapon("사냥꾼 활", 85)
        self.assertEqual(p["weapon"], "사냥꾼 활")
        self.assertEqual(p["atk"], level_attack + 8)
        g.open_inventory()
        g.choose(1)
        g.choose(1)
        self.assertEqual(p["weapon"], "철검")
        self.assertEqual(p["atk"], iron_attack)

    def test_owned_armor_can_be_swapped_without_losing_level_stats(self):
        g = self.new_game()
        p = g.player
        p["gold"] = 500
        g.gain_xp(35)
        level_defense = p["def"]
        g.buy_armor("가죽 갑옷", 55)
        leather_defense = p["def"]
        g.buy_armor("기사 갑옷", 120)
        self.assertEqual(p["def"], level_defense + 6)
        g.open_inventory()
        g.choose(2)
        g.choose(0)
        self.assertEqual(p["armor"], "여행자 옷")
        self.assertEqual(p["def"], level_defense)
        self.assertGreater(leather_defense, level_defense)

    def test_equipped_weapon_and_armor_change_character_render_data(self):
        g = self.new_game()
        shapes = []
        g.draw_character(shapes, 100, 100, "검증", "전사", "인간", "왕실", 1.0,
                         weapon="사냥꾼 활", armor="기사 갑옷")
        colors = {shape.get("c") for shape in shapes}
        self.assertIn("#9ba5af", colors)
        self.assertIn("#895b38", colors)

    def test_attack_opens_skill_choices_before_damage(self):
        g = self.new_game()
        g.enemies = [{"name":"늑대","x":400,"y":300,"hp":90,"maxhp":90,
                      "atk":1,"level":1,"alive":True}]
        g.start_battle(0)
        g.battle_action("attack")
        self.assertEqual(g.battle["submenu"], "attack")
        self.assertEqual(g.enemies[0]["hp"], 90)
        g.battle_action("skill")
        self.assertLess(g.enemies[0]["hp"], 90)

    def test_defense_blocks_the_enemy_turn(self):
        g = self.new_game()
        g.player["hp"] = 55
        g.enemies = [{"name":"멧돼지","x":400,"y":300,"hp":90,"maxhp":90,
                      "atk":30,"level":1,"alive":True}]
        g.start_battle(0)
        g.battle_action("defend")
        self.assertEqual(g.player["hp"], 55)
        self.assertFalse(g.battle["defending"])

    def test_bandage_does_not_consume_a_combat_turn(self):
        g = self.new_game()
        g.player.update(hp=50, maxhp=100, bandages=2)
        g.enemies = [{"name":"늑대","x":400,"y":300,"hp":90,"maxhp":90,
                      "atk":30,"level":1,"alive":True}]
        g.start_battle(0)
        g.battle_action("item")
        self.assertEqual(g.player["hp"], 62)
        self.assertEqual(g.player["bandages"], 1)
        self.assertEqual(g.enemies[0]["hp"], 90)

    def test_bandage_is_not_wasted_at_full_health(self):
        g = self.new_game()
        p = g.player
        p.update(hp=100, maxhp=100, bandages=1)
        g.enemies = [{"name":"늑대","x":400,"y":300,"hp":90,"maxhp":90,
                      "atk":1,"level":1,"alive":True}]
        g.start_battle(0)
        g.battle_action("item")
        self.assertEqual(p["bandages"], 1)
        self.assertEqual(g.enemies[0]["hp"], 90)

    def test_forest_walk_triggers_an_immediate_ambush(self):
        g = self.new_game()
        g.area = "숲"
        g.player.update(area="숲", x=1200, y=800)
        g.spawn_enemies()
        g.walk_meter = 189
        with patch("game.random.random", return_value=0.0):
            g.update_world_ai(0.1, 2)
        self.assertEqual(g.mode, "battle")
        self.assertIn(g.enemies[g.battle["index"]]["name"], {"멧돼지", "늑대", "고블린"})

    def test_wanderer_groups_move_automatically(self):
        g = self.new_game()
        g.area = "숲"
        g.player["area"] = "숲"
        g.spawn_enemies()
        before = (g.wanderers[0]["x"], g.wanderers[0]["y"])
        g.update_world_ai(0.5, 0)
        after = (g.wanderers[0]["x"], g.wanderers[0]["y"])
        self.assertNotEqual(before, after)

    def test_e_dismisses_the_notice_without_interacting(self):
        g = self.new_game()
        g.notice = "닫을 안내"
        g.notice_t = 3
        g.tick(0.03, "[]", '["e"]', "null")
        self.assertEqual(g.notice_t, 0)
        self.assertIsNone(g.dialog)

    def test_royal_route_is_connected_in_order(self):
        g = self.new_game()
        g.area = "마을"
        g.player.update(area="마을", race="인간", faction="왕실")
        route = ("왕실 상점가", "왕국 기사단", "왕국 안", "왕의 방")
        for area in route:
            g.move_area(area)
            self.assertEqual(g.area, area)

    def test_death_returns_to_last_area_and_halves_gold(self):
        g = self.new_game()
        g.player.update(hp=1, maxhp=100, gold=101, visited_faction="교회 안")
        g.enemies = [{"name":"늑대","x":400,"y":300,"hp":90,"maxhp":90,
                      "atk":40,"level":1,"alive":True}]
        g.start_battle(0)
        g.enemy_turn()
        self.assertEqual(g.area, "교회 안")
        self.assertEqual(g.player["gold"], 50)
        self.assertEqual(g.player["hp"], g.player["maxhp"])
        self.assertEqual((g.player["x"], g.player["y"]), (480, 640))


if __name__ == "__main__":
    unittest.main()
