#!/usr/bin/env python3
"""
STILL — Product mockup generator v3
Ghost-mannequin style: directional lighting, fabric grain texture,
3D depth gradients, realistic fold lines, interior collar/cuff depth.
"""
import os, random, math
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance

OUTPUT = os.path.join(os.path.dirname(__file__), "images", "products")
os.makedirs(OUTPUT, exist_ok=True)

W, H = 600, 800
BG   = (251, 248, 244)          # warm chalk

PALETTE = {
    'chalk':    (244, 241, 236),
    'graphite': (48,  48,  48),
    'navy':     (27,  43,  75),
    'sand':     (205, 188, 158),
    'black':    (22,  22,  22),
}

# ── colour helpers ──────────────────────────────────────────────
def dk(c, a=28):  return tuple(max(0, x-a) for x in c)
def lt(c, a=28):  return tuple(min(255, x+a) for x in c)
def mix(c1, c2, t):
    return tuple(int(c1[i]*(1-t)+c2[i]*t) for i in range(3))

# ── is the colour light or dark? ────────────────────────────────
def is_light(c): return (c[0]*299+c[1]*587+c[2]*114)/1000 > 128

# ── fabric grain texture ────────────────────────────────────────
def make_grain(w, h, intensity=14, seed=42):
    """Creates a tileable fabric grain texture image (L mode)."""
    rng = random.Random(seed)
    img = Image.new('L', (w, h), 128)
    px  = img.load()
    for y in range(h):
        for x in range(w):
            v = rng.randint(128-intensity, 128+intensity)
            # Slight horizontal warp bias (woven look)
            if x % 3 == 0: v = max(0, v - 8)
            px[x, y] = v
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    return img

GRAIN = make_grain(W, H, intensity=11)

def apply_grain(base_rgba, garment_mask, strength=0.07):
    """Overlay fabric grain onto the garment area."""
    grain_rgb = Image.merge('RGB', [GRAIN]*3)
    grain_rgb = grain_rgb.resize((W, H))
    result = base_rgba.copy().convert('RGB')
    # Blend grain using soft-light-like formula
    for y in range(H):
        for x in range(W):
            if garment_mask.getpixel((x, y)) > 10:
                gr, gg, gb = grain_rgb.getpixel((x, y))
                pr, pg, pb = result.getpixel((x, y))
                t = strength * ((gr - 128) / 128.0)
                nr = int(max(0, min(255, pr + pr*t)))
                ng = int(max(0, min(255, pg + pg*t)))
                nb = int(max(0, min(255, pb + pb*t)))
                result.putpixel((x, y), (nr, ng, nb))
    return result

def fast_grain(base_img, mask_img, strength=0.05):
    """Faster grain using ImageChops."""
    grain = GRAIN.resize((W, H)).convert('RGB')
    # screen blend: result = 1-(1-a)(1-b)
    inv_base  = ImageChops.invert(base_img)
    inv_grain = ImageChops.invert(grain)
    screened  = ImageChops.invert(ImageChops.multiply(inv_base, inv_grain))
    blended   = Image.blend(base_img, screened, strength)
    # only apply where garment exists
    mask_3ch = mask_img.convert('RGB')
    out = Image.composite(blended, base_img, mask_img)
    return out

