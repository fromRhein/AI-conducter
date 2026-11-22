import ctypes, ctypes.wintypes as w
u=ctypes.windll.user32
h=0x4A0B1E  # placeholder
def cls(x):
    b=ctypes.create_unicode_buffer(256); u.GetClassNameW(x,b,256); return b.value
def tit(x):
    b=ctypes.create_unicode_buffer(512); u.GetWindowTextW(x,b,512); return b.value
EP=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
found=[]
def cb(x,l):
    if cls(x)=="NINormalWindow0000000140000000":
        found.append(x)
    return True
u.EnumWindows(EP(cb),0)
print("found",[hex(x) for x in found])
for x in found:
    u.SetWindowPos(x,0,40,20,1379,699,0x0040)
    print("moved",hex(x),tit(x))
