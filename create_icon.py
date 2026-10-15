import math
import struct
import io
from PIL import Image, ImageDraw, ImageFilter
import colorsys

def create_liquid_glass_rainbow_ring(size=512):
    cx, cy = size / 2.0, size / 2.0
    r_ring = 175.0        # Radius of torus ring center
    r_tube = 46.0         # Thickness radius of the torus tube
    
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()
    
    # Light direction: from top-left, slightly forward
    lx, ly, lz = -0.5, -0.6, 0.62
    l_len = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx, ly, lz = lx/l_len, ly/l_len, lz/l_len
    
    # View direction
    vx, vy, vz = 0.0, 0.0, 1.0
    
    for y in range(size):
        dy = y - cy
        for x in range(size):
            dx = x - cx
            dist = math.hypot(dx, dy)
            if dist < 1e-4:
                continue
                
            d_to_ring = abs(dist - r_ring)
            if d_to_ring > r_tube + 3.0:
                continue
                
            # Angle around the ring: seamless [0.0, 1.0)
            angle = math.atan2(dy, dx)
            hue = (angle / (2.0 * math.pi) + 0.5) % 1.0
            
            # Base rainbow color
            base_r, base_g, base_b = colorsys.hsv_to_rgb(hue, 0.95, 1.0)
            base_r = int(base_r * 255)
            base_g = int(base_g * 255)
            base_b = int(base_b * 255)
            
            # Anti-aliased alpha at tube boundary
            if d_to_ring > r_tube:
                edge_fade = max(0.0, 1.0 - (d_to_ring - r_tube) / 3.0)
                norm_d = 1.0
            else:
                edge_fade = 1.0
                norm_d = d_to_ring / r_tube
                
            # 3D Normal of the Torus surface
            rad_dir_x = (dx / dist) * ((dist - r_ring) / r_tube)
            rad_dir_y = (dy / dist) * ((dist - r_ring) / r_tube)
            nz = math.sqrt(max(0.0, 1.0 - norm_d * norm_d))
            nx, ny = rad_dir_x, rad_dir_y
            
            # Diffuse lighting
            dot_nl = max(0.0, nx * lx + ny * ly + nz * lz)
            diffuse = 0.55 + 0.45 * dot_nl
            
            # Specular liquid glass highlight (Blinn-Phong)
            hx = lx + vx
            hy = ly + vy
            hz = lz + vz
            h_len = math.sqrt(hx*hx + hy*hy + hz*hz)
            hx, hy, hz = hx/h_len, hy/h_len, hz/h_len
            
            dot_nh = max(0.0, nx * hx + ny * hy + nz * hz)
            specular = (dot_nh ** 28) * 220.0
            
            # Fresnel glass rim
            fresnel = ((1.0 - nz) ** 3.0) * 80.0
            
            final_r = min(255, int(base_r * diffuse + specular + fresnel * 0.8))
            final_g = min(255, int(base_g * diffuse + specular + fresnel * 0.8))
            final_b = min(255, int(base_b * diffuse + specular + fresnel * 0.8))
            
            alpha = int(255 * edge_fade)
            pixels[x, y] = (final_r, final_g, final_b, alpha)
            
    # Soft ambient glow
    glow = img.filter(ImageFilter.GaussianBlur(24))
    final_canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_data = glow.split()
    glow_alpha = glow_data[3].point(lambda a: int(a * 0.55))
    glow.putalpha(glow_alpha)
    
    final_canvas = Image.alpha_composite(final_canvas, glow)
    final_canvas = Image.alpha_composite(final_canvas, img)
    return final_canvas


def save_compliant_windows_ico(src_img, out_ico_path):
    # Standard Windows sizes: 16, 24, 32, 48, 64, 128, 256
    sizes = [16, 24, 32, 48, 64, 128, 256]
    entries = []
    images_data = []
    
    for s in sizes:
        resized = src_img.resize((s, s), Image.Resampling.LANCZOS)
        if s == 256:
            buf = io.BytesIO()
            resized.save(buf, format="PNG")
            data = buf.getvalue()
        else:
            w, h = s, s
            # DIB BITMAPINFOHEADER (40 bytes)
            header = struct.pack('<IIIHHIIIIII', 40, w, h * 2, 1, 32, 0, w * h * 4, 0, 0, 0, 0)
            rgba = resized.convert('RGBA')
            pix = rgba.load()
            xor_data = bytearray()
            for y in range(h - 1, -1, -1):
                for x in range(w):
                    r, g, b, a = pix[x, y]
                    xor_data.extend([b, g, r, a])
            and_stride = ((w + 31) // 32) * 4
            and_data = b'\x00' * (and_stride * h)
            data = header + xor_data + and_data
            
        images_data.append(data)
        w_b = 0 if s >= 256 else s
        h_b = 0 if s >= 256 else s
        entries.append((w_b, h_b, len(data)))
        
    offset = 6 + len(entries) * 16
    ico_bytes = bytearray()
    ico_bytes.extend(struct.pack('<HHH', 0, 1, len(entries)))
    for (w_b, h_b, size) in entries:
        ico_bytes.extend(struct.pack('<BBBBHHII', w_b, h_b, 0, 0, 1, 32, size, offset))
        offset += size
        
    for data in images_data:
        ico_bytes.extend(data)
        
    with open(out_ico_path, "wb") as f:
        f.write(ico_bytes)
    print(f"Saved Windows compliant ICO ({len(ico_bytes)} bytes) to {out_ico_path}")


if __name__ == "__main__":
    icon_img = create_liquid_glass_rainbow_ring(512)
    icon_img.save("D:\\AI\\AutoHDR_Manager\\icon.png", format="PNG")
    save_compliant_windows_ico(icon_img, "D:\\AI\\AutoHDR_Manager\\icon.ico")
