import ctypes, ctypes.wintypes as w, time
u=ctypes.windll.user32
def cls(x):
    b=ctypes.create_unicode_buffer(256); u.GetClassNameW(x,b,256); return b.value
EP=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
t=[]
def cb(x,l):
    if cls(x)=="NINormalWindow0000000140000000" and u.IsWindowVisible(x): t.append(x)
    return True
u.EnumWindows(EP(cb),0)
for x in t:
    u.ShowWindow(x,9)
    k=u.GetForegroundWindow(); tp=u.GetWindowThreadProcessId(k,None); sp=u.GetWindowThreadProcessId(x,None)
    u.AttachThreadInput(tp,sp,True)
    u.SetForegroundWindow(x); u.BringWindowToTop(x)
    u.AttachThreadInput(tp,sp,False)
    print("target",hex(x),"foreground",hex(u.GetForegroundWindow()))
