import os
try:
    from PIL import Image, ImageDraw
    has_pil = True
except ImportError:
    has_pil = False

os.makedirs("static/icons", exist_ok=True)

if has_pil:
    for size in (192, 512):
        img = Image.new("RGBA", (size, size), (6, 13, 26, 255))
        draw = ImageDraw.Draw(img)
        # Draw a nice rounded icon with a cyan circle
        draw.ellipse([size*0.1, size*0.1, size*0.9, size*0.9], fill=(6, 13, 26, 255), outline=(0, 255, 224, 255), width=max(2, int(size*0.04)))
        # Draw a little robot eye/lightning shape in the center
        draw.polygon([
            (size*0.5, size*0.25),
            (size*0.65, size*0.48),
            (size*0.52, size*0.48),
            (size*0.58, size*0.75),
            (size*0.35, size*0.52),
            (size*0.48, size*0.52)
        ], fill=(0, 255, 224, 255))
        img.save(f"static/icons/icon-{size}.png")
    print("Icons generated successfully using PIL.")
else:
    # 1x1 transparent PNG as fallback to prevent 404
    tiny_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x01\x00\x00\x0c\x00\x01\x12\xac\x1a\x1b\x00\x00\x00\x00IEND\xaeB`\x82'
    with open("static/icons/icon-192.png", "wb") as f:
        f.write(tiny_png)
    with open("static/icons/icon-512.png", "wb") as f:
        f.write(tiny_png)
    print("Fallback tiny PNGs written.")
