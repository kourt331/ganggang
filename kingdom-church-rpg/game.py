"""Chapter 1 prototype: top-down, turn-based fantasy RPG. Runs in Pyodide."""
import json, random, math
from js import window

W, H = 960, 600
AREAS = {
    "숲": ("#243b31", "#35543a"),
    "마을": ("#64513c", "#806647"),
    "교회": ("#394356", "#56617a"),
    "왕실": ("#49394c", "#765343"),
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
        self.tick_n = 0

    def start(self, name):
        race = random.choice(["인간", "수인"])
        gender = random.choice(["남성", "여성"])
        starts = ["숲", "교회", "왕실"] if race == "인간" else ["숲", "교회"]
        area = random.choice(starts)
        faction = {"숲":"방랑자", "교회":"교회", "왕실":"왕실"}[area]
        self.player = {
            "name": (name or "이름 없는 여행자")[:14], "race":race, "gender":gender,
            "area":area,"faction":faction,"job":"미정","x":470,"y":330,
            "hp":100,"maxhp":100,"mp":30,"maxmp":30,"level":1,"xp":0,
            "gold":80,"bandages":1,"weapon":"낡은 검","armor":"여행자 옷",
            "atk":10,"def":3,"quest":None,"quest_kills":0,"priest_refusals":0,
            "prayer_count":0,"prayer_due":False,"king_quests":0,"exiled":False,
            "bandit_unlocked":False,"visited_faction":faction,"promoted":False,
            "inventory":["낡은 검","여행자 옷","회복 붕대 ×1"],"story_flags":[]
        }
        self.player["visited_faction"]=area
        self.area=area; self.enemies=[]; self.dialog=None; self.started=True
        self.notice = self.intro_text(); self.notice_t=9
        self.spawn_enemies()
        self.draw()

    def intro_text(self):
        p=self.player
        lines={"교회":"성직자가 전쟁의 불길이 번진 숲을 바라본다. 교회에서 전사나 신자의 길을 얻을 수 있다. 다른 직업을 원한다면 교회를 벗어나야 한다.",
               "왕실":"왕실의 성문에는 전쟁 동원령이 붙어 있다. 왕의 의뢰를 수행하고 기사단에 들어갈지, 도시를 빠져나갈지 선택해야 한다.",
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
        if self.area=="숲":
            names=["멧돼지","늑대","고블린"]
            for i in range(3): self.enemies.append({"name":random.choice(names),"x":random.randint(160,800),"y":random.randint(130,470),"hp":random.choice([26,34,42]),"maxhp":42,"atk":random.randint(5,9),"level":random.choice([1,1,2]),"alive":True})
        elif self.area=="마을":
            self.enemies=[]
        elif self.area=="왕실" and self.player.get("faction")=="방랑자": self.enemies=[]

    def entities(self):
        data=[]
        if self.area=="숲": data=[("방랑자 야영지",135,180,"camp"),("마을로 가는 길",865,310,"exit_village")]
        if self.area=="마을":
            data=[("상점",210,200,"shop"),("주민",470,205,"villager"),("숲",70,320,"exit_forest"),("교회",875,240,"exit_church"),("왕실",875,420,"exit_kingdom")]
            if self.player.get("job")=="기사" and self.player.get("faction")=="방랑자":data.append(("기사단 추격대",470,430,"knight_hunters"))
        if self.area=="교회": data=[("성직자",720,190,"priest"),("수련관",230,200,"trainer_church"),("기도 제단",480,150,"altar"),("밭",685,390,"field"),("마을",65,320,"exit_village")]
        if self.area=="왕실": data=[("왕실 교관",245,190,"trainer_kingdom"),("왕",720,190,"king"),("상점",720,405,"shop"),("마을",65,320,"exit_village")]
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
        if p["prayer_due"] and dest not in ("교회","마을"):
            self.exile_church();return
        if dest=="왕실" and (p["race"]=="수인" or p["faction"]=="방랑자"):
            self.say("성문 경비가 길을 막는다. 수인과 방랑자는 왕실 구역에 들어갈 수 없다."); p["x"]=790; return
        if dest=="교회" and p["exiled"]:
            self.say("교회에서 추방된 방랑자는 교회 땅에 들어갈 수 없다.");p["x"]=790;return
        p["area"]=dest; p["visited_faction"]=dest
        self.area=dest; p["x"]=80 if dest in ("마을","숲") else 870; p["y"]=320
        self.spawn_enemies()
        intro={"숲":"깊은 숲. 멧돼지와 늑대, 고블린이 길을 막는다.","마을":"왕실과 교회 사이의 작은 마을. 종족과 직업에 따라 주민들의 시선이 달라진다.","교회":"전쟁을 피해 온 사람들이 교회 마당에서 쉰다.","왕실":"왕실 도시. 인간이라도 방랑자 직업이면 경비가 의심스럽게 바라본다."}
        if dest=="왕실" and p["race"]=="인간" and p["job"] in ("도둑","도적"):
            self.say("경비가 네 직업을 알아보고 경계한다. 상점과 왕실 의뢰 이용이 제한될 수 있다.")
        else:self.say(intro[dest])

    def open_dialog(self, title, text, options): self.dialog={"title":title,"text":text,"options":options}
    def interact(self):
        ent=self.nearest()
        if not ent: self.say("주변에 상호작용할 대상이 없어. 사람이나 시설 가까이 가서 E를 눌러봐.");return
        name,x,y,kind,*extra=ent; p=self.player
        if kind.startswith("exit_"):
            dest={"exit_village":"마을","exit_forest":"숲","exit_church":"교회","exit_kingdom":"왕실"}[kind]; self.move_area(dest);return
        if kind=="enemy": self.open_dialog(name,"마물이 길을 막고 있어.",["전투 시작","물러난다"]);self.dialog["enemy_index"]=extra[0];return
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
            self.open_dialog("교회 수련관",f"교회 직업은 전사와 신자야. 현재 직업 {p['job']} · 기도 {p['prayer_count']}/10. 다른 진영에서 왔다면 교회 직업을 새로 선택할 수 있어.",["전사로 수련 시작","신자로 수련 시작","다른 진영을 찾아 떠나기"])
            return
        if kind=="priest":
            if p["faction"]!="교회":self.open_dialog("성직자","교회 진영에 속한 직업만 교회 스토리 의뢰를 받을 수 있다. 교회 수련관에서 합류할 수 있다.",["나가기"])
            elif p["job"]=="신자":self.open_dialog("성직자","교회 일을 도와줄 수 있겠나? 일을 세 번 이상 거절하면 교회 직업의 승급 자격을 잃는다.",["밭에 물 주기 의뢰","교회 청소 의뢰","기도 의뢰","의뢰 거절","나가기"])
            elif p["job"]=="전사":self.open_dialog("성직자","숲에서 마물을 퇴치해주게. 성공하면 반드시 제단에서 기도해야 하네.",["마물 퇴치 의뢰","의뢰 거절","나가기"])
            else:self.open_dialog("성직자","교회 직업을 얻으려면 수련관에서 수련해야 하네. 다른 진영 직업으로는 교회 스토리 의뢰를 받을 수 없어.",["나가기"])
            return
        if kind=="altar":
            p["prayer_count"]+=1
            if p["prayer_due"]: p["prayer_due"]=False;self.say(f"기도를 마쳤다. 성전사 승급을 향한 기도 {p['prayer_count']}/10.")
            else:self.say(f"조용히 기도했다. 기도 횟수 {p['prayer_count']}/10.")
            if p["job"]=="전사" and p["prayer_count"]>=10 and p["priest_refusals"]<3 and not p["promoted"]:self.promote("성전사")
            if p["quest"] and p["quest"]["title"]=="기도":self.complete_simple_quest("기도")
            return
        if kind=="field": self.complete_simple_quest("밭에 물 주기");return
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
        p["quest"]=None;p["gold"]+=12;self.gain_xp(8)
        self.say(f"{title} 완료! 12G와 경험치를 얻었다.")
        self.after_church_quest()

    def after_church_quest(self):
        p=self.player
        if p["faction"]=="교회" and p["job"]=="전사":
            p["prayer_due"]=True
            self.open_dialog("기도 의무","교회 전사는 의뢰를 성공할 때마다 기도해야 한다. 지금 기도하지 않고 교회를 떠나면 추방되어 방랑자 진영으로 바뀐다.",["제단에서 기도하기","나중에 기도하기"])
        if p["faction"]=="왕실" and p["job"] in ("전사","기사"):
            p["king_quests"]+=1
            if p["king_quests"]>=10 and p["job"]=="전사":self.promote("기사")

    def complete_monster_quest(self):
        p=self.player; q=p["quest"]
        if not q: return
        p["quest"]=None;p["gold"]+=25;self.gain_xp(20)
        self.say("마물 퇴치 의뢰 완료! 25G와 경험치를 얻었다.")
        self.after_church_quest()

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
                p["faction"]="왕실";self.move_area("왕실");self.say("기사단에 다시 들어갔다. 왕실 진영으로 돌아왔다.")
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
            elif opt=="방랑자로 탈출하기":p["faction"]="무소속";self.move_area("마을")
            elif opt=="의뢰 거절":self.say("왕실 의뢰를 거절했다.")
            return
        if title=="기도 의무":
            if idx==0:
                self.player["prayer_count"]+=1;self.player["prayer_due"]=False;self.say(f"기도했다. 성전사 승급을 향한 기도 {p['prayer_count']}/10.")
                if p["job"]=="전사" and p["prayer_count"]>=10 and p["priest_refusals"]<3:self.promote("성전사")
            return
        if title=="직업 승급": self.say("1장 완료. 이후 파트는 추후 추가 예정.");return
        if title=="교회 수련관" and opt=="교회에서 나가기":self.exile_church()

    def exile_church(self):
        p=self.player;p["faction"]="방랑자";p["exiled"]=True
        self.area="마을";p["area"]="마을";p["x"]=120;p["y"]=320
        self.say("교회에서 추방되었다. 방랑자 진영으로 편입되어 교회에 다시 들어갈 수 없다.")

    def start_battle(self, idx):
        e=self.enemies[idx];self.battle={"index":idx,"enemy_turn":True,"log":f"{e['name']}와 마주쳤다!","defending":False,"turn":0}
        self.mode="battle"

    def battle_action(self, action):
        if not hasattr(self,"battle"):return
        b=self.battle;p=self.player;e=self.enemies[b["index"]]
        if action=="attack":
            dmg=max(1,p["atk"]+random.randint(-2,3));e["hp"]-=dmg;b["log"]=f"{p['weapon']}으로 공격! {dmg} 피해."
        elif action=="skill":
            cost=7
            if p["mp"]<cost:b["log"]="MP가 부족하다."
            else:
                p["mp"]-=cost;dmg=max(2,p["atk"]*2+random.randint(-2,4));e["hp"]-=dmg;b["log"]=f"강타! {dmg} 피해. MP -{cost}."
        elif action=="defend":b["defending"]=True;b["log"]="방어 자세를 취했다. 이번 적의 공격은 무효가 된다."
        elif action=="item":
            if p["bandages"]>0:
                healed=max(1,round(p["maxhp"]*.12));p["hp"]=min(p["maxhp"],p["hp"]+healed);p["bandages"]-=1;b["log"]=f"회복 붕대를 사용해 HP {healed} 회복."
            else:b["log"]="회복 붕대가 없다. 마을 상점에서 구매할 수 있다."
            return
        elif action=="flee":
            chance=max(.1,min(.9,.5+(p["level"]-e["level"])*.15))
            if random.random()<chance:
                b["log"]="도주에 성공했다.";self.mode="world";del self.battle;return
            b["log"]="도주에 실패했다!"
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
            b["defending"]=False;b["log"]+=" 적의 공격을 완전히 막았다."
        else:
            dmg=max(1,e["atk"]-p["def"]+random.randint(-1,2));p["hp"]-=dmg;b["log"]+=f" {e['name']}의 반격! {dmg} 피해."
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
            if click:
                x,y=click
                if 300<=y<=362:
                    if x<350:self.battle_action("attack")
                    elif x<475:self.battle_action("skill")
                    elif x<600:self.battle_action("defend")
                    else:self.battle_action("flee")
                elif 390<=y<=434:self.battle_action("item")
                elif y>520:self.battle_action("item")
            for k in presses:
                acts={"1":"attack","2":"skill","3":"defend","4":"flee","h":"item"}
                if k in acts:self.battle_action(acts[k]);break
            self.draw();return
        p=self.player
        speed=175*min(dt,.05); dx=dy=0
        if any(k in held for k in ("ArrowLeft","a","A")):dx-=speed
        if any(k in held for k in ("ArrowRight","d","D")):dx+=speed
        if any(k in held for k in ("ArrowUp","w","W")):dy-=speed
        if any(k in held for k in ("ArrowDown","s","S")):dy+=speed
        if dx and dy:dx*=.707;dy*=.707
        p["x"]=max(35,min(925,p["x"]+dx));p["y"]=max(95,min(530,p["y"]+dy))
        for k in presses:
            if k in ("e","E","Enter"):self.interact()
            elif k in ("i","I"):self.open_dialog("소지품",f"무기: {p['weapon']}\n방어구: {p['armor']}\n회복 붕대: {p['bandages']}개\n골드: {p['gold']}G",["회복 붕대 사용","닫기"])
            elif k in ("q","Q"):
                q=p["quest"]
                self.open_dialog("퀘스트 기록",f"진영: {p['faction']} · 직업: {p['job']}\n의뢰: {q['title'] if q else '없음'}\n교회 의뢰 거절: {p['priest_refusals']}/3\n기도: {p['prayer_count']}/10\n왕실 의뢰: {p['king_quests']}/10",["닫기"])
            elif k in ("h","H"):
                healed=max(1,round(p["maxhp"]*.12))
                if p["bandages"]:p["bandages"]-=1;p["hp"]=min(p["maxhp"],p["hp"]+healed);self.say(f"회복 붕대 사용: HP {healed} 회복.")
                else:self.say("회복 붕대가 없어.")
        self.draw()

    def rect(self,x,y,w,h,fill,outline=None):return {"t":"r","x":x,"y":y,"w":w,"h":h,"c":fill,"o":outline}
    def circle(self,x,y,r,fill,outline=None):return {"t":"c","x":x,"y":y,"r":r,"c":fill,"o":outline}
    def text(self,x,y,s,size=16,color="#f6eddb",align="left"):return {"t":"t","x":x,"y":y,"s":str(s),"size":size,"c":color,"a":align}

    def draw(self):
        if not self.started:return
        p=self.player;out=[]; top,bottom=AREAS[self.area]
        out.append(self.rect(0,0,W,H,top))
        # top-down area tiles and paths
        for row in range(0,H,64):
            for col in range((row//64%2)*32,W,64):
                if self.area=="숲":
                    out.append(self.circle(col+18,row+30,17,"#294831"));out.append(self.circle(col+18,row+26,10,"#47724a"))
                elif self.area=="마을":
                    out.append(self.rect(col,row,62,62,"#765d43" if (row//64+col//64)%2 else "#806849"))
                elif self.area=="교회":
                    out.append(self.rect(col,row,62,62,"#49566b" if (row//64+col//64)%2 else "#536079"))
                else:out.append(self.rect(col,row,62,62,"#59434f" if (row//64+col//64)%2 else "#654b4d"))
        out.append(self.rect(0,70,W,480,"#00000000","#ffffff22"))
        # place decorations
        if self.area=="숲":
            for x,y in [(120,100),(815,130),(250,490),(850,480),(550,115)]:out.append(self.circle(x,y,33,"#1d382c"));out.append(self.circle(x,y-12,24,"#3f7043"))
        if self.area=="마을":
            for x,y,col in [(160,130,"#8b6646"),(425,125,"#725a6d"),(720,130,"#775f4b")]:out.append(self.rect(x-45,y-12,90,58,col));out.append(self.rect(x-10,y+14,20,32,"#342b31"));out.append(self.rect(x-53,y-22,106,13,"#be7953"))
        if self.area=="교회":
            out.extend([self.rect(380,95,210,115,"#767b83"),self.rect(445,55,80,110,"#858a90"),self.rect(470,35,30,45,"#c5b887"),self.rect(310,210,350,34,"#7a735f")])
        if self.area=="왕실":
            out.extend([self.rect(320,95,310,130,"#8a6749"),self.rect(385,55,55,75,"#9d7851"),self.rect(505,55,55,75,"#9d7851"),self.rect(435,130,75,95,"#382b33")])
        # entities
        for ent in self.entities():
            name,x,y,kind,*extra=ent
            if kind=="enemy": color="#bc564a" if name!="고블린" else "#72a362"
            elif kind in ("exit_forest","exit_village","exit_church","exit_kingdom"):color="#e5c47e"
            elif kind in ("priest","trainer_church","altar","field","trainer_kingdom","king","shop","villager","camp"):color="#dfbc83" if kind not in ("priest","king") else "#d5d7de"
            else:color="#d3ad83"
            out.append(self.circle(x,y,17,"#171c22"));out.append(self.circle(x,y-2,12,color));out.append(self.text(x,y+22,name,12,"#fff2d8","center"))
        # player token and hud
        out.extend([self.circle(p["x"],p["y"],17,"#10151c"),self.circle(p["x"],p["y"]-3,12,"#72c6d4" if p["race"]=="인간" else "#d68ac7"),self.text(p["x"],p["y"]+24,p["name"],12,"#ffffff","center")])
        out.append(self.rect(0,0,W,67,"#111b24"));out.append(self.text(20,18,"왕실과 교회의 전쟁 · 제1장",18,"#f1d39a"));out.append(self.text(20,45,f"{p['name']} · {p['race']} · {p['gender']} · {p['faction']} / {p['job']}",13))
        out.append(self.text(690,20,f"HP {p['hp']}/{p['maxhp']}   MP {p['mp']}/{p['maxmp']}",14,"#e7e9dc"));out.append(self.text(690,45,f"Lv.{p['level']}   {p['gold']}G   붕대 {p['bandages']}개",13,"#e7e9dc"))
        out.append(self.rect(20,557,920,30,"#111b24dd"));out.append(self.text(32,572,f"{self.area}  ·  WASD/방향키 이동  ·  E 상호작용  ·  Q 퀘스트  ·  I 소지품  ·  H 붕대",13,"#e8ddc8"))
        if self.notice_t>0:
            out.append(self.rect(170,455,620,88,"#101923eF","#d8c08d"));
            for i,line in enumerate(self.notice.split("\n")[:3]):out.append(self.text(190,474+i*22,line[:70],15,"#f2ead9"))
        if getattr(self,"mode","world")=="battle" and hasattr(self,"battle"):
            e=self.enemies[self.battle["index"]]
            out.append(self.rect(210,110,540,360,"#171e2bf2","#e6c782"));out.append(self.text(480,140,e["name"],24,"#f3ddae","center"));out.append(self.text(480,182,f"HP {max(0,e['hp'])}/{e['maxhp']}",16,"#e8e0d5","center"));out.append(self.text(480,230,self.battle["log"],16,"#ffffff","center"))
            for i,(label,key) in enumerate([("공격","1"),("스킬 공격 · MP 7","2"),("방어 · 이번 턴 무적","3"),("도주","4")]):
                x=235+i*125;out.append(self.rect(x,300,112,62,"#39495a","#9c9b84"));out.append(self.text(x+56,327,f"{key} · {label}",13,"#fff5df","center"))
            out.append(self.rect(360,390,240,44,"#665045","#d8c08d"));out.append(self.text(480,412,"H · 회복 붕대 (턴 소모 없음)",14,"#fff5df","center"))
        if self.dialog:
            d=self.dialog;out.append(self.rect(115,95,730,420,"#131b26f5","#e2c783"));out.append(self.text(150,125,d["title"],23,"#f2d696"))
            for i,line in enumerate(d["text"].split("\n")[:5]):out.append(self.text(150,167+i*25,line[:78],15,"#e9e5dc"))
            for i,opt in enumerate(d["options"][:4]):out.append(self.rect(145,300+i*43,670,35,"#293747","#748494"));out.append(self.text(160,318+i*43,f"{i+1}. {opt}",15,"#f3eee2"))
            out.append(self.text(150,490,"숫자 키 선택 · E 닫기",12,"#c6bdad"))
        window.gameBridge.draw(json.dumps(out,ensure_ascii=False,separators=(",",":")))

game=Game()
def start_game(name): game.start(str(name))
def tick(dt,held,presses,click): game.tick(float(dt),str(held),str(presses),str(click))
