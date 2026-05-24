"""Generate 5 synthetic sample crack images for demo purposes."""
import cv2, numpy as np, os

os.makedirs(r"C:\college_project\samples", exist_ok=True)

def concrete_bg(h=480, w=640):
    bg = np.random.randint(160, 200, (h, w, 3), dtype=np.uint8)
    for _ in range(300):
        x,y = np.random.randint(0,w), np.random.randint(0,h)
        r = np.random.randint(2,8)
        c = np.random.randint(130,160)
        cv2.circle(bg,(x,y),r,(c,c,c),-1)
    bg = cv2.GaussianBlur(bg,(3,3),0)
    return bg

def save(name, img):
    path = fr"C:\college_project\samples\{name}"
    cv2.imwrite(path, img)
    print(f"Saved {path}")

# V-01: Vertical flexural crack — midspan beam soffit
img = concrete_bg()
for i in range(5):
    x = 310 + np.random.randint(-4,4)
    pts = np.array([[x+np.random.randint(-2,2), y] for y in range(80,400)], np.int32)
    cv2.polylines(img,[pts],False,(40,40,40),np.random.randint(1,3))
cv2.putText(img,"Midspan Beam - Flexural Crack",(10,460),cv2.FONT_HERSHEY_SIMPLEX,0.6,(80,80,80),1)
save("V01_flexural_midspan.jpg", img)

# V-02: Diagonal shear crack — near support
img = concrete_bg()
for i in range(4):
    x0 = 180+i*6; y0 = 120
    x1 = 380+i*6; y1 = 360
    pts = np.array([[int(x0+(x1-x0)*t/100)+np.random.randint(-2,2),
                     int(y0+(y1-y0)*t/100)] for t in range(101)], np.int32)
    cv2.polylines(img,[pts],False,(30,30,30),np.random.randint(1,3))
cv2.putText(img,"Near Support - Shear Crack (~45 deg)",(10,460),cv2.FONT_HERSHEY_SIMPLEX,0.55,(80,80,80),1)
save("V02_shear_near_support.jpg", img)

# V-03: Diagonal joint crack — beam-column joint panel
img = concrete_bg()
for i in range(3):
    d = i*5
    pts1 = np.array([[200+d+np.random.randint(-2,2), y] for y in range(100,380)
                     if True], np.int32)
    # diagonal in joint panel
    x0,y0 = 160+d,100; x1,y1 = 380+d,370
    pts = np.array([[int(x0+(x1-x0)*t/100)+np.random.randint(-3,3),
                     int(y0+(y1-y0)*t/100)] for t in range(101)], np.int32)
    cv2.polylines(img,[pts],False,(20,20,20),2)
cv2.rectangle(img,(140,90),(420,390),(100,100,100),2)
cv2.putText(img,"B-C Joint Panel - Diagonal Crack",(10,460),cv2.FONT_HERSHEY_SIMPLEX,0.55,(80,80,80),1)
save("V03_joint_diagonal.jpg", img)

# V-04: Hairline vertical — secondary beam midspan
img = concrete_bg()
for i in range(2):
    x = 305+i*8
    pts = np.array([[x+np.random.randint(-1,1), y] for y in range(150,350)], np.int32)
    cv2.polylines(img,[pts],False,(100,100,100),1)
cv2.putText(img,"Secondary Beam - Hairline Crack",(10,460),cv2.FONT_HERSHEY_SIMPLEX,0.55,(80,80,80),1)
save("V04_hairline_secondary.jpg", img)

# V-05: Horizontal crack — column face (bond/split)
img = concrete_bg()
for i in range(4):
    y = 200+i*12
    pts = np.array([[x, y+np.random.randint(-1,1)] for x in range(100,540)], np.int32)
    cv2.polylines(img,[pts],False,(30,30,30),np.random.randint(1,3))
cv2.putText(img,"Column Face - Horizontal Bond Crack",(10,460),cv2.FONT_HERSHEY_SIMPLEX,0.55,(80,80,80),1)
save("V05_horizontal_column.jpg", img)

print("All sample images created.")