# ── directional lighting gradient (top-left highlight) ──────────
def lighting_overlay(garment_mask, color, angle_deg=135, strength=0.22):
    """
    Creates a highlight/shadow gradient at `angle_deg` projected onto
    the garment silhouette. Returns RGBA image.
    """
    overlay = Image.new('RGBA', (W, H), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    rad = math.radians(angle_deg)
    lx = math.cos(rad); ly = math.sin(rad)
    # Sample at each pixel whether it is in the highlight or shadow zone
    # We do this coarsely by drawing gradient bands
    for step in range(40):
        t = step / 39.0
        # t=0 => highlight side, t=1 => shadow side
        shade = int(strength * 255 * (t - 0.5))   # -range to +range
        alpha = int(120 * (1 - abs(t - 0.5)*2))    # peak at t=0.5 edges
        if shade > 0:
            fill = (min(255,color[0]+shade), min(255,color[1]+shade), min(255,color[2]+shade), alpha//3)
        else:
            fill = (max(0,color[0]+shade), max(0,color[1]+shade), max(0,color[2]+shade), alpha//2)
        # Draw strip perpendicular to light direction
        ox = lx * (step - 20) * 15
        oy = ly * (step - 20) * 15
        d.rectangle([0,0,W,H], fill=fill)
    # This approach needs a mask composite
    overlay.putalpha(garment_mask)
    return overlay

def add_lighting(base_rgba, garment_mask, color, strength=0.28):
    """
    Faster approach: create two gradients (highlight top-left, shadow bottom-right)
    and composite them onto the garment using the mask.
    """
    w, h = W, H
    # Highlight gradient (top-left → transparent centre)
    hi = Image.new('RGBA', (w, h), (0,0,0,0))
    hi_d = ImageDraw.Draw(hi)
    hi_amount = int(strength * 255 * 0.6)
    hi_color = lt(color, hi_amount)
    for i in range(120):
        alpha = int(90 * (1 - i/120.0))
        hi_d.line([(0, i*2), (i*2, 0)], fill=(*hi_color, alpha), width=3)

    # Shadow gradient (bottom-right)
    sh = Image.new('RGBA', (w, h), (0,0,0,0))
    sh_d = ImageDraw.Draw(sh)
    sh_amount = int(strength * 255 * 0.55)
    sh_color = dk(color, sh_amount)
    for i in range(130):
        alpha = int(85 * (1 - i/130.0))
        sh_d.line([(w, h-i*2), (w-i*2, h)], fill=(*sh_color, alpha), width=3)

    # Mask both to garment shape
    def apply_masked(layer, mask):
        lr, lg, lb, la = layer.split()
        masked_a = ImageChops.multiply(la, mask)
        return Image.merge('RGBA', (lr, lg, lb, masked_a))

    hi = apply_masked(hi, garment_mask)
    sh = apply_masked(sh, garment_mask)

    result = Image.alpha_composite(base_rgba, hi)
    result = Image.alpha_composite(result, sh)
    return result

# ── realistic drop shadow ────────────────────────────────────────
def drop_shadow(garment_mask, offset=(12, 18), blur=26, opacity=0.42):
    sh = Image.new('RGBA', (W, H), (0,0,0,0))
    shadow_color = Image.new('RGBA', (W, H), (20, 16, 12, 255))
    sh.paste(shadow_color, offset, garment_mask)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    r,g,b,a = sh.split()
    a = a.point(lambda x: int(x * opacity))
    return Image.merge('RGBA', (r,g,b,a))

# ── interior depth (collar/cuff openings) ───────────────────────
def draw_interior(d, cx, cy, w, h, color, depth=22):
    """Draw an elliptical hole with interior shadow — ghost mannequin effect."""
    inner = dk(color, 55)
    d.ellipse([cx-w//2, cy-h//2, cx+w//2, cy+h//2], fill=inner)
    # graduated rim
    steps = min(6, w//4, h//4)
    for i in range(steps):
        t = i / max(steps,1)
        rim_c = mix(inner, color, t)
        x0 = cx-w//2+i*2; x1 = cx+w//2-i*2
        y0 = cy-h//2+i;   y1 = cy+h//2-i
        if x1 > x0 and y1 > y0:
            d.ellipse([x0, y0, x1, y1], outline=rim_c, width=1)

# ── fold line helper ─────────────────────────────────────────────
def fold_line(d, x1, y1, x2, y2, color, strength=1):
    c = dk(color, 18 * strength)
    d.line([(x1,y1),(x2,y2)], fill=c, width=1)

def curved_fold(d, x1, y1, x2, y2, curve, color):
    """Draw a bezier-like fold curve using small line segments."""
    steps = 20
    c = dk(color, 22)
    pts = []
    for i in range(steps+1):
        t = i / steps
        # quadratic bezier with midpoint control
        mx = (x1+x2)//2 + curve
        my = (y1+y2)//2
        x = int((1-t)**2*x1 + 2*(1-t)*t*mx + t**2*x2)
        y = int((1-t)**2*y1 + 2*(1-t)*t*my + t**2*y2)
        pts.append((x,y))
    for i in range(len(pts)-1):
        d.line([pts[i], pts[i+1]], fill=c, width=1)

# ══════════════════════════════════════════════════════════════════
#  GARMENT DRAWERS
# ══════════════════════════════════════════════════════════════════

def tee(d, c, boxy=False, extended=False, fitted=False):
    sw = 88 if boxy else (68 if fitted else 78)   # sleeve width
    bw = 290 if boxy else (245 if fitted else 268)
    bt = 210 if boxy else 218
    bh = 330 if extended else (285 if fitted else 308)
    bl, br = 300-bw//2, 300+bw//2
    bb = bt + bh
    # rib hem
    hem_c = dk(c, 16)
    # sleeves
    d.polygon([(bl,bt+24),(bl-sw,bt+4),(bl-sw+7,bt+86),(bl,bt+100)], fill=c)
    d.polygon([(br,bt+24),(br+sw,bt+4),(br+sw-7,bt+86),(br,bt+100)], fill=c)
    # sleeve cuff interior
    draw_interior(d, bl-sw+4, bt+42, 14, 48, c)
    draw_interior(d, br+sw-4, bt+42, 14, 48, c)
    # body
    d.rectangle([bl,bt,br,bb], fill=c)
    # collar interior
    cw = 108 if boxy else (88 if fitted else 98)
    draw_interior(d, 300, bt+20, cw, 52, c)
    # hem line
    d.rectangle([bl, bb-10, br, bb], fill=hem_c)
    # fold lines
    curved_fold(d, bl+30, bt+130, bl+50, bt+240, 8, c)
    curved_fold(d, br-30, bt+130, br-50, bt+240, -8, c)
    curved_fold(d, 300, bt+150, 300, bt+bb-bt-30, 0, c)
    if boxy:
        curved_fold(d, bl+40, bt+60, 300-30, bt+120, 4, c)
        curved_fold(d, br-40, bt+60, 300+30, bt+120, -4, c)
    # underarm fold
    fold_line(d, bl, bt+80, bl+22, bt+110, c)
    fold_line(d, br, bt+80, br-22, bt+110, c)

def long_sleeve(d, c, slim=False):
    bw = 250 if slim else 268
    bt = 210
    bh = 318
    bl, br = 300-bw//2, 300+bw//2
    bb = bt + bh
    # long sleeves
    d.polygon([(bl,bt+26),(bl-78,bt+10),(bl-70,bt+235),(bl,bt+248)], fill=c)
    d.polygon([(br,bt+26),(br+78,bt+10),(br+70,bt+235),(br,bt+248)], fill=c)
    # cuffs
    cuff_c = dk(c, 20)
    d.rectangle([bl-72,bt+230,bl-56,bt+252], fill=cuff_c)
    d.rectangle([br+56,bt+230,br+72,bt+252], fill=cuff_c)
    # cuff interior
    draw_interior(d, bl-64, bt+242, 12, 20, c)
    draw_interior(d, br+64, bt+242, 12, 20, c)
    # body
    d.rectangle([bl,bt,br,bb], fill=c)
    # collar
    cw = 90 if slim else 98
    draw_interior(d, 300, bt+20, cw, 50, c)
    # hem
    d.rectangle([bl, bb-10, br, bb], fill=dk(c,16))
    # fold lines
    curved_fold(d, bl+22, bt+130, bl+38, bt+260, 5, c)
    curved_fold(d, br-22, bt+130, br-38, bt+260, -5, c)
    fold_line(d, bl, bt+82, bl+18, bt+115, c)
    fold_line(d, br, bt+82, br-18, bt+115, c)
    # sleeve fold
    curved_fold(d, bl-55, bt+80, bl-65, bt+200, -5, c)
    curved_fold(d, br+55, bt+80, br+65, bt+200, 5, c)

def hoodie(d, c, full_zip=False):
    bt = 192; bw = 298
    bl, br = 300-bw//2, 300+bw//2
    bb = bt + 372
    # hood panels
    hood_pts = [(300-85,bt+26),(300-100,bt-35),(300-65,bt-88),(300,bt-108),(300+65,bt-88),(300+100,bt-35),(300+85,bt+26)]
    d.polygon(hood_pts, fill=c)
    # hood shadow (inner)
    inner_hood = dk(c, 38)
    d.arc([300-58,bt-90,300+58,bt+18], start=198, end=342, fill=inner_hood, width=4)
    draw_interior(d, 300, bt-30, 90, 62, c)
    # drawcord holes
    dh_c = dk(c, 48)
    d.ellipse([300-35,bt+20,300-22,bt+32], fill=dh_c)
    d.ellipse([300+22,bt+20,300+35,bt+32], fill=dh_c)
    # sleeves
    d.polygon([(bl,bt+26),(bl-105,bt+10),(bl-95,bt+118),(bl,bt+132)], fill=c)
    d.polygon([(br,bt+26),(br+105,bt+10),(br+95,bt+118),(br,bt+132)], fill=c)
    # ribbed cuffs
    cuff_c = dk(c, 22)
    d.rectangle([bl-97,bt+106,bl-78,bt+134], fill=cuff_c)
    d.rectangle([br+78,bt+106,br+97,bt+134], fill=cuff_c)
    for i in range(0,20,4):
        d.line([(bl-97+i,bt+106),(bl-97+i,bt+134)], fill=dk(cuff_c,8), width=1)
        d.line([(br+78+i,bt+106),(br+78+i,bt+134)], fill=dk(cuff_c,8), width=1)
    draw_interior(d, bl-88, bt+121, 14, 22, c)
    draw_interior(d, br+88, bt+121, 14, 22, c)
    # body
    d.rectangle([bl,bt,br,bb], fill=c)
    if full_zip:
        # full zip line
        d.line([(300,bt+18),(300,bb-30)], fill=dk(c,40), width=4)
        # zip pull
        d.rectangle([300-7,bt+18,300+7,bt+40], fill=(160,155,145))
        d.ellipse([300-9,bt+36,300+9,bt+50], fill=(140,135,125))
        # zip hand pockets
        for px in [bl+50, br-50]:
            d.line([(px-44,bt+215),(px+44,bt+215)], fill=dk(c,34), width=2)
    else:
        # kangaroo pocket
        pk_c = dk(c, 14)
        py = bt+198
        d.rectangle([300-95,py,300+95,py+80], fill=pk_c)
        d.line([(300,py),(300,py+80)], fill=dk(c,22), width=1)
        # pocket inner shadow
        d.rectangle([300-95,py,300+95,py+8], fill=dk(c,28))
    # ribbed hem
    hem_c = dk(c, 22)
    d.rectangle([bl,bb-34,br,bb], fill=hem_c)
    for i in range(0,bw,6): d.line([(bl+i,bb-34),(bl+i,bb)], fill=dk(hem_c,8), width=1)
    # fold lines
    curved_fold(d, bl+28, bt+90, bl+45, bt+230, 9, c)
    curved_fold(d, br-28, bt+90, br-45, bt+230, -9, c)
    curved_fold(d, 300, bt+110, 300, bb-38, 0, c)
    fold_line(d, bl, bt+85, bl+24, bt+118, c)
    fold_line(d, br, bt+85, br-24, bt+118, c)

def polo(d, c):
    bt = 218; bw = 262
    bl, br = 300-bw//2, 300+bw//2
    bb = bt + 318
    # short sleeves
    d.polygon([(bl,bt+36),(bl-72,bt+18),(bl-65,bt+92),(bl,bt+102)], fill=c)
    d.polygon([(br,bt+36),(br+72,bt+18),(br+65,bt+92),(br,bt+102)], fill=c)
    draw_interior(d, bl-65, bt+50, 14, 44, c)
    draw_interior(d, br+65, bt+50, 14, 44, c)
    # body
    d.rectangle([bl,bt,br,bb], fill=c)
    # ribbed collar
    cw = 115; collar_c = dk(c, 20)
    d.rectangle([300-cw//2,bt-14,300+cw//2,bt+52], fill=collar_c)
    for i in range(0,cw,5): d.line([(300-cw//2+i,bt-14),(300-cw//2+i,bt+52)], fill=dk(collar_c,8), width=1)
    draw_interior(d, 300, bt+22, 68, 42, c)
    # placket
    pl_c = dk(c, 18)
    d.rectangle([300-12,bt+42,300+12,bt+158], fill=pl_c)
    for by in [bt+65,bt+100,bt+135]:
        d.ellipse([300-4,by-4,300+4,by+4], fill=(215,210,200), outline=dk(c,40), width=1)
    # curved hem
    d.arc([bl-10,bb-30,br+10,bb+30], start=1, end=179, fill=c, width=28)
    # hem rib
    d.arc([bl-10,bb-38,br+10,bb+22], start=1, end=179, fill=dk(c,18), width=10)
    curved_fold(d, bl+25, bt+118, bl+40, bb-30, 7, c)
    curved_fold(d, br-25, bt+118, br-40, bb-30, -7, c)

def oxford_shirt(d, c):
    bt = 192; bw = 270
    bl, br = 300-bw//2, 300+bw//2
    bb = bt + 352
    # long sleeves with cuffs
    d.polygon([(bl,bt+36),(bl-88,bt+20),(bl-79,bt+248),(bl,bt+260)], fill=c)
    d.polygon([(br,bt+36),(br+88,bt+20),(br+79,bt+248),(br,bt+260)], fill=c)
    cuff_c = dk(c, 22)
    d.rectangle([bl-81,bt+236,bl-64,bt+262], fill=cuff_c)
    d.rectangle([br+64,bt+236,br+81,bt+262], fill=cuff_c)
    # cuff buttons
    for cy_ in [bt+244, bt+256]:
        d.ellipse([bl-76,cy_-3,bl-70,cy_+3], fill=(215,210,200))
        d.ellipse([br+70,cy_-3,br+76,cy_+3], fill=(215,210,200))
    draw_interior(d, bl-73, bt+250, 12, 20, c)
    draw_interior(d, br+73, bt+250, 12, 20, c)
    # body
    d.rectangle([bl,bt,br,bb], fill=c)
    # spread collar
    lc = [(300-6,bt+50),(300-85,bt+4),(300-64,bt-16),(300-6,bt+18)]
    rc = [(300+6,bt+50),(300+85,bt+4),(300+64,bt-16),(300+6,bt+18)]
    d.polygon(lc, fill=c)
    d.polygon(rc, fill=c)
    d.line([(300-6,bt+50),(300-85,bt+4)], fill=dk(c,30), width=1)
    d.line([(300+6,bt+50),(300+85,bt+4)], fill=dk(c,30), width=1)
    draw_interior(d, 300, bt+18, 78, 50, c)
    # button placket
    d.line([(300,bt+36),(300,bb)], fill=dk(c,24), width=2)
    for by in range(bt+64, bb-25, 55):
        d.ellipse([300-4,by-4,300+4,by+4], fill=(222,217,207))
    # chest pocket
    px = bl+32
    d.rectangle([px,bt+98,px+58,bt+142], fill=dk(c,14))
    d.line([(px,bt+98),(px+58,bt+98)], fill=dk(c,30), width=1)
    curved_fold(d, bl+22, bt+150, bl+35, bb-20, 6, c)
    curved_fold(d, br-22, bt+150, br-35, bb-20, -6, c)
    fold_line(d, bl, bt+80, bl+20, bt+115, c)
    fold_line(d, br, bt+80, br-20, bt+115, c)

def overshirt(d, c):
    bt = 188; bw = 308
    bl, br = 300-bw//2, 300+bw//2
    bb = bt + 375
    # long sleeves
    d.polygon([(bl,bt+30),(bl-94,bt+14),(bl-84,bt+265),(bl,bt+275)], fill=c)
    d.polygon([(br,bt+30),(br+94,bt+14),(br+84,bt+265),(br,bt+275)], fill=c)
    cuff_c = dk(c, 24)
    d.rectangle([bl-86,bt+253,bl-68,bt+277], fill=cuff_c)
    d.rectangle([br+68,bt+253,br+86,bt+277], fill=cuff_c)
    draw_interior(d, bl-77, bt+266, 14, 22, c)
    draw_interior(d, br+77, bt+266, 14, 22, c)
    # body
    d.rectangle([bl,bt,br,bb], fill=c)
    # camp collar
    d.polygon([(300-8,bt+55),(300-80,bt+3),(300-60,bt-15),(300-8,bt+22)], fill=c)
    d.polygon([(300+8,bt+55),(300+80,bt+3),(300+60,bt-15),(300+8,bt+22)], fill=c)
    d.line([(300-8,bt+55),(300-80,bt+3)], fill=dk(c,30), width=1)
    d.line([(300+8,bt+55),(300+80,bt+3)], fill=dk(c,30), width=1)
    draw_interior(d, 300, bt+20, 80, 52, c)
    # center buttons
    d.line([(300,bt+36),(300,bb)], fill=dk(c,24), width=2)
    for by in range(bt+70,bb-18,64):
        d.ellipse([300-5,by-5,300+5,by+5], fill=(214,209,199))
    # chest pockets with flaps
    for pcx in [bl+54, br-54]:
        d.rectangle([pcx-32,bt+90,pcx+32,bt+155], fill=dk(c,15))
        flap = [(pcx-32,bt+90),(pcx+32,bt+90),(pcx+34,bt+112),(pcx-34,bt+112)]
        d.polygon(flap, fill=dk(c,24))
        d.ellipse([pcx-4,bt+87,pcx+4,bt+95], fill=(214,209,199))
    curved_fold(d, bl+22, bt+158, bl+38, bb-18, 8, c)
    curved_fold(d, br-22, bt+158, br-38, bb-18, -8, c)
    fold_line(d, bl, bt+80, bl+22, bt+118, c)
    fold_line(d, br, bt+80, br-22, bt+118, c)

def trouser(d, c, style='standard'):
    wt = 152; ww = 205; hw = 228
    wl, wr = 300-ww//2, 300+ww//2
    hl, hr = 300-hw//2, 300+hw//2
    ht = wt+70; cy = ht+90; bot = 688

    # waistband
    wb_c = dk(c, 28)
    d.rectangle([wl,wt,wr,wt+46], fill=wb_c)

    if style == 'wide':
        hl = 300-148; hr = 300+148
        hw = 296
        # drawcord at high waist (no loops)
        wt = 144; wl, wr = 300-ww//2, 300+ww//2
        wb_c = dk(c, 28)
        d.rectangle([wl,wt,wr,wt+52], fill=wb_c)
        d.line([(300-30,wt+32),(300+30,wt+32)], fill=(204,199,189), width=3)
        d.ellipse([300-36,wt+26,300-24,wt+38], fill=(204,199,189))
        d.ellipse([300+24,wt+26,300+36,wt+38], fill=(204,199,189))
        ht = wt+72; cy = ht+98; bot = 698
    elif style == 'chino':
        # clean welt back pockets
        for bx in [wl+22,wl+68,300-12,300+12,wr-68,wr-22]:
            d.rectangle([bx,wt-5,bx+9,wt+50], fill=dk(c,46))
    else:
        # belt loops
        for bx in [wl+22,wl+68,300-12,300+12,wr-68,wr-22]:
            d.rectangle([bx,wt-5,bx+9,wt+50], fill=dk(c,46))

    # hip trapezoid
    d.polygon([(wl,wt+46),(wr,wt+46),(hr,ht),(hl,ht)], fill=c)

    if style == 'wide':
        # wide flared legs
        d.polygon([(hl,cy),(300-5,cy),(300-24,bot),(hl-24,bot)], fill=c)
        d.polygon([(300+5,cy),(hr,cy),(hr+24,bot),(300+24,bot)], fill=c)
        d.rectangle([hl,ht,hr,cy+5], fill=c)
        d.line([(300-34,ht+80),(300-58,bot)], fill=dk(c,22), width=2)
        d.line([(300+34,ht+80),(300+58,bot)], fill=dk(c,22), width=2)
        curved_fold(d, hl-24, cy+100, hl-20, bot-80, 6, c)
        curved_fold(d, hr+24, cy+100, hr+20, bot-80, -6, c)
    elif style == 'chino':
        d.polygon([(hl,cy),(300-5,cy),(300-22,bot),(hl-12,bot)], fill=c)
        d.polygon([(300+5,cy),(hr,cy),(hr+12,bot),(300+22,bot)], fill=c)
        d.rectangle([hl,ht,hr,cy+5], fill=c)
        d.line([(300-30,ht+74),(300-40,bot)], fill=dk(c,15), width=1)
        d.line([(300+30,ht+74),(300+40,bot)], fill=dk(c,15), width=1)
    else:
        # standard / five-pocket
        d.polygon([(hl,cy),(300-5,cy),(300-14,bot),(hl-5,bot)], fill=c)
        d.polygon([(300+5,cy),(hr,cy),(hr+5,bot),(300+14,bot)], fill=c)
        d.rectangle([hl,ht,hr,cy+5], fill=c)
        d.line([(300-32,ht+75),(300-42,bot)], fill=dk(c,16), width=1)
        d.line([(300+32,ht+75),(300+42,bot)], fill=dk(c,16), width=1)
        if style == 'five_pocket':
            d.arc([300-198,ht-22,300-92,ht+64], start=205, end=340, fill=dk(c,34), width=2)
            d.arc([300+92,ht-22,300+198,ht+64], start=205, end=340, fill=dk(c,34), width=2)
            d.arc([300+52,ht-8,300+115,ht+48], start=186, end=358, fill=dk(c,34), width=2)

    # edge shading on legs
    for i in range(14):
        shade = dk(c, 20-i)
        if style == 'wide':
            d.line([(hl-24+i,cy+2),(hl-24+i,bot)], fill=shade, width=1)
            d.line([(hr+24-i,cy+2),(hr+24-i,bot)], fill=shade, width=1)
        else:
            d.line([(hl-5+i,cy+2),(hl-5+i,bot)], fill=shade, width=1)
            d.line([(hr+5-i,cy+2),(hr+5-i,bot)], fill=shade, width=1)
    # natural leg folds
    curved_fold(d, 300-45, ht+120, 300-50, bot-80, 3, c)
    curved_fold(d, 300+45, ht+120, 300+50, bot-80, -3, c)

def shorts(d, c, inseam=162, linen=False):
    wt = 222; ww = 215; hw = 236
    wl, wr = 300-ww//2, 300+ww//2
    hl, hr = 300-hw//2, 300+hw//2
    ht = wt+66; cy = ht+84; bot = cy+inseam
    wb_c = dk(c, 26)
    d.rectangle([wl,wt,wr,wt+46], fill=wb_c)
    d.line([(300-30,wt+26),(300+30,wt+26)], fill=(204,199,189), width=3)
    d.polygon([(wl,wt+46),(wr,wt+46),(hr,ht),(hl,ht)], fill=c)
    d.polygon([(hl,cy),(300-5,cy),(300-8,bot),(hl+5,bot)], fill=c)
    d.polygon([(300+5,cy),(hr,cy),(hr-5,bot),(300+8,bot)], fill=c)
    d.rectangle([hl,ht,hr,cy], fill=c)
    # hem
    d.rectangle([hl+5,bot-6,hr-5,bot+6], fill=dk(c,18))
    if linen:
        d.line([(hl+5,bot-28),(hl+5,bot+8)], fill=dk(c,30), width=2)
        d.line([(hr-5,bot-28),(hr-5,bot+8)], fill=dk(c,30), width=2)
    # edge shading
    for i in range(11):
        d.line([(hl+i,cy),(hl+i,bot)], fill=dk(c,16-i), width=1)
        d.line([(hr-i,cy),(hr-i,bot)], fill=dk(c,16-i), width=1)
    curved_fold(d, hl+35, cy+40, hl+28, bot-20, 4, c)
    curved_fold(d, hr-35, cy+40, hr-28, bot-20, -4, c)

def track_pant(d, c, tech=False):
    wt = 152; ww = 210; hw = 232
    wl, wr = 300-ww//2, 300+ww//2
    hl, hr = 300-hw//2, 300+hw//2
    ht = wt+70; cy = ht+90; bot = 690
    wb_c = dk(c, 25)
    d.rectangle([wl,wt,wr,wt+52], fill=wb_c)
    if not tech:
        for i in range(0,ww,6): d.line([(wl+i,wt),(wl+i,wt+52)], fill=dk(wb_c,8), width=1)
        d.line([(300-34,wt+28),(300+34,wt+28)], fill=(204,199,189), width=3)
        d.ellipse([300-40,wt+22,300-28,wt+35], fill=(204,199,189))
        d.ellipse([300+28,wt+22,300+40,wt+35], fill=(204,199,189))
    d.polygon([(wl,wt+52),(wr,wt+52),(hr,ht),(hl,ht)], fill=c)
    d.polygon([(hl,cy),(300-5,cy),(300-18,bot),(hl-6,bot)], fill=c)
    d.polygon([(300+5,cy),(hr,cy),(hr+6,bot),(300+18,bot)], fill=c)
    d.rectangle([hl,ht,hr,cy+5], fill=c)
    if not tech:
        rib_c = dk(c, 22)
        for side in [(hl-6,300-16), (300+16,hr+6)]:
            d.rectangle([side[0],bot-40,side[1],bot], fill=rib_c)
            w = side[1]-side[0]
            for i in range(0,w,5): d.line([(side[0]+i,bot-40),(side[0]+i,bot)], fill=dk(rib_c,8), width=1)
    else:
        d.line([(hl-6,bot),(300-16,bot)], fill=dk(c,32), width=3)
        d.line([(300+16,bot),(hr+6,bot)], fill=dk(c,32), width=3)
    # back zip pocket
    d.arc([300-52,cy-62,300+52,cy+22], start=200, end=340, fill=dk(c,34), width=2)
    d.line([(300-36,ht+74),(300-50,bot)], fill=dk(c,16), width=1)
    d.line([(300+36,ht+74),(300+50,bot)], fill=dk(c,16), width=1)
    for i in range(12):
        d.line([(hl-6+i,cy),(hl-6+i,bot)], fill=dk(c,18-i), width=1)
        d.line([(hr+6-i,cy),(hr+6-i,bot)], fill=dk(c,18-i), width=1)
    curved_fold(d, 300-42, ht+118, 300-48, bot-70, 3, c)
    curved_fold(d, 300+42, ht+118, 300+48, bot-70, -3, c)

def hat_sixpanel(d, c):
    cx, cy = 300, 390
    cw, ch = 228, 164
    # six panels
    d.polygon([(cx,cy-ch-10),(cx+cw//2+14,cy-30),(cx+cw//2,cy+12),(cx-cw//2,cy+12),(cx-cw//2-14,cy-30)], fill=c)
    for xo in [-26, 0, 26]:
        d.line([(cx,cy-ch-6),(cx+xo*3,cy+12)], fill=dk(c,22), width=1)
    # highlight on crown
    d.ellipse([cx-40,cy-ch-10,cx+40,cy-ch+40], fill=lt(c,18) if not is_light(c) else dk(c,10))
    # sweatband
    d.ellipse([cx-cw//2-4,cy-4,cx+cw//2+4,cy+30], fill=dk(c,32))
    # brim
    brim_pts = [(cx-cw//2-14,cy+14),(cx-cw//2+20,cy+34),(cx-64,cy+48),(cx+64,cy+48),(cx+cw//2-20,cy+34),(cx+cw//2+14,cy+14)]
    d.polygon(brim_pts, fill=dk(c,44))
    d.line([(cx-64,cy+48),(cx+64,cy+48)], fill=dk(c,58), width=2)
    # brim underside
    d.arc([cx-64,cy+36,cx+64,cy+60], start=0, end=180, fill=dk(c,62), width=3)
    # top button
    d.ellipse([cx-8,cy-ch-22,cx+8,cy-ch-5], fill=dk(c,14))
    d.ellipse([cx-4,cy-ch-18,cx+4,cy-ch-9], fill=(208,203,193))
    # back strap
    d.rectangle([cx-20,cy+17,cx+20,cy+27], fill=dk(c,55), outline=(155,148,138), width=1)
    d.rectangle([cx-4,cy+17,cx+4,cy+27], fill=(188,183,173))

def hat_wool(d, c):
    cx, cy = 300, 390
    cw, ch = 218, 160
    d.polygon([(cx,cy-ch-24),(cx+cw//2+18,cy-20),(cx+cw//2,cy+16),(cx-cw//2,cy+16),(cx-cw//2-18,cy-20)], fill=c)
    for xo in [-20, 0, 20]:
        d.line([(cx,cy-ch-20),(cx+xo*3,cy+16)], fill=dk(c,18), width=1)
    d.ellipse([cx-40,cy-ch-10,cx+40,cy-ch+42], fill=lt(c,16) if not is_light(c) else dk(c,10))
    d.ellipse([cx-cw//2-4,cy-2,cx+cw//2+4,cy+30], fill=dk(c,30))
    brim_pts = [(cx-cw//2-5,cy+14),(cx-cw//2+16,cy+30),(cx-54,cy+36),(cx+54,cy+36),(cx+cw//2-16,cy+30),(cx+cw//2+5,cy+14)]
    d.polygon(brim_pts, fill=dk(c,46))
    d.line([(cx-54,cy+36),(cx+54,cy+36)], fill=dk(c,60), width=2)
    d.ellipse([cx-8,cy-ch-24,cx+8,cy-ch-7], fill=dk(c,14))
    d.ellipse([cx-4,cy-ch-20,cx+4,cy-ch-11], fill=(208,203,193))

def hat_bucket(d, c):
    cx, cy = 300, 392
    cw, ch = 198, 138
    # crown
    d.ellipse([cx-cw//2,cy-26,cx+cw//2,cy+26], fill=dk(c,24))
    d.rectangle([cx-cw//2,cy-ch,cx+cw//2,cy], fill=c)
    d.ellipse([cx-cw//2,cy-ch-14,cx+cw//2,cy-ch+14], fill=lt(c,20))
    # crown seam
    d.ellipse([cx-cw//2+3,cy-ch-12,cx+cw//2-3,cy-ch+12], outline=dk(c,28), width=1)
    # wide brim
    bw = 282
    d.ellipse([cx-bw//2,cy-16,cx+bw//2,cy+60], fill=dk(c,24))
    d.ellipse([cx-cw//2+5,cy-13,cx+cw//2-5,cy+23], fill=c)
    # brim top surface
    d.arc([cx-bw//2+8,cy-12,cx+bw//2-8,cy+22], start=180, end=0, fill=lt(c,10), width=2)
    # highlight on crown
    d.ellipse([cx-38,cy-ch-5,cx+38,cy-ch+44], fill=lt(c,14) if not is_light(c) else dk(c,10))

def sock_crew(d, c):
    for ox, oy in [(-34,-20),(24,24)]:
        x, y = 300+ox, 408+oy
        lw = 70; lh = 200
        # leg with rounded top
        d.rounded_rectangle([x-lw//2,y-lh,x+lw//2,y+18], radius=14, fill=c)
        # ribbing bands
        rib_c = dk(c, 14)
        for ri in range(0, 44, 5):
            d.line([(x-lw//2,y-lh+ri),(x+lw//2,y-lh+ri)], fill=rib_c, width=1)
        # heel
        d.ellipse([x-lw//2-10,y-18,x+lw//2+10,y+56], fill=dk(c,30))
        draw_interior(d, x+2, y+18, lw-10, 20, c)
        # foot
        d.rounded_rectangle([x-10,y+8,x+90,y+64], radius=10, fill=c)
        # toe
        d.ellipse([x+72,y+4,x+114,y+68], fill=dk(c,30))
        draw_interior(d, x+93, y+38, 16, 28, c)
        # subtle texture on leg
        curved_fold(d, x-lw//2+5, y-lh+55, x-lw//2+5, y-8, 3, c)

def sock_noshow(d, c):
    for ox, oy in [(-44,-15),(34,26)]:
        x, y = 300+ox, 448+oy
        fw = 100; fh = 56
        d.rounded_rectangle([x-15,y,x+fw,y+fh], radius=12, fill=c)
        d.ellipse([x-28,y+10,x+14,y+50], fill=dk(c,30))
        draw_interior(d, x-8, y+32, 18, 22, c)
        d.ellipse([x+fw-24,y+2,x+fw+18,y+fh+2], fill=dk(c,30))
        # silicone grip dots
        for dy in range(3):
            for dx in range(2):
                px=x-20+dx*12; py=y+22+dy*9
                d.ellipse([px,py,px+5,py+5], fill=dk(c,54))

# ══════════════════════════════════════════════════════════════════
#  COMPOSE & SAVE
# ══════════════════════════════════════════════════════════════════

def make(draw_fn, color_key, filename, **kwargs):
    c = PALETTE[color_key]

    # 1. Draw garment onto transparent layer
    garment_layer = Image.new('RGBA', (W,H), (0,0,0,0))
    d = ImageDraw.Draw(garment_layer)
    draw_fn(d, c, **kwargs)

    # 2. Extract garment mask (alpha channel)
    garment_mask = garment_layer.split()[3]

    # 3. Build base with warm background
    base = Image.new('RGB', (W,H), BG)

    # 4. Drop shadow
    shadow = drop_shadow(garment_mask)
    base_rgba = Image.alpha_composite(base.convert('RGBA'), shadow)

    # 5. Composite garment
    base_rgba = Image.alpha_composite(base_rgba, garment_layer)

    # 6. Add directional lighting for 3D depth
    base_rgba = add_lighting(base_rgba, garment_mask, c, strength=0.24)

    # 7. Fabric grain texture
    garment_rgb = base_rgba.convert('RGB')
    garment_rgb = fast_grain(garment_rgb, garment_mask, strength=0.055)

    # 8. Subtle overall image vignette
    vignette = Image.new('RGBA', (W,H), (0,0,0,0))
    vd = ImageDraw.Draw(vignette)
    for i in range(60):
        alpha = int(i * 1.2)
        vd.rectangle([i,i,W-i,H-i], outline=(20,16,12,alpha), width=1)
    garment_final = Image.alpha_composite(garment_rgb.convert('RGBA'), vignette).convert('RGB')

    # 9. Very slight contrast boost
    garment_final = ImageEnhance.Contrast(garment_final).enhance(1.08)

    path = os.path.join(OUTPUT, filename)
    garment_final.save(path, 'JPEG', quality=95)
    print(f"  ✓  {filename}")

# ──────────────────────────────────────────────────────────────────
print(f"\nGenerating 24 product images — STILL\n{'─'*52}")

make(hat_sixpanel, 'graphite', "six-panel-graphite.jpg")
make(hat_wool,     'graphite', "wool-cap-graphite.jpg")
make(hat_bucket,   'chalk',    "bucket-chalk.jpg")

make(hoodie,     'graphite', "foundation-hoodie-graphite.jpg")
make(hoodie,     'graphite', "the-zip-graphite.jpg", full_zip=True)

make(oxford_shirt, 'chalk',    "the-oxford-chalk.jpg")
make(overshirt,    'sand',     "the-overshirt-sand.jpg")
make(polo,         'chalk',    "foundation-polo-chalk.jpg")

make(long_sleeve, 'chalk',    "ls-foundation-chalk.jpg")
make(long_sleeve, 'graphite', "merino-ls-graphite.jpg", slim=True)

make(tee, 'chalk',    "foundation-tee-chalk.jpg",    extended=True)
make(tee, 'graphite', "fitted-tee-graphite.jpg",     fitted=True)
make(tee, 'graphite', "heavyweight-tee-graphite.jpg", boxy=True)

make(track_pant, 'graphite', "foundation-track-graphite.jpg")
make(track_pant, 'graphite', "tech-track-graphite.jpg", tech=True)

make(shorts, 'chalk', "pull-on-short-chalk.jpg", inseam=162)
make(shorts, 'chalk', "terry-short-chalk.jpg",   inseam=148)
make(shorts, 'chalk', "linen-short-chalk.jpg",   inseam=172, linen=True)

make(trouser, 'graphite', "five-pocket-graphite.jpg",  style='five_pocket')
make(trouser, 'chalk',    "tapered-chino-chalk.jpg",   style='chino')
make(trouser, 'chalk',    "wide-leg-chalk.jpg",         style='wide')

make(sock_crew,   'graphite', "crew-sock-graphite.jpg")
make(sock_noshow, 'chalk',    "no-show-chalk.jpg")
make(sock_crew,   'graphite', "merino-crew-sock-graphite.jpg")

print(f"\n{'─'*52}\nAll done.\n")
