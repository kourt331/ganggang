"""Chapter 1 prototype: top-down, turn-based fantasy RPG. Runs in Pyodide."""
import json, random, math
from js import window

W, H = 960, 600
AREAS = {
    "숲": ("#243b31", "#35543a"), "마을": ("#64513c", "#806647"),
    "교회 밖": ("#394356", "#56617a"), "교회 안": ("#4b5365", "#6b7180"),
    "왕실 상점가": ("#49394c", "#765343"), "왕국 기사단": ("#3d4652", "#56616a"),
    "왕국 안": ("#624d3d", "#806348"), "왕의 방": ("#503b43", "#80605a"),
}
MAP_SIZE = {
    "숲": (2400, 1600), "마을": (1400, 1000), "교회 밖": (1200, 900), "교회 안": (960, 720),
    "왕실 상점가": (1200, 900), "왕국 기사단": (1000, 760), "왕국 안": (1000, 760), "왕의 방": (900, 650),
}

class Game:
    def __init__(self):
        self.started = False
        self.keys_last = set()
        self.player = {}
        self.area = "숲"
        self.dialog = None
        self.notice = ""
        self.notice_t = 0
        self.enemies = []
        self.wanderers = []
        self.walk_meter = 0
        self.encounter_meter = 0
        self.tick_n = 0

    def start(self, name):
        race = random.choice(["인간", "수인"])
        gender = random.choice(["남성", "여성"])
        starts = ["숲", "교회 밖", "왕실 상점가"] if race == "인간" else ["숲", "교회 밖"]
        area = random.choice(starts)
        faction = {"숲":"방랑자", "교회 밖":"교회", "왕실 상점가":"왕실"}[area]
        mw,mh=MAP_SIZE[area]
        self.player = {
            "name": (name or "이름 없는 여행자")[:14], "race":race, "gender":gender,
            "area":area,"faction":faction,"job":"미정","x":mw//2,"y":mh//2,
            "hp":100,"maxhp":100,"mp":30,"maxmp":30,"level":1,"xp":0,
            "gold":80,"bandages":1,"weapon":"낡은 검","armor":"여행자 옷",
            "atk":10,"def":3,"quest":None,"quest_kills":0,"priest_refusals":0,
            "prayer_count":0,"church_quests_completed":0,"prayer_due":False,"king_quests":0,"exiled":False,
            "bandit_unlocked":False,"visited_faction":faction,"promoted":False,
            "inventory":["낡은 검","여행자 옷","회복 붕대 ×1"],"story_flags":[]
        }
        self.player["visited_faction"]=area
        self.area=area; self.enemies=[]; self.wanderers=[]; self.dialog=None; self.started=True
        self.mode="world";self.walk_meter=0;self.encounter_meter=0
        self.notice = self.intro_text(); self.notice_t=9
        self.spawn_enemies()
        self.draw()

    def intro_text(self):
        p=self.player
        lines={"교회 밖":"성직자가 전쟁의 불길이 번진 숲을 바라본다. 교회 안으로 들어가 전사나 신자의 길을 얻을 수 있다.",
               "왕실 상점가":"왕실 도시의 상점가. 기사단으로 향하는 길과 궁성으로 향하는 성문이 있다.",
               "숲":"숲의 방랑자들이 불가에 모여 있다. 마을과 교회는 숲의 마물 때문에 긴장하고, 왕실은 방랑자의 출입을 금한다."}
        return f"{p['race']} · {p['gender']}\n{lines[p['area']]}"

    def say(self, text, seconds=4): self.notice=str(text); self.notice_t=seconds
    def gain_xp(self, amount):
        p=self.player;p["xp"]+=amount;level_message=[]
        while p["xp"]>=p["level"]*35:
            p["xp"]-=p["level"]*35;p["level"]+=1;p["maxhp"]+=8;p["maxmp"]+=3
            p["hp"]=p["maxhp"];p["mp"]=p["maxmp"];p["atk"]+=2;p["def"]+=1
            level_message.append(f"레벨 {p['level']}!")
        if level_message:self.say(" ".join(level_message)+" 능력치가 올랐다.")
    def spawn_enemies(self):
        self.enemies=[]
        self.wanderers=[]
        if self.area=="숲":
            names=["멧돼지","늑대","고블린"]
            for i in range(7):
                self.enemies.append({"name":random.choice(names),"x":random.randint(160,2200),"y":random.randint(130,1450),"hp":random.choice([26,34,42]),"maxhp":42,"atk":random.randint(5,9),"level":random.choice([1,1,2]),"alive":True,"vx":random.choice([-1,1])*random.randint(10,22),"vy":random.choice([-1,1])*random.randint(8,18),"turn":random.uniform(1,5)})
            for _ in range(random.randint(3,5)):
                self.wanderers.append({"x":random.randint(180,2200),"y":random.randint(150,1400),"vx":random.choice([-1,1])*random.randint(20,38),"vy":random.choice([-1,1])*random.randint(12,26),"turn":random.uniform(1,4),"size":random.randint(2,4)})
        elif self.area in ("왕실 상점가","왕국 기사단","왕국 안","왕의 방") and self.player.get("job") in ("도둑","도적"):
            self.enemies.append({"name":"왕실 경비","x":MAP_SIZE[self.area][0]//2,"y":MAP_SIZE[self.area][1]//2-90,"hp":52,"maxhp":52,"atk":11,"level":2,"alive":True,"human":True})

    def entities(self):
        data=[]
        if self.area=="숲":
            data=[("방랑자 야영지",240,210,"camp"),("마을로 가는 길",2310,800,"exit_village"),("숲길 표지판",120,780,"sign")]
            for i,g in enumerate(self.wanderers):data.append(("방랑자 집단",g["x"],g["y"],"wanderer_party",i))
        if self.area=="마을":
            data=[("상점",260,280,"shop"),("주민",700,300,"villager"),("숲",55,500,"exit_forest"),("교회로",700,55,"exit_church"),("왕실 상점가",1350,500,"exit_kingdom")]
            if self.player.get("job")=="기사" and self.player.get("faction")=="방랑자":data.append(("기사단 추격대",700,780,"knight_hunters"))
        if self.area=="교회 밖":data=[("교회 입구",600,95,"enter_church"),("마을로",60,450,"exit_village"),("신자들",820,470,"villager")]
        if self.area=="교회 안":data=[("성직자",700,230,"priest"),("수련관",240,260,"trainer_church"),("기도 제단",480,130,"altar"),("밭",760,560,"field"),("청소 구역",210,540,"cleaning"),("교회 밖",480,680,"exit_churchyard")]
        if self.area=="왕실 상점가":data=[("상점",330,300,"shop"),("왕국 기사단으로",1120,450,"exit_barracks"),("마을로",50,450,"exit_village")]
        if self.area=="왕국 기사단":data=[("왕실 교관",500,330,"trainer_kingdom"),("왕실 상점가",500,710,"exit_market"),("왕국 안으로",500,65,"exit_city")]
        if self.area=="왕국 안":data=[("왕의 방",500,70,"exit_throne"),("왕실 상점가",500,710,"exit_market"),("기사단",80,360,"exit_barracks"),("주민",780,400,"villager")]
        if self.area=="왕의 방":data=[("왕",450,225,"king"),("왕국 안",450,610,"exit_palace")]
        for i,e in enumerate(self.enemies):
            if e["alive"]: data.append((e["name"],e["x"],e["y"],"enemy",i))
        return data

    def nearest(self):
        px,py=self.player["x"],self.player["y"]
        near=None; best=70
        for e in self.entities():
            d=math.hypot(px-e[1],py-e[2])
            if d<best: best=d; near=e
        return near

    def move_area(self, dest):
        p=self.player
        royal_areas=("왕실 상점가","왕국 기사단","왕국 안","왕의 방")
        church_areas=("교회 밖","교회 안")
        if p["prayer_due"] and dest not in church_areas+ ("마을",):
            self.exile_church();return
        if p["prayer_due"] and p["area"] in church_areas and dest=="마을":
            self.exile_church();return
        if dest in royal_areas and (p["race"]=="수인" or p["faction"]=="방랑자"):
            self.say("성문 경비가 길을 막는다. 수인과 방랑자 진영은 왕실 구역에 들어갈 수 없다.");p["x"]=max(80,min(MAP_SIZE[self.area][0]-80,p["x"]));return
        if dest in church_areas and p["exiled"]:
            self.say("교회에서 추방된 방랑자는 교회 땅에 들어갈 수 없다.");return
        entry={
            "숲":(2200,800),"마을":(100,500),"교회 밖":(600,790),"교회 안":(480,640),
            "왕실 상점가":(100,450),"왕국 기사단":(500,680),"왕국 안":(500,680),"왕의 방":(450,590)
        }
        p["area"]=dest;p["visited_faction"]=dest;self.area=dest
        p["x"],p["y"]=entry[dest]
        self.spawn_enemies()
        intro={
            "숲":"나무와 바위가 이어지는 넓은 숲. 방랑자 무리가 숲길을 떠돌고, 마물이 배회한다.",
            "마을":"왕실과 교회의 사이에 놓인 마을. 상점과 주민들의 집이 모여 있다.",
            "교회 밖":"교회 앞마당. 성당 안으로 들어가려면 정문에 다가가 E를 눌러라.",
            "교회 안":"촛불이 켜진 성당 안. 성직자와 수련관, 기도 제단이 있다.",
            "왕실 상점가":"왕국의 상점가. 기사단과 왕국 안쪽으로 이어지는 길이 있다.",
            "왕국 기사단":"왕실 기사단의 훈련 구역. 교관에게 전사 직업과 토벌 의뢰를 얻을 수 있다.",
            "왕국 안":"왕국의 중심 구역. 궁성으로 가는 길은 북쪽에 있다.",
            "왕의 방":"왕이 머무는 궁성 안쪽. 왕에게 직접 의뢰를 받을 수 있다."
        }
        if dest in royal_areas and p["race"]=="인간" and p["job"] in ("도둑","도적"):
            self.say("경비가 네 직업을 알아보고 경계한다. 왕국 안의 주민과 상점에서 적대적인 반응을 보일 수 있다.")
        else:self.say(intro[dest])

    def open_dialog(self, title, text, options): self.dialog={"title":title,"text":text,"options":options}
    def interact(self):
        ent=self.nearest()
        if not ent: self.say("주변에 상호작용할 대상이 없어. 사람이나 시설 가까이 가서 E를 눌러봐.");return
        name,x,y,kind,*extra=ent; p=self.player
        transitions={
            "exit_village":"마을","exit_forest":"숲","exit_church":"교회 밖",
            "enter_church":"교회 안","exit_churchyard":"교회 밖",
            "exit_kingdom":"왕실 상점가","exit_barracks":"왕국 기사단",
            "exit_city":"왕국 안","exit_market":"왕실 상점가",
            "exit_throne":"왕의 방","exit_palace":"왕국 안"
        }
        if kind in transitions:self.move_area(transitions[kind]);return
        if kind=="sign":self.say("숲은 넓다. 길을 잃지 않도록 동쪽 끝의 마을 길을 찾아가자.");return
        if kind=="enemy": self.start_battle(extra[0]);return
        if kind=="wanderer_party":
            if p["faction"]=="방랑자":self.open_dialog("방랑자 집단","떠돌이 무리가 숲길을 따라 이동 중이다.",["함께 이동하기","나가기"])
            else:self.open_dialog("방랑자 집단","방랑자 무리가 숲에서 이동하고 있다. 함께하기 위해서는 진영을 바꿔야 한다.",["방랑자 진영에 합류","대화하기","나가기"])
            return
        if kind=="knight_hunters":
            self.open_dialog("기사단 추격대","왕실에서 방랑 기사를 추격해왔다. 싸우거나 기사단으로 돌아갈 수 있다.",["기사단과 싸운다","기사단에 다시 들어간다"]);return
        if kind=="shop":
            price=20 if p["race"]=="인간" else 21
            weapon_price=60 if p["race"]=="인간" else 63
            armor_price=55 if p["race"]=="인간" else 58
            last="물건 훔치기" if p["job"]=="도둑" else "나가기"
            self.open_dialog("상점",f"회복 붕대는 최대 체력의 12%를 회복해. 수인 가격 +5%. 현재 {p['gold']}G.",[f"회복 붕대 구매 · {price}G",f"철검 구매 · {weapon_price}G",f"갑옷 구매 · {armor_price}G",last]);return
        if kind=="camp":
            if p["faction"]!="방랑자": self.open_dialog("방랑자 야영지","방랑자와 함께하거나, 이 진영을 떠나 다른 길을 찾을 수 있다.",["방랑자 진영에 합류","도둑 직업 얻기","다른 진영으로 떠나기"])
            elif p["job"]!="도둑": self.open_dialog("방랑자 야영지","숲의 방랑자들은 왕실을 피해 떠돌아. 도둑의 길을 배울 수 있다.",["도둑 직업 얻기","마을로 향하기","방랑자 진영에서 탈퇴"])
            else:self.open_dialog("방랑자 야영지","야영지에서 잠시 숨을 돌린다.",["마을로 향하기","방랑자 진영에서 탈퇴"])
            return
        if kind=="trainer_church":
            if p["prayer_due"]:self.open_dialog("교회 수련관","완료한 의뢰에 대한 기도를 먼저 마쳐야 한다.",["나가기"])
            else:self.open_dialog("교회 수련관",f"교회 직업은 전사와 신자야. 현재 직업 {p['job']} · 기도 {p['prayer_count']}/10. 다른 진영에서 왔다면 교회 직업을 새로 선택할 수 있어.",["전사로 수련 시작","신자로 수련 시작","다른 진영을 찾아 떠나기"])
            return
        if kind=="priest":
            if p["faction"]!="교회":self.open_dialog("성직자","교회 진영에 속한 직업만 교회 스토리 의뢰를 받을 수 있다. 교회 수련관에서 합류할 수 있다.",["나가기"])
            elif p["job"]=="신자":
                prayer_option="기도 의뢰" if p["prayer_count"]<p["church_quests_completed"] else "나가기"
                self.open_dialog("성직자","교회 일을 도와주게. 완료한 성직자 의뢰 횟수만큼 기도할 수 있다. 세 번 이상 거절하면 직업 승급 자격을 잃는다.",["밭에 물 주기 의뢰","교회 청소 의뢰",prayer_option,"의뢰 거절"])
            elif p["job"]=="전사":self.open_dialog("성직자","숲에서 마물을 퇴치해주게. 성공하면 반드시 제단에서 기도해야 하네.",["마물 퇴치 의뢰","의뢰 거절","나가기"])
            else:self.open_dialog("성직자","교회 직업을 얻으려면 수련관에서 수련해야 하네. 다른 진영 직업으로는 교회 스토리 의뢰를 받을 수 없어.",["나가기"])
            return
        if kind=="altar":
            if p["prayer_count"]>=p["church_quests_completed"]:
                self.say(f"기도할 수 있는 횟수가 부족하다. 성직자 의뢰 완료 {p['church_quests_completed']}회 / 기도 {p['prayer_count']}회.");return
            p["prayer_count"]+=1
            if p["prayer_due"]: p["prayer_due"]=False;self.say(f"기도를 마쳤다. 성전사 승급을 향한 기도 {p['prayer_count']}/10.")
            else:self.say(f"조용히 기도했다. 기도 횟수 {p['prayer_count']}/10.")
            if p["job"]=="전사" and p["prayer_count"]>=10 and p["priest_refusals"]<3 and not p["promoted"]:self.promote("성전사")
            if p["quest"] and p["quest"]["title"]=="기도":self.complete_simple_quest("기도")
            return
        if kind=="field": self.complete_simple_quest("밭에 물 주기");return
        if kind=="cleaning": self.complete_simple_quest("교회 청소");return
        if kind=="villager":
            if p["job"] in ("전사","기사"):
                self.open_dialog("마을 주민","숲에서 마물이 내려와 가축과 주민을 위협하고 있어.",["마물 퇴치 의뢰","의뢰 거절","나가기"])
            else:self.open_dialog("마을 주민","수인 여행자에게는 경계하는 눈빛을 보낸다. 숲에 사는 이들에게는 친절하다.",["마물 퇴치 의뢰","의뢰 거절","나가기"])
            return
        if kind=="trainer_kingdom":
            if p["faction"]=="왕실" and p["job"]=="미정":self.open_dialog("왕실 교관","왕실 도시에서 전쟁에 참여할 전사를 모집한다.",["전사로 수련 시작","왕실 토벌 의뢰","방랑자로 탈출하기"])
            elif p["faction"]=="왕실":self.open_dialog("왕실 교관",f"왕실 직업은 전사에서 시작해 기사로 승급해. 현재 직업 {p['job']} · 왕실 의뢰 {p['king_quests']}/10.",["왕실 토벌 의뢰","승급 진행도 확인","방랑자로 탈출하기"])
            else:self.open_dialog("왕실 교관","왕실 직업은 전사로 합류해 시작한다. 방랑자 진영 소속은 왕실에 들어올 수 없다.",["전사로 수련 시작","나가기"])
            return
        if kind=="king":
            if p["faction"]=="왕실":self.open_dialog("왕","전쟁은 끝날 기미가 없다. 왕실의 이름으로 숲과 방랑자의 문제를 해결하라.",["마물 퇴치 의뢰","나가기"])
            else:self.open_dialog("왕","왕실 소속이 아닌 자는 왕의 명령을 받을 수 없다.",["나가기"])
            return

    def accept_quest(self, title, source):
        self.player["quest"]={"title":title,"source":source,"goal":1,"count":0}
        self.player["quest_kills"]=0
        self.say(f"의뢰 수락: {title}. 숲의 마물을 처치하고 돌아오자.")

    def complete_simple_quest(self,title):
        p=self.player
        if not p["quest"]: self.say("먼저 성직자에게 의뢰를 받아야 해.");return
        if p["quest"].get("source")!="church_simple":self.say("이 의뢰는 여기서 완료할 수 없어.");return
        if p["quest"]["title"]!=title:self.say("이곳에서 완료할 수 있는 의뢰가 아니야.");return
        source=p["quest"]["source"]
        p["quest"]=None;p["gold"]+=12;self.gain_xp(8)
        self.say(f"{title} 완료! 12G와 경험치를 얻었다.")
        self.after_church_quest(source)

    def after_church_quest(self, source=None):
        p=self.player
        if p["faction"]=="교회" and source in ("church","church_simple"):
            p["church_quests_completed"]+=1
        if p["faction"]=="교회" and p["job"]=="전사" and source=="church":
            p["prayer_due"]=True
            self.open_dialog("기도 의무","의뢰를 완료했다. 교회 안의 제단에서 기도해야 한다. 기도하지 않고 교회 진영을 떠나면 방랑자로 추방된다.",["알겠어"])
        if p["faction"]=="왕실" and p["job"] in ("전사","기사") and source=="kingdom":
            p["king_quests"]+=1
            if p["king_quests"]>=10 and p["job"]=="전사":self.promote("기사")

    def complete_monster_quest(self):
        p=self.player; q=p["quest"]
        if not q: return
        source=q.get("source")
        p["quest"]=None;p["gold"]+=25;self.gain_xp(20)
        self.say("마물 퇴치 의뢰 완료! 25G와 경험치를 얻었다.")
        self.after_church_quest(source)

    def promote(self, job):
        p=self.player;p["job"]=job;p["promoted"]=True
        self.open_dialog("직업 승급",f"새로운 직업을 얻었다: {job}. 1장의 이야기를 마쳤다.",["1장 마무리"])

    def choose(self, idx):
        if not self.dialog:return
        d=self.dialog;p=self.player
        if idx<0 or idx>=len(d["options"]):return
        self.dialog=None
        title=d["title"]; opt=d["options"][idx]
        if "enemy_index" in d and title not in ("직업 승급",):
            if idx==0:
                i=d["enemy_index"]
                if i<len(self.enemies) and self.enemies[i]["alive"]: self.start_battle(i)
            else:self.say("전투를 피했다.")
            return
        if title=="상점":
            bandage_price=20 if p["race"]=="인간" else 21
            weapon_price=60 if p["race"]=="인간" else 63
            armor_price=55 if p["race"]=="인간" else 58
            if idx==0:
                if p["gold"]>=bandage_price:p["gold"]-=bandage_price;p["bandages"]+=1;p["inventory"].append("회복 붕대");self.say("회복 붕대를 샀다.")
                else:self.say("소지금이 부족하다.")
            elif idx==1:
                if p["gold"]>=weapon_price:p["gold"]-=weapon_price;p["weapon"]="철검";p["atk"]+=5;self.say("철검을 장착했다. 공격력이 5 올랐다.")
                else:self.say("소지금이 부족하다.")
            elif idx==2:
                if p["gold"]>=armor_price:p["gold"]-=armor_price;p["armor"]="가죽 갑옷";p["def"]+=3;self.say("가죽 갑옷을 장착했다. 방어력이 3 올랐다.")
                else:self.say("소지금이 부족하다.")
            elif idx==3 and opt=="물건 훔치기":
                if random.random()<.55:
                    self.enemies.append({"name":"상점 주인","x":280,"y":300,"hp":48,"maxhp":48,"atk":8,"level":1,"alive":True,"human":True})
                    self.open_dialog("발각!","물건을 훔치다 들켰다. 상점 주인이 길을 막는다.",["맞서 싸운다","도망친다"]);self.dialog["enemy_index"]=len(self.enemies)-1
                else:
                    p["gold"]+=25;p["inventory"].append("훔친 물건");self.say("들키지 않고 물건을 훔쳤다. 25G 상당의 물건을 챙겼다.")
            return
        if title=="소지품":
            if opt=="회복 붕대 사용":
                if p["bandages"]>0:
                    healed=max(1,round(p["maxhp"]*.12));p["hp"]=min(p["maxhp"],p["hp"]+healed);p["bandages"]-=1;self.say(f"회복 붕대를 사용해 HP {healed} 회복.")
                else:self.say("회복 붕대가 없어.")
            return
        if title=="방랑자 야영지":
            if opt=="방랑자 진영에 합류":p["faction"]="방랑자";self.say("방랑자 진영에 합류했다. 왕실 구역에는 들어갈 수 없다.")
            elif opt=="도둑 직업 얻기":p["job"]="도둑";p["faction"]="방랑자";self.say("도둑의 길을 택했다. 사람을 죽이면 도적으로 승급할 수 있다.")
            elif opt=="마을로 향하기":self.move_area("마을")
            elif opt=="다른 진영으로 떠나기" or opt=="방랑자 진영에서 탈퇴":p["faction"]="무소속";self.say("방랑자 진영을 떠나 무소속이 되었다. 인간이라면 왕실에도 들어갈 수 있다.")
            return
        if title=="기사단 추격대":
            if idx==0:
                self.enemies.append({"name":"기사단 추격자","x":560,"y":340,"hp":56,"maxhp":56,"atk":10,"level":2,"alive":True,"human":True})
                self.open_dialog("추격전","기사단 추격자가 검을 뽑았다.",["맞서 싸운다","도망친다"]);self.dialog["enemy_index"]=len(self.enemies)-1
            elif idx==1:
                p["faction"]="왕실";self.move_area("왕국 기사단");self.say("기사단에 다시 들어갔다. 왕실 진영으로 돌아왔다.")
            return
        if title=="방랑자 집단":
            if opt in ("방랑자 진영에 합류","함께 이동하기"):
                p["faction"]="방랑자";self.say("방랑자 무리와 함께 숲길을 걷는다. 왕실 구역에 들어갈 수 없게 되었다.")
            elif opt=="대화하기":self.say("방랑자들이 왕실과 교회의 전쟁 소문을 나눈다.")
            return
        if title=="교회 수련관":
            if opt=="전사로 수련 시작":p["job"]="전사";p["faction"]="교회";self.say("교회 전사가 되었다. 의뢰를 성공할 때마다 제단에서 기도하자.")
            elif opt=="신자로 수련 시작":p["job"]="신자";p["faction"]="교회";self.say("교회 신자가 되었다. 성직자에게 교회 일을 받자.")
            elif opt=="교회에서 나가기":self.exile_church()
            elif opt=="다른 진영을 찾아 떠나기":p["faction"]="무소속";self.move_area("마을")
            elif opt=="기도 횟수 확인":self.say(f"현재 기도 횟수 {p['prayer_count']}/10. 교회 퀘스트 거절 {p['priest_refusals']}회.")
            return
        if title=="성직자":
            if opt=="의뢰 거절":
                p["priest_refusals"]+=1
                if p["priest_refusals"]>=3:self.say("의뢰를 세 번 이상 거절했다. 교회 직업의 승급 자격을 잃었다.")
                else:self.say(f"의뢰를 거절했다. 거절 {p['priest_refusals']}/3.")
            elif opt=="마물 퇴치 의뢰":self.accept_quest("숲의 마물 퇴치","church")
            elif opt=="밭에 물 주기 의뢰" or opt=="교회 청소 의뢰" or opt=="기도 의뢰":self.accept_quest(opt.replace(" 의뢰",""),"church_simple")
            return
        if title=="마을 주민":
            if opt=="의뢰 거절":self.say("의뢰를 거절했다.")
            elif opt=="마물 퇴치 의뢰":self.accept_quest("숲의 마물 퇴치","village")
            return
        if title=="왕실 교관" or title=="왕":
            if opt=="전사로 수련 시작":p["job"]="전사";p["faction"]="왕실";self.say("왕실 전사가 되었다. 왕실 의뢰를 수행해 기사단에 입대할 수 있다.")
            elif opt=="왕실 토벌 의뢰" or opt=="마물 퇴치 의뢰":self.accept_quest("왕실 토벌","kingdom")
            elif opt=="승급 진행도 확인":self.say(f"왕실 의뢰 {p['king_quests']}/10. 전사로 왕실 의뢰를 10번 완료하면 기사가 된다.")
            elif opt=="방랑자로 탈출하기":p["faction"]="무소속";self.move_area("마을");self.say("왕실을 탈출했다. 이제 무소속으로 다른 진영에 들어갈 수 있다.")
            elif opt=="의뢰 거절":self.say("왕실 의뢰를 거절했다.")
            return
        if title=="기도 의무":
            if idx==0:self.say("교회 안의 제단으로 돌아가 기도하자.")
            return
        if title=="직업 승급": self.say("1장 완료. 이후 파트는 추후 추가 예정.");return
        if title=="교회 수련관" and opt=="교회에서 나가기":self.exile_church()

    def exile_church(self):
        p=self.player;p["faction"]="방랑자";p["exiled"]=True
        self.area="마을";p["area"]="마을";p["x"]=700;p["y"]=500;p["visited_faction"]="마을";self.spawn_enemies()
        self.say("교회에서 추방되었다. 방랑자 진영으로 편입되어 교회에 다시 들어갈 수 없다.")

    def start_battle(self, idx):
        e=self.enemies[idx];self.battle={"index":idx,"enemy_turn":True,"log":f"{e['name']}와 마주쳤다!","defending":False,"turn":0,"effect":None}
        self.mode="battle"

    def start_ambush(self):
        name=random.choice(["멧돼지","늑대","고블린"])
        enemy={"name":name,"x":self.player["x"]+45,"y":self.player["y"],"hp":random.choice([28,36,44]),"maxhp":44,"atk":random.randint(6,10),"level":random.choice([1,1,2]),"alive":True,"vx":0,"vy":0}
        self.enemies.append(enemy)
        self.say(f"숲의 {name}가 갑자기 습격했다!",3)
        self.start_battle(len(self.enemies)-1)

    def update_world_ai(self, dt, distance):
        if self.area!="숲":return
        for g in self.wanderers:
            g["turn"]-=dt
            if g["turn"]<=0:
                g["vx"]=random.uniform(-42,42);g["vy"]=random.uniform(-28,28);g["turn"]=random.uniform(1.5,4)
            g["x"]=max(95,min(2300,g["x"]+g["vx"]*dt));g["y"]=max(100,min(1500,g["y"]+g["vy"]*dt))
        for e in self.enemies:
            if not e.get("alive") or e.get("human"):continue
            e["turn"]-=dt
            if e["turn"]<=0:
                e["vx"]=random.uniform(-25,25);e["vy"]=random.uniform(-20,20);e["turn"]=random.uniform(1.2,3.5)
            e["x"]=max(100,min(2300,e["x"]+e["vx"]*dt));e["y"]=max(100,min(1500,e["y"]+e["vy"]*dt))
        if distance>0:
            self.walk_meter+=distance
            while self.walk_meter>=190:
                self.walk_meter-=190
                if random.random()<.12:
                    self.start_ambush();break

    def battle_action(self, action):
        if not hasattr(self,"battle"):return
        b=self.battle;p=self.player;e=self.enemies[b["index"]]
        if action=="attack":
            b["submenu"]="attack";b["log"]="사용할 공격 기술을 선택해."
            return
        if action=="basic":
            dmg=max(1,p["atk"]+random.randint(-2,3));e["hp"]-=dmg;b["log"]=f"{p['weapon']}으로 공격! {dmg} 피해."
            b["effect"]="slash";b["effect_t"]=.42;b["submenu"]=None
        elif action=="skill":
            cost=7
            if p["mp"]<cost:b["log"]="MP가 부족하다."
            else:
                p["mp"]-=cost;dmg=max(2,p["atk"]*2+random.randint(-2,4));e["hp"]-=dmg;b["log"]=f"강타! {dmg} 피해. MP -{cost}."
                b["effect"]="skill";b["effect_t"]=.5
            b["submenu"]=None
        elif action=="defend":b["defending"]=True;b["log"]="방어 자세를 취했다. 이번 적의 공격은 무효가 된다.";b["effect"]="shield";b["effect_t"]=.4
        elif action=="item":
            if p["bandages"]>0:
                healed=max(1,round(p["maxhp"]*.12));p["hp"]=min(p["maxhp"],p["hp"]+healed);p["bandages"]-=1;b["log"]=f"회복 붕대를 사용해 HP {healed} 회복."
            else:b["log"]="회복 붕대가 없다. 마을 상점에서 구매할 수 있다."
            return
        elif action=="flee":
            chance=max(.1,min(.9,.5+(p["level"]-e["level"])*.15))
            if random.random()<chance:
                b["log"]="도주에 성공했다.";self.mode="world";del self.battle;return
            b["log"]="도주에 실패했다!";b["effect"]="miss";b["effect_t"]=.25;b["submenu"]=None
        if e["hp"]<=0:
            e["alive"]=False;self.mode="world";del self.battle
            self.gain_xp(12);p["gold"]+=random.randint(8,16)
            if p["quest"] and p["quest"]["source"] in ("church","village","kingdom"):
                self.complete_monster_quest()
            if e.get("human") and p["job"]=="도둑":
                self.promote("도적");return
            self.say(f"{e['name']} 처치! 경험치와 골드를 얻었다.");return
        self.enemy_turn()

    def enemy_turn(self):
        b=self.battle;p=self.player;e=self.enemies[b["index"]]
        if b["defending"]:
            b["defending"]=False;b["log"]+=" 적의 공격을 완전히 막았다.";b["effect"]="shield";b["effect_t"]=.4
        else:
            dmg=max(1,e["atk"]-p["def"]+random.randint(-1,2));p["hp"]-=dmg;b["log"]+=f" {e['name']}의 반격! {dmg} 피해.";b["counter_t"]=.35
        if p["hp"]<=0:
            p["hp"]=p["maxhp"];p["gold"]//=2
            self.area=p["visited_faction"] if p["visited_faction"] in AREAS else "숲"
            p["area"]=self.area; p["x"]=480;p["y"]=340
            self.mode="world";del self.battle
            self.say(f"쓰러졌다. 마지막으로 방문한 진영({p['visited_faction']})에서 눈을 떴다. 보유금 절반을 잃었다.",7)

    def handle_dialog_input(self, presses, click):
        if click:
            x,y=click
            for i in range(4):
                if 300+i*43 <= y <= 335+i*43: self.choose(i);return
        for k in presses:
            if k in ("Escape","e","E"):self.dialog=None;return
            if k in ("1","2","3","4"):self.choose(int(k)-1);return

    def tick(self, dt, held_json, press_json, click_json):
        try:
            held=set(json.loads(held_json)); presses=json.loads(press_json); click=json.loads(click_json) if click_json else None
        except Exception: held=set();presses=[];click=None
        if not self.started:return
        self.tick_n+=1
        if self.notice_t>0:self.notice_t-=dt
        if self.dialog:
            self.handle_dialog_input(presses,click);self.draw();return
        if getattr(self,"mode","world")=="battle":
            b=self.battle
            b["effect_t"]=max(0,b.get("effect_t",0)-dt);b["counter_t"]=max(0,b.get("counter_t",0)-dt)
            if click:
                x,y=click
                if b.get("submenu")=="attack" and 390<=y<=445:
                    if x<410:self.battle_action("basic")
                    elif x<620:self.battle_action("skill")
                    else:b["submenu"]=None
                elif 475<=y<=532:
                    if x<310:self.battle_action("attack")
                    elif x<490:self.battle_action("defend")
                    elif x<670:self.battle_action("flee")
                    else:self.battle_action("item")
            for k in presses:
                if b.get("submenu")=="attack":
                    if k=="1":self.battle_action("basic")
                    elif k=="2":self.battle_action("skill")
                    elif k in ("3","Escape"):b["submenu"]=None
                    break
                acts={"1":"attack","2":"defend","3":"flee","4":"item","h":"item"}
                if k in acts:self.battle_action(acts[k]);break
            self.draw();return
        p=self.player
        if any(k in presses for k in ("e","E","Enter")) and self.notice_t>0:
            self.notice_t=0;self.draw();return
        speed=220*min(dt,.05); dx=dy=0
        if any(k in held for k in ("ArrowLeft","a","A")):dx-=speed
        if any(k in held for k in ("ArrowRight","d","D")):dx+=speed
        if any(k in held for k in ("ArrowUp","w","W")):dy-=speed
        if any(k in held for k in ("ArrowDown","s","S")):dy+=speed
        if dx and dy:dx*=.707;dy*=.707
        mapw,maph=MAP_SIZE[self.area]
        p["x"]=max(32,min(mapw-32,p["x"]+dx));p["y"]=max(80,min(maph-32,p["y"]+dy))
        self.update_world_ai(dt,math.hypot(dx,dy))
        if self.mode=="battle":self.draw();return
        for k in presses:
            if k in ("e","E","Enter"):self.interact()
            elif k in ("i","I"):self.open_dialog("소지품",f"무기: {p['weapon']}\n방어구: {p['armor']}\n회복 붕대: {p['bandages']}개\n골드: {p['gold']}G",["회복 붕대 사용","닫기"])
            elif k in ("q","Q"):
                q=p["quest"]
                self.open_dialog("퀘스트 기록",f"진영: {p['faction']} · 직업: {p['job']}\n의뢰: {q['title'] if q else '없음'}\n교회 의뢰 거절: {p['priest_refusals']}/3\n기도 가능/완료: {p['church_quests_completed']}/{p['prayer_count']} (성전사 10회)\n왕실 의뢰: {p['king_quests']}/10",["닫기"])
            elif k in ("h","H"):
                healed=max(1,round(p["maxhp"]*.12))
                if p["bandages"]:p["bandages"]-=1;p["hp"]=min(p["maxhp"],p["hp"]+healed);self.say(f"회복 붕대 사용: HP {healed} 회복.")
                else:self.say("회복 붕대가 없어.")
        self.draw()

    def rect(self,x,y,w,h,fill,outline=None):return {"t":"r","x":x,"y":y,"w":w,"h":h,"c":fill,"o":outline}
    def circle(self,x,y,r,fill,outline=None):return {"t":"c","x":x,"y":y,"r":r,"c":fill,"o":outline}
    def oval(self,x,y,w,h,fill,outline=None):return {"t":"o","x":x,"y":y,"w":w,"h":h,"c":fill,"o":outline}
    def line(self,x1,y1,x2,y2,color,width=2):return {"t":"l","x1":x1,"y1":y1,"x2":x2,"y2":y2,"c":color,"w":width}
    def polygon(self,points,fill,outline=None):return {"t":"p","pts":points,"c":fill,"o":outline}
    def text(self,x,y,s,size=16,color="#f6eddb",align="left"):return {"t":"t","x":x,"y":y,"s":str(s),"size":size,"c":color,"a":align}

    def draw_character(self,out,x,y,name,job="주민",race="인간",faction="마을",scale=1.0):
        s=scale
        palettes={"교회":("#d8d8cd","#566782","#cfb66d"),"왕실":("#9a4e47","#ddd2b6","#d9b96d"),"방랑자":("#594a3c","#292b31","#a9784f"),"마을":("#6d7651","#9b7558","#d1b27c")}
        coat,trim,metal=palettes.get(faction,palettes["마을"])
        if job in ("성직자","교황","성인"):coat,trim,metal="#e1ddcd","#536183","#e7cf84"
        if job in ("기사","기사단장","전사"):coat,trim,metal="#77808b","#d7d0c1","#c9aa67"
        if job in ("도둑","도적","암살자"):coat,trim,metal="#35343e","#514553","#a87855"
        skin="#dfb999" if race=="인간" else "#d5a982"
        hair="#382b2a" if race=="인간" else "#593d35"
        # ground shadow, boots, cloak, tunic, arms, head and hair
        out.append(self.oval(x-15*s,y+10*s,30*s,8*s,"#10171288"))
        out.append(self.rect(x-9*s,y+6*s,6*s,9*s,"#342b2a"));out.append(self.rect(x+3*s,y+6*s,6*s,9*s,"#342b2a"))
        out.append(self.polygon([x-9*s,y-7*s,x+9*s,y-7*s,x+13*s,y+8*s,x+8*s,y+14*s,x-8*s,y+14*s,x-13*s,y+8*s],coat,"#24252a"))
        out.append(self.rect(x-7*s,y-2*s,14*s,13*s,trim))
        out.append(self.rect(x-14*s,y-5*s,6*s,12*s,coat));out.append(self.rect(x+8*s,y-5*s,6*s,12*s,coat))
        out.append(self.circle(x,y-13*s,8*s,skin,"#473732"));out.append(self.oval(x-8*s,y-21*s,16*s,10*s,hair))
        if race=="수인":
            out.append(self.polygon([x-6*s,y-18*s,x-13*s,y-29*s,x-1*s,y-22*s],hair));out.append(self.polygon([x+6*s,y-18*s,x+13*s,y-29*s,x+1*s,y-22*s],hair))
            out.append(self.line(x+10*s,y+4*s,x+17*s,y+12*s,hair,3*s))
        else:out.append(self.oval(x-7*s,y-20*s,14*s,7*s,hair))
        out.append(self.circle(x-3*s,y-13*s,1.3*s,"#292323"));out.append(self.circle(x+3*s,y-13*s,1.3*s,"#292323"))
        if job in ("성직자","교황","성인"):out.append(self.line(x,y-4*s,x,y+5*s,metal,2*s));out.append(self.line(x-3*s,y,x+3*s,y,metal,2*s))
        if job in ("전사","기사","기사단장","도둑","도적","암살자"):
            out.append(self.line(x+13*s,y+4*s,x+20*s,y-11*s,metal,2*s));out.append(self.line(x+10*s,y+6*s,x+16*s,y+9*s,"#49352b",3*s))
        if job in ("왕","군주"):out.append(self.polygon([x-7*s,y-19*s,x-6*s,y-27*s,x-2*s,y-22*s,x+2*s,y-28*s,x+5*s,y-21*s,x+8*s,y-25*s,x+8*s,y-18*s],"#d2ad55"))
        out.append(self.text(x,y+27*s,name,11*s,"#fff3d9","center"))

    def draw_monster(self,out,x,y,name,scale=1.0):
        s=scale
        if name=="멧돼지":
            out.append(self.oval(x-25*s,y-13*s,48*s,27*s,"#805238","#382c27"));out.append(self.circle(x+18*s,y-2*s,13*s,"#946447"));out.append(self.circle(x+22*s,y-4*s,2*s,"#ffdf94"));out.append(self.polygon([x+15*s,y+8*s,x+19*s,y+16*s,x+24*s,y+7*s],"#e7d7b6"))
        elif name=="늑대":
            out.append(self.oval(x-28*s,y-11*s,52*s,22*s,"#72777a","#30373b"));out.append(self.polygon([x+13*s,y-8*s,x+31*s,y-4*s,x+22*s,y+8*s],"#8c9190"));out.append(self.polygon([x+13*s,y-11*s,x+12*s,y-25*s,x+23*s,y-14*s],"#555c60"));out.append(self.polygon([x+22*s,y-10*s,x+30*s,y-22*s,x+31*s,y-7*s],"#555c60"));out.append(self.circle(x+23*s,y-5*s,2*s,"#f1d578"))
        else:
            out.append(self.oval(x-17*s,y-10*s,34*s,26*s,"#5d9852","#253c29"));out.append(self.circle(x,y-16*s,11*s,"#75a95d"));out.append(self.polygon([x-7*s,y-22*s,x-17*s,y-32*s,x-11*s,y-15*s],"#54854b"));out.append(self.polygon([x+7*s,y-22*s,x+17*s,y-32*s,x+11*s,y-15*s],"#54854b"));out.append(self.circle(x-4*s,y-17*s,1.5*s,"#2d211b"));out.append(self.circle(x+4*s,y-17*s,1.5*s,"#2d211b"))

    def draw(self):
        if not self.started:return
        p=self.player;out=[];top,bottom=AREAS[self.area];mapw,maph=MAP_SIZE[self.area]
        camx=max(0,min(mapw-W,p["x"]-W/2));camy=max(0,min(maph-H,p["y"]-H/2))
        def sx(x):return x-camx
        def sy(y):return y-camy
        out.append(self.rect(0,0,W,H,top))
        gx=int(camx//80)*80;gy=int(camy//80)*80
        for wy in range(gy,gy+H+100,80):
            for wx in range(gx,gx+W+100,80):
                ix,iy=int(wx//80),int(wy//80)
                shade=(ix*7+iy*11)%3
                if self.area=="숲":
                    out.append(self.rect(sx(wx),sy(wy),79,79,("#294633","#304e38","#35563b")[shade]))
                    if (ix*13+iy*7)%4==0:
                        tx,ty=sx(wx+40),sy(wy+38);out.append(self.rect(tx-5,ty+3,10,22,"#553f2d"));out.append(self.circle(tx,ty,23,"#1c382c"));out.append(self.circle(tx-5,ty-5,15,"#426d42"))
                elif self.area=="마을":out.append(self.rect(sx(wx),sy(wy),79,79,("#765d43","#806849","#826b4b")[shade]))
                elif self.area=="교회 안":out.append(self.rect(sx(wx),sy(wy),79,79,("#72747a","#7b7d83","#858187")[shade]))
                else:out.append(self.rect(sx(wx),sy(wy),79,79,("#594b46","#625249","#6a584a")[shade]))
        # Distinct landmarks by zone
        if self.area=="숲":
            out.append(self.rect(sx(140),sy(730),2100,76,"#8a7651"))
            out.append(self.rect(sx(1390),sy(430),65,650,"#81704e"))
            for x,y in [(360,390),(760,1160),(1250,300),(1710,1270),(2060,550),(1900,1050)]:
                out.append(self.rect(sx(x)-6,sy(y)+8,12,30,"#51402e"));out.append(self.circle(sx(x),sy(y),32,"#183329"));out.append(self.circle(sx(x)-8,sy(y)-8,22,"#3b6840"))
        elif self.area=="마을":
            for x,y,c in [(240,230,"#8b6646"),(550,215,"#725a6d"),(970,235,"#775f4b"),(1090,700,"#705341"),(350,720,"#806349")]:
                X,Y=sx(x),sy(y);out.append(self.rect(X-60,Y-18,120,82,c));out.append(self.rect(X-17,Y+20,34,45,"#342b31"));out.append(self.polygon([X-68,Y-18,X,Y-72,X+68,Y-18],"#b76f51"))
        elif self.area=="교회 밖":
            X,Y=sx(600),sy(300);out.append(self.rect(X-170,Y-45,340,150,"#85858a"));out.append(self.polygon([X-195,Y-45,X,Y-155,X+195,Y-45],"#777b87"));out.append(self.rect(X-50,Y-220,100,180,"#a19b8d"));out.append(self.polygon([X-60,Y-220,X,Y-290,X+60,Y-220],"#72798b"));out.append(self.rect(sx(130),sy(630),180,95,"#6e624e"))
        elif self.area=="교회 안":
            out.append(self.rect(sx(440),sy(95),80,510,"#873d49"));out.append(self.rect(sx(240),sy(130),55,270,"#594d4a"));out.append(self.rect(sx(665),sy(130),55,270,"#594d4a"))
            for y in (280,350,420):out.append(self.rect(sx(270),sy(y),150,14,"#674c42"));out.append(self.rect(sx(540),sy(y),150,14,"#674c42"))
            out.append(self.rect(sx(410),sy(95),140,42,"#d0b678"))
        elif self.area=="왕실 상점가":
            for x,y,c in [(260,230,"#805941"),(540,220,"#674b5c"),(850,230,"#76634a"),(960,650,"#735543")]:
                X,Y=sx(x),sy(y);out.append(self.rect(X-75,Y-15,150,100,c));out.append(self.polygon([X-85,Y-15,X,Y-75,X+85,Y-15],"#b47950"));out.append(self.rect(X-35,Y+26,70,12,"#d1b675"))
        elif self.area=="왕국 기사단":
            for x in (240,760):
                out.append(self.rect(sx(x),sy(150),10,380,"#8c7c63"));out.append(self.circle(sx(x),sy(130),18,"#a34c42"))
            for x in (350,500,650):out.append(self.rect(sx(x-30),sy(420),60,20,"#76523e"));out.append(self.rect(sx(x-4),sy(390),8,30,"#c8b178"))
        elif self.area=="왕국 안":
            out.append(self.rect(sx(480),sy(0),40,700,"#b59b68"));out.append(self.rect(sx(0),sy(350),1000,40,"#b59b68"));out.append(self.rect(sx(350),sy(150),300,190,"#89704e"))
        elif self.area=="왕의 방":
            out.append(self.rect(0,0,W,H,"#493740"));out.append(self.rect(sx(360),sy(80),180,560,"#8a3c48"))
            for x in (150,750):out.append(self.rect(sx(x),sy(100),28,470,"#c9b67b"))
        # Zone labels and actors; world coordinates are translated through the camera.
        for ent in self.entities():
            name,x,y,kind,*extra=ent;X,Y=sx(x),sy(y)
            if X < -75 or X > W+75 or Y < 65 or Y > H+40:continue
            if kind=="enemy":
                e=self.enemies[extra[0]]
                if e.get("human"):self.draw_character(out,X,Y,name,"기사","인간","왕실",.9)
                else:self.draw_monster(out,X,Y,name,.78);out.append(self.text(X,Y+31,name,11,"#fff0d4","center"))
            elif kind=="wanderer_party":
                for j in range(extra[0]%3+2):self.draw_character(out,X+(j-(extra[0]%3+1)/2)*26,Y+8,"", "방랑자", "인간", "방랑자",.72)
                out.append(self.text(X,Y+40,name,11,"#fff0d4","center"))
            elif kind in ("exit_village","exit_forest","exit_church","enter_church","exit_churchyard","exit_kingdom","exit_barracks","exit_city","exit_market","exit_throne","exit_palace"):
                out.append(self.circle(X,Y,19,"#d7b971"));out.append(self.text(X,Y,name,11,"#1f2928","center"))
            else:
                role={"priest":"성직자","trainer_church":"전사","trainer_kingdom":"기사","king":"왕","shop":"상인","villager":"주민","camp":"방랑자 집단","field":"신자","cleaning":"신자","altar":"성직자","knight_hunters":"기사"}.get(kind,"주민")
                faction="교회" if kind in ("priest","trainer_church","altar","field","cleaning") else "왕실" if kind in ("trainer_kingdom","king","knight_hunters") else "방랑자" if kind in ("camp","wanderer_party") else "마을"
                race="수인" if kind in ("villager","wanderer_party") and (int(x+y)//80)%3==0 else "인간"
                self.draw_character(out,X,Y,name,role,race,faction,.86)
        self.draw_character(out,sx(p["x"]),sy(p["y"]),p["name"],p["job"],p["race"],p["faction"],1.0)
        out.append(self.rect(0,0,W,67,"#111b24"));out.append(self.text(20,18,"왕실과 교회의 전쟁 · 제1장",18,"#f1d39a"));out.append(self.text(20,45,f"{p['name']} · {p['race']} · {p['gender']} · {p['faction']} / {p['job']}",13))
        out.append(self.text(690,20,f"HP {p['hp']}/{p['maxhp']}   MP {p['mp']}/{p['maxmp']}",14,"#e7e9dc"));out.append(self.text(690,45,f"Lv.{p['level']}   {p['gold']}G   붕대 {p['bandages']}개",13,"#e7e9dc"))
        out.append(self.rect(20,557,920,30,"#111b24dd"));out.append(self.text(32,572,f"{self.area}  ·  WASD/방향키 이동  ·  E 상호작용  ·  Q 퀘스트  ·  I 소지품  ·  H 붕대",13,"#e8ddc8"))
        if self.notice_t>0:
            out.append(self.rect(150,455,660,88,"#101923ef","#d8c08d"))
            for i,line in enumerate(self.notice.split("\n")[:3]):out.append(self.text(170,474+i*22,line[:70],15,"#f2ead9"))
            out.append(self.text(790,532,"E 닫기",11,"#e4c783","right"))
        if getattr(self,"mode","world")=="battle" and hasattr(self,"battle"):
            b=self.battle;e=self.enemies[b["index"]]
            out.append(self.rect(0,67,W,490,"#10151deE"));out.append(self.rect(65,90,830,445,"#252d36","#d7bb7c"));out.append(self.rect(65,90,830,445,"#38404a"))
            out.append(self.text(480,112,"전투",16,"#e8cc8f","center"))
            out.append(self.text(245,150,p["name"],17,"#f5ecd9","center"));out.append(self.text(705,150,e["name"],17,"#f5ecd9","center"))
            out.append(self.rect(145,170,200,13,"#351f25"));out.append(self.rect(145,170,200*max(0,p["hp"])/p["maxhp"],13,"#76ae77"));out.append(self.text(245,194,f"HP {p['hp']}/{p['maxhp']} · MP {p['mp']}/{p['maxmp']}",12,"#e7e3da","center"))
            out.append(self.rect(605,170,200,13,"#351f25"));out.append(self.rect(605,170,200*max(0,e["hp"])/e["maxhp"],13,"#c8564d"));out.append(self.text(705,194,f"HP {max(0,e['hp'])}/{e['maxhp']} · Lv.{e['level']}",12,"#e7e3da","center"))
            self.draw_character(out,285,325,p["name"],p["job"],p["race"],p["faction"],1.85)
            if e.get("human"):self.draw_character(out,675,325,e["name"],"기사" if "기사" in e["name"] else "상인","인간","왕실",1.65)
            else:self.draw_monster(out,675,325,e["name"],1.65)
            if b.get("effect_t",0)>0:
                if b.get("effect")=="slash":out.append(self.line(360,300,590,350,"#fff1c1",13));out.append(self.line(385,285,600,335,"#e9aa55",4))
                elif b.get("effect")=="skill":
                    for i in range(6):out.append(self.circle(515+(i%3)*25,280+(i//3)*60,8,"#ffd56f"))
                    out.append(self.line(360,300,590,350,"#ffe7a2",20))
                elif b.get("effect")=="shield":out.append(self.circle(285,310,61,"#78c7d566","#a4e6e6"))
            if b.get("counter_t",0)>0:out.append(self.line(630,315,365,340,"#e85d50",11))
            out.append(self.text(480,410,b["log"],15,"#fff5df","center"))
            if b.get("submenu")=="attack":
                choices=[("1 기본 공격","#405348"),("2 강타 · MP 7","#67503c"),("3 돌아가기","#454451")]
                for i,(label,c) in enumerate(choices):out.append(self.rect(260+i*150,430,140,40,c,"#a79774"));out.append(self.text(330+i*150,450,label,13,"#fff5df","center"))
            for i,(label,c) in enumerate([("1 공격","#59464a"),("2 방어","#40524e"),("3 도주","#424a5c"),("4 붕대","#685044")]):
                out.append(self.rect(130+i*180,480,165,44,c,"#a79774"));out.append(self.text(212+i*180,502,label,15,"#fff5df","center"))
            out.append(self.text(480,542,"아이템은 턴을 소비하지 않아 · 공격을 고르면 사용할 기술을 선택",12,"#d7d4c9","center"))
        if self.dialog:
            d=self.dialog;out.append(self.rect(115,95,730,420,"#131b26f5","#e2c783"));out.append(self.text(150,125,d["title"],23,"#f2d696"))
            for i,line in enumerate(d["text"].split("\n")[:5]):out.append(self.text(150,167+i*25,line[:78],15,"#e9e5dc"))
            for i,opt in enumerate(d["options"][:4]):out.append(self.rect(145,300+i*43,670,35,"#293747","#748494"));out.append(self.text(160,318+i*43,f"{i+1}. {opt}",15,"#f3eee2"))
            out.append(self.text(150,490,"숫자 키 선택 · E 닫기",12,"#c6bdad"))
        window.gameBridge.draw(json.dumps(out,ensure_ascii=False,separators=(",",":")))

game=Game()
def start_game(name): game.start(str(name))
def tick(dt,held,presses,click): game.tick(float(dt),str(held),str(presses),str(click))
