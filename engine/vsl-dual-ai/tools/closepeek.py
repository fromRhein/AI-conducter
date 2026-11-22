import ctypes, ctypes.wintypes as w, time
u=ctypes.windll.user32
for h in (0x3507a4, 0x3b078a):
    u.PostMessageW(h, 0x0010, 0, 0)  # WM_CLOSE
time.sleep(1)
print("sent")
