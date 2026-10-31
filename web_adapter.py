import sys, types, json, math
from types import SimpleNamespace
try:
    import js
except ImportError:
    js=None
images={}
class PhotoImage:
    def __init__(self,master=None,width=1,height=1,**kw):
        self.id=str(len(images));self.width=width;self.height=height;self.rows=[['' for _ in range(width)] for _ in range(height)];images[self.id]=self
    def put(self,data,to=(0,0)):
        colors=data.strip('{}').split();x,y=to
        for i,c in enumerate(colors):self.rows[y][x+i]=c
    def transparency_set(self,x,y,b):
        if b:self.rows[y][x]=''
class Tk:
    def __init__(self):self.full=False
    def title(self,*a):pass
    def geometry(self,*a):pass
    def minsize(self,*a):pass
    def configure(self,*a,**kw):pass
    def protocol(self,*a):pass
    def after(self,*a):pass
    def mainloop(self):pass
    def destroy(self):pass
    def attributes(self,key,*v):
        if v:
            self.full=v[0]
            if js:js.webFullscreen(bool(v[0]))
        return self.full
class Canvas:
    def __init__(self,*a,**kw):self.items=[];self.serial=0;self.bindings={}
    def pack(self,*a,**kw):pass
    def focus_set(self):pass
    def bind(self,key,fn):self.bindings[key]=fn
    def _create(self,kind,args,options):
        args=list(args)
        if len(args)==1 and isinstance(args[0],(list,tuple)):args=list(args[0])
        options=dict(options)
        if 'image' in options:options['image']=options['image'].id
        self.serial+=1;self.items.append([kind,args,options,self.serial]);return self.serial
    def create_rectangle(self,*a,**k):return self._create('rectangle',a,k)
    def create_line(self,*a,**k):return self._create('line',a,k)
    def create_polygon(self,*a,**k):return self._create('polygon',a,k)
    def create_oval(self,*a,**k):return self._create('oval',a,k)
    def create_arc(self,*a,**k):return self._create('arc',a,k)
    def create_text(self,*a,**k):return self._create('text',a,k)
    def create_image(self,*a,**k):return self._create('image',a,k)
    def _match(self,item,tag):return tag=='all' or item[3]==tag or tag in item[2].get('tags',())
    def delete(self,tag):self.items=[i for i in self.items if not self._match(i,tag)]
    def move(self,tag,dx,dy):
        for i in self.items:
            if self._match(i,tag):i[1]=[v+(dx if j%2==0 else dy) for j,v in enumerate(i[1])]
module=types.ModuleType('tkinter');module.Tk=Tk;module.Canvas=Canvas;module.PhotoImage=PhotoImage;module.TclError=Exception
sys.modules['tkinter']=module

def init_game():
    global game
    import original_game
    game=original_game.PhysicsChronicles(Tk())
    # Only OS audio callbacks are adapted. All battle, drawing and input methods remain original.
    def sync_music():
        if js:js.webMusic(bool(game.music_enabled),float(game.music_volume))
    def toggle_music():game.music_enabled=not game.music_enabled;sync_music()
    game.start_music=sync_music;game.restart_music=sync_music;game.toggle_music=toggle_music
    if js:
        js.loadSprites(json.dumps({k:{'w':v.width,'h':v.height,'rows':v.rows} for k,v in images.items()}))
    game.draw();return game

def web_key(key,down):
    event=SimpleNamespace(keysym=key)
    (game.key_down if down else game.key_up)(event)
    # Menus are rendered even when fixed updates are paused, matching the desktop key handler.

def web_frame(count):
    for _ in range(int(count)):game._fixed_update()
    game.draw()
    if js:
        js.webMusic(bool(game.music_enabled),float(game.music_volume))
        js.renderFrame(json.dumps(game.canvas.items,ensure_ascii=False))
