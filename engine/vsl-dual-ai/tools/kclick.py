import ctypes, ctypes.wintypes as w, time, sys
u=ctypes.windll.user32
WIN=0x4a043e
def focus():
    u.ShowWindow(WIN,9)
    k=u.GetForegroundWindow()
    tp=u.GetWindowThreadProcessId(k,None); sp=u.GetWindowThreadProcessId(WIN,None)
    u.AttachThreadInput(tp,sp,True); u.SetForegroundWindow(WIN); u.SetFocus(WIN); u.AttachThreadInput(tp,sp,False)
    time.sleep(0.4)
def click(x,y,n=1):
    u.SetCursorPos(x,y); time.sleep(0.25)
    for i in range(n):
        u.mouse_event(0x0002,0,0,0,0); time.sleep(0.08); u.mouse_event(0x0004,0,0,0,0)
        time.sleep(0.15)
focus()
r=w.RECT(); u.GetWindowRect(WIN,ctypes.byref(r))
print("rect",r.left,r.top,r.right,r.bottom,"fg",hex(u.GetForegroundWindow()))
args=sys.argv[1:]
if args:
    x,y,n=int(args[0]),int(args[1]),int(args[2]) if len(args)>2 else 1
    click(r.left+x, r.top+y, n)
    print("clicked",r.left+x,r.top+y,"x",n)
