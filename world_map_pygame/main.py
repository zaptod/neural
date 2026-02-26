"""
world_map_pygame/main.py
Ponto de entrada. A janela é criada com o tamanho real detectado em config.py.
"""
import sys, time
import pygame

# config.py já detectou SCREEN_W/SCREEN_H baseado na tela real
from .config        import SCREEN_W, SCREEN_H, FPS
from .data_loader   import load_data
from .terrain       import generate_heightmap, build_base_texture
from .territories   import build_territory_maps, extract_border_mask, zone_at_pixel, world_to_tex
from .camera        import Camera
from .renderer      import MapRenderer
from .ui            import UI
from .particles     import Particles


def run():
    pygame.init()

    # Cria janela exatamente no tamanho detectado pelo config.py
    # (SCREEN_W/SCREEN_H já respeitam o tamanho físico da tela)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Neural Fights — Aethermoor")
    clock = pygame.time.Clock()

    ui = UI()

    # ── Loading ────────────────────────────────────────────────────────────
    ui.draw_loading(screen, "Carregando dados do mundo...", 0.05)
    zones, gods, ownership, ancient_seals, global_stats = load_data()
    print(f"[map] {len(zones)} zonas · {len(gods)} deuses · "
          f"janela {SCREEN_W}×{SCREEN_H}")

    ui.draw_loading(screen, "Gerando heightmap procedural (fBm)...", 0.20)
    heightmap = generate_heightmap()

    ui.draw_loading(screen, "Computando territórios (Voronoi warp)...", 0.45)
    zone_idx, zone_list = build_territory_maps(zones)

    ui.draw_loading(screen, "Extraindo fronteiras...", 0.62)
    border_mask = extract_border_mask(zone_idx)

    ui.draw_loading(screen, "Renderizando textura cartográfica...", 0.75)
    img_u8   = build_base_texture(heightmap, border_mask)
    map_surf = pygame.Surface((img_u8.shape[1], img_u8.shape[0]))
    pygame.surfarray.blit_array(map_surf, img_u8.swapaxes(0, 1))

    ui.draw_loading(screen, "Inicializando câmera...", 0.92)
    cam  = Camera(map_x=ui.map_x, map_w=ui.map_w)
    rend = MapRenderer(map_surf, zone_idx, zone_list, zones, gods, cam)
    part = Particles()

    ui.draw_loading(screen, "Pronto!", 1.0)
    pygame.time.wait(300)

    selected_zone = None
    hover_zone    = None
    t_anim        = 0.0
    last_click_t  = 0.0
    last_click_z  = None
    intro_alpha   = 255

    running = True
    while running:
        dt     = clock.tick(FPS) / 1000.0
        t_anim += dt
        fps    = clock.get_fps()

        cam.map_x = ui.map_x
        cam.map_w = ui.map_w

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key in (pygame.K_h, pygame.K_HOME):
                    cam.fly_home()
                    selected_zone = None
                    ui.notify("Visão Global")
                elif ev.key == pygame.K_r:
                    ui.draw_loading(screen, "Recarregando dados...", 0.5)
                    zones, gods, ownership, ancient_seals, global_stats = load_data()
                    rend.zones = zones
                    rend.gods  = gods
                    ui.notify("Dados recarregados ✓")

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                on_panel = mx < ui.panel_w
                on_map   = mx >= ui.map_x and my >= ui.map_y

                if on_panel:
                    if ev.button == 4:
                        ui.scroll_panel(-32)
                    elif ev.button == 5:
                        ui.scroll_panel(32)

                elif on_map:
                    if ev.button == 1:
                        wx, wy = cam.s2w(mx, my)
                        tx, ty = world_to_tex(wx, wy)
                        z   = zone_at_pixel(zone_idx, zone_list, tx, ty)
                        now = time.time()
                        if z and z == last_click_z and now - last_click_t < 0.35:
                            cam.fly_to(*z.centroid)
                            ui.notify(f"✈  {z.zone_name}")
                        else:
                            selected_zone = z
                            if z:
                                ui.notify(z.zone_name)
                                sx, sy = cam.w2s(*z.centroid)
                                part.emit(sx, sy, (255, 220, 60), n=22)
                        last_click_z = z
                        last_click_t = now
                        cam.start_drag(mx, my)

                    elif ev.button == 3:
                        selected_zone = None

                    elif ev.button == 4:
                        cam.zoom_at(mx, my, Camera.ZOOM_STEP)
                    elif ev.button == 5:
                        cam.zoom_at(mx, my, 1 / Camera.ZOOM_STEP)

            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1:
                    cam.end_drag()

            elif ev.type == pygame.MOUSEMOTION:
                mx, my = ev.pos
                if cam.dragging:
                    cam.update_drag(mx, my)
                if mx >= ui.map_x and my >= ui.map_y:
                    wx, wy = cam.s2w(mx, my)
                    tx, ty = world_to_tex(wx, wy)
                    hover_zone = zone_at_pixel(zone_idx, zone_list, tx, ty)
                else:
                    hover_zone = None

            elif ev.type == pygame.MOUSEWHEEL:
                mx2, my2 = pygame.mouse.get_pos()
                if mx2 >= ui.map_x and my2 >= ui.map_y:
                    f = Camera.ZOOM_STEP if ev.y > 0 else 1 / Camera.ZOOM_STEP
                    cam.zoom_at(mx2, my2, f)

        # WASD
        keys = pygame.key.get_pressed()
        spd  = 600 * dt / max(cam.zoom, 0.1)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  cam.offset_x -= spd
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: cam.offset_x += spd
        if keys[pygame.K_w] or keys[pygame.K_UP]:    cam.offset_y -= spd
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  cam.offset_y += spd

        cam.update()
        part.update(dt)
        ui.update(dt)

        # ── Render ─────────────────────────────────────────────────────────
        screen.fill((6, 12, 28))

        # 1. Mapa (clipado à área do mapa)
        rend.draw(screen, ownership, selected_zone, hover_zone,
                  ancient_seals, t_anim, ui.map_x, ui.map_w)

        # 2. UI sobre o mapa — ordem: painel, HUD, extras
        ui.draw_left_panel(screen, gods, zones, ownership,
                           selected_zone, ancient_seals, global_stats)
        ui.draw_top_hud(screen, gods, zones, ownership, cam, fps, t_anim)
        ui.draw_seals_panel(screen, zones, ancient_seals, t_anim)
        part.draw(screen)
        mx_cur, my_cur = pygame.mouse.get_pos()
        ui.draw_hover_tooltip(screen, hover_zone, gods, ownership,
                              ancient_seals, mx_cur, my_cur)
        ui.draw_notif(screen)
        ui.draw_corners(screen)

        # 3. Intro fade
        if intro_alpha > 0:
            fade = pygame.Surface((SCREEN_W, SCREEN_H))
            fade.fill((0, 0, 0))
            fade.set_alpha(max(0, intro_alpha))
            screen.blit(fade, (0, 0))
            intro_alpha = max(0, intro_alpha - 3)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
