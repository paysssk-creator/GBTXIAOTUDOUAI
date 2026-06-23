"""生成 GBT 图标 (256x256 .ico)"""
from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 256
img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 深蓝圆角矩形背景
draw.rounded_rectangle([8, 8, SIZE-8, SIZE-8], radius=40, fill=(13, 17, 23, 255))
draw.rounded_rectangle([12, 12, SIZE-12, SIZE-12], radius=36,
                       outline=(35, 134, 54, 255), width=4)

# 文字
try:
    font = ImageFont.truetype("segoeui.ttf", 120)
except:
    font = ImageFont.load_default()

bbox = draw.textbbox((0, 0), "GBT", font=font)
tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
x = (SIZE - tw) // 2
y = (SIZE - th) // 2 - 15
draw.text((x, y), "GBT", fill=(35, 134, 54, 255), font=font)

# 底部小字
try:
    sf = ImageFont.truetype("segoeui.ttf", 24)
    draw.text((SIZE//2-85, SIZE-50), "ALL-IN-ONE", fill=(201, 209, 217, 255), font=sf)
except:
    pass

img.save(os.path.join(os.path.dirname(__file__), 'gbt.ico'), format='ICO', sizes=[(256, 256)])
print("OK: gbt.ico generated")
