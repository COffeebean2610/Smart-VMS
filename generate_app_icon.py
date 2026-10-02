import os
from pathlib import Path
from PIL import Image, ImageDraw

def create_smart_vms_icon():
    root = Path(__file__).parent
    build_dir = root / "build"
    electron_dir = root / "electron"
    public_dir = root / "frontend" / "public"

    build_dir.mkdir(parents=True, exist_ok=True)
    electron_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Dark Shield / Badge Background (Dark Navy/Slate gradient fill simulation)
    margin = 16
    shield_polygon = [
        (size // 2, margin),                          # Top center
        (size - margin, margin + 30),                 # Top right
        (size - margin, size // 2 + 30),              # Mid right
        (size // 2, size - margin),                   # Bottom tip
        (margin, size // 2 + 30),                     # Mid left
        (margin, margin + 30)                         # Top left
    ]
    
    # Outer dark shield border & fill
    draw.polygon(shield_polygon, fill=(15, 23, 42, 255), outline=(59, 130, 246, 255), width=6)

    # Inner shield accent ring
    inner_polygon = [
        (size // 2, margin + 16),
        (size - margin - 14, margin + 40),
        (size - margin - 14, size // 2 + 22),
        (size // 2, size - margin - 16),
        (margin + 14, size // 2 + 22),
        (margin + 14, margin + 40)
    ]
    draw.polygon(inner_polygon, fill=(30, 41, 59, 255), outline=(14, 165, 233, 200), width=3)

    # 2. Security Camera Body (Center Graphic)
    cx, cy = size // 2, size // 2 - 5

    # Main camera body box
    cam_box = [cx - 40, cy - 25, cx + 25, cy + 25]
    draw.rounded_rectangle(cam_box, radius=8, fill=(14, 165, 233, 255), outline=(255, 255, 255, 255), width=3)

    # Camera lens cone/hood
    hood_polygon = [
        (cx + 25, cy - 15),
        (cx + 50, cy - 30),
        (cx + 50, cy + 30),
        (cx + 25, cy + 15)
    ]
    draw.polygon(hood_polygon, fill=(59, 130, 246, 255), outline=(255, 255, 255, 255), width=3)

    # Glowing Cyan Lens Iris
    lens_center = (cx - 8, cy)
    r = 16
    draw.ellipse([lens_center[0] - r, lens_center[1] - r, lens_center[0] + r, lens_center[1] + r], fill=(15, 23, 42, 255), outline=(34, 211, 238, 255), width=4)
    r_inner = 8
    draw.ellipse([lens_center[0] - r_inner, lens_center[1] - r_inner, lens_center[0] + r_inner, lens_center[1] + r_inner], fill=(34, 211, 238, 255))

    # Recording Red Pulse Light (Top Left of Camera)
    draw.ellipse([cx - 32, cy - 18, cx - 22, cy - 8], fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=1)

    # Save PNG copies
    png_path_build = build_dir / "icon.png"
    png_path_electron = electron_dir / "icon.png"
    png_path_public = public_dir / "icon.png"

    img.save(png_path_build, format="PNG")
    img.save(png_path_electron, format="PNG")
    img.save(png_path_public, format="PNG")

    # Save Multi-size ICO for Windows
    ico_path_build = build_dir / "icon.ico"
    ico_path_electron = electron_dir / "icon.ico"

    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path_build, format="ICO", sizes=ico_sizes)
    img.save(ico_path_electron, format="ICO", sizes=ico_sizes)

    print(f"Created application icons:\n - {ico_path_build}\n - {png_path_electron}\n - {png_path_public}")

if __name__ == "__main__":
    create_smart_vms_icon()
