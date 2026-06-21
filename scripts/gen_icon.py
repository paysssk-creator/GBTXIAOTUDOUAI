"""生成 GBT 专业图标 — 16x16 ~ 256x256 多层 ICO"""
import os, struct, io
from PIL import Image, ImageDraw, ImageFont

def create_gbt_icon():
    """生成渐变色 GBT 徽章图标"""
    icondir = os.path.join(os.path.dirname(__file__), "desktop")
    
    # 定义各尺寸
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 圆角矩形背景 — 紫色渐变
        r = size // 6
        # 主背景
        for y in range(size):
            ratio = y / size
            r_val = int(108 * (1 - ratio) + 96 * ratio)
            g_val = int(92 * (1 - ratio) + 60 * ratio)
            b_val = int(231 * (1 - ratio) + 144 * ratio)
            draw.line([(r, y), (size - r - 1, y)], fill=(r_val, g_val, b_val, 255))
        
        # 文字 "G"
        font_size = size // 2 + 2
        try:
            font = ImageFont.truetype("segoeui.ttf", font_size)
        except:
            font = ImageFont.load_default()

        text = "G"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (size - tw) // 2
        y = (size - th) // 2 - 1
        
        # 描边效果
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            draw.text((x+dx, y+dy), text, fill=(255,255,255,80), font=font)
        draw.text((x, y), text, fill=(255,255,255,255), font=font)
        
        images.append(img)
    
    # 保存为 ICO
    ico_path = os.path.join(icondir, "GBT.ico")
    # PIL 直接 save 为 ICO
    images[0].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(f"✅ ICO图标生成: {ico_path} ({len(images)} sizes)")
    return ico_path

if __name__ == "__main__":
    create_gbt_icon()
