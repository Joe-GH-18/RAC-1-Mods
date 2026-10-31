"""The camera keeps both players in the picture (the user: "make it so the camera tries to keep both
players in the camera ... by moving the camera to the middle position of both and zooming a bit out").

The game's camera is left to do what it does; at the HUD hook, after its update (0x53550 runs
before the HUD's 0xd56d8 in the frame update 0x166fb0), coop_cam moves its place (CAMERA_STATE
+0x140) by an offset of its own and keeps the game's place (C_CAM_KEPT). The view's direction is
not touched (the rows at +0x350: view axis, left, up). The place written there is the one the
picture is drawn from (Golden Clank's VIEW does the same). Before the next frame's hero and camera
(coop_frame), coop_cam_restore puts the game's place back, so the game's camera never starts from
the moved one; a HUD hook that comes again with the place still where coop_cam put it (no camera
update between, as in a pause) does the same first.

The offset: with Clank out (popping off, flying, docking) or the mini Giant Clank walking, d =
Player 2's place - Ratchet's; the camera goes T_CAM_SHARE of d toward him (the middle at 0.5), at
most T_CAM_SHIFT_MAX, and back along its view axis by T_CAM_ZOOM per unit of |d| beyond
T_CAM_ZOOM_FROM, at most T_CAM_ZOOM_MAX. The offset eases toward that by T_CAM_EASE a frame (and
back to none with Clank on Ratchet's back, as Giant Clank or Clank himself, with AI Clank
flying (the user: "only if player 2 actually plays ... if it is just the AI, dont do it"), or
T_CAM_ON 0); in the game's scenes it is dropped at once.

Walls (seen on Novalis: Clank flown left put the camera into a rock face, toward the camera into
the ship behind it): the offset is tried whole, then a half, a quarter, and none, with the game's
ray (MINI_RAY with T_CAM_RAY_FLAGS, coop_cam_ray) from the game's place to the moved one, and from the moved one to
Ratchet's chest (T_CAM_LOOK_UP over his feet) and to Player 2 (flown left, the camera had slid
behind a rock that hid Clank); the first that meets nothing is taken. The first ray goes T_CAM_MARGIN beyond the moved place:
stopped just short of the ship's nose, the camera still had it filling the picture. Cut back
like that, the offset eases at T_CAM_EASE_IN, faster, so it does not stay in the wall.
"""
from ..game import *  # noqa: F401,F403

CODE = r"""
coop_cam_restore:                   # (r29) the game's own camera place back before its update; uses r9..r11
    lwz 10, {C_CAM_ON}(29)
    cmpwi 10, 0
    beqlr
    li 10, 0
    stw 10, {C_CAM_ON}(29)
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lwz 10, 0x140(9)                # (moved by the game since: its own already)
    lwz 11, {C_CAM_APPLIED}(29)
    cmpw 10, 11
    bnelr
    lwz 10, {C_CAM_KEPT}(29)
    stw 10, 0x140(9)
    lwz 10, {C_CAM_KEPT} + 4(29)
    stw 10, 0x144(9)
    lwz 10, {C_CAM_KEPT} + 8(29)
    stw 10, 0x148(9)
    blr

coop_cam_ray:                       # (r29; r6 a moby left out) the game's ray C_RAY_FROM -> C_RAY_TO, T_CAM_RAY_FLAGS -> r3 not 0 on a hit
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 3, 29, {C_RAY_FROM}
    addi 4, 29, {C_RAY_TO}
    lwz 5, {T_CAM_RAY_FLAGS}(29)
    li 7, 0
    bl {MINI_RAY}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_cam:                           # (r29/r30, at the HUD hook) the camera toward Player 2 and back
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl coop_cam_restore             # (no camera update since the last: from the game's place again)
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lwz 10, 0x140(9)                # the game's place, kept
    stw 10, {C_CAM_KEPT}(29)
    lwz 10, 0x144(9)
    stw 10, {C_CAM_KEPT} + 4(29)
    lwz 10, 0x148(9)
    stw 10, {C_CAM_KEPT} + 8(29)
    lfs 1, {T_ZERO}(29)             # f1..f3: the offset wanted
    fmr 2, 1
    fmr 3, 1
    lfs 0, {T_CAM_EASE}(29)
    stfs 0, {C_CAM_RATE}(29)
    lis 10, {SCENE_FLAG_HA}
    lwz 10, {SCENE_FLAG_LO}(10)
    cmpwi 10, 0
    bne ccm_scene
    lwz 10, {T_CAM_ON}(29)
    cmpwi 10, 0
    beq ccm_ease
    lwz 10, {C_DRIVER}(29)          # a player's Clank only, not the AI's
    cmpwi 10, {DRIVER_P2}
    bne ccm_ease
    lbz 10, {HERO_KIND}(30)         # Ratchet only
    cmpwi 10, 0
    bne ccm_ease
    lwz 10, {C_MODE}(29)
    addi 11, 29, {C_POS}
    lwz 12, {C_BODY}(29)            # (r12: his moby, left out of the ray to him)
    cmpwi 10, {MODE_POP}
    beq ccm_target
    cmpwi 10, {MODE_FLY}
    beq ccm_target
    cmpwi 10, {MODE_DOCKING}
    beq ccm_target
    addi 11, 29, {C_MINI_POS}
    lwz 12, {C_MINI}(29)
    cmpwi 10, {MODE_MINI}
    bne ccm_ease
ccm_target:
    stw 11, {C_CAM_P2}(29)
    stw 12, {C_CAM_P2_MOBY}(29)
    lfs 4, 0(11)                    # d = Player 2 - Ratchet (f4..f6), |d| (f7)
    lfs 0, 0x80(30)
    fsubs 4, 4, 0
    lfs 5, 4(11)
    lfs 0, 0x84(30)
    fsubs 5, 5, 0
    lfs 6, 8(11)
    lfs 0, 0x88(30)
    fsubs 6, 6, 0
    fmuls 7, 4, 4
    fmadds 7, 5, 5, 7
    fmadds 7, 6, 6, 7
    fsqrts 7, 7
    lfs 0, {T_CAM_SHARE}(29)        # toward him, at most T_CAM_SHIFT_MAX
    fmuls 1, 4, 0
    fmuls 2, 5, 0
    fmuls 3, 6, 0
    fmuls 8, 7, 0
    lfs 0, {T_CAM_SHIFT_MAX}(29)
    fcmpu 0, 8, 0
    ble ccm_pull
    fdivs 0, 0, 8
    fmuls 1, 1, 0
    fmuls 2, 2, 0
    fmuls 3, 3, 0
ccm_pull:
    lfs 0, {T_CAM_ZOOM_FROM}(29)    # and back along the view axis
    fsubs 8, 7, 0
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 8, 0
    ble ccm_walls
    lfs 0, {T_CAM_ZOOM}(29)
    fmuls 8, 8, 0
    lfs 0, {T_CAM_ZOOM_MAX}(29)
    fcmpu 0, 8, 0
    ble ccm_back
    fmr 8, 0
ccm_back:
    lfs 0, 0x350(9)
    fnmsubs 1, 8, 0, 1
    lfs 0, 0x354(9)
    fnmsubs 2, 8, 0, 2
    lfs 0, 0x358(9)
    fnmsubs 3, 8, 0, 3
ccm_walls:
    stfs 1, {C_CAM_WANT}(29)        # whole, a half, a quarter: the first the rays let through
    stfs 2, {C_CAM_WANT} + 4(29)
    stfs 3, {C_CAM_WANT} + 8(29)
    li 10, 3
    stw 10, {C_CAM_TRIES}(29)
ccm_try:
    lfs 1, {C_CAM_WANT}(29)         # the game's place -> the moved one and T_CAM_MARGIN on (a ray is
    lfs 2, {C_CAM_WANT} + 4(29)     # thin; the camera stopped beside the ship's nose had it in the picture)
    lfs 3, {C_CAM_WANT} + 8(29)
    fmuls 5, 1, 1
    fmadds 5, 2, 2, 5
    fmadds 5, 3, 3, 5
    fsqrts 5, 5
    lfs 6, {T_ONE}(29)
    lfs 0, {T_CAM_TINY}(29)
    fcmpu 0, 5, 0
    blt ccm_margin
    lfs 0, {T_CAM_MARGIN}(29)
    fadds 6, 5, 0
    fdivs 6, 6, 5
ccm_margin:
    lfs 4, {C_CAM_KEPT}(29)
    stfs 4, {C_RAY_FROM}(29)
    fadds 0, 4, 1
    stfs 0, {C_CAM_AT}(29)
    fmadds 4, 1, 6, 4
    stfs 4, {C_RAY_TO}(29)
    lfs 4, {C_CAM_KEPT} + 4(29)
    stfs 4, {C_RAY_FROM} + 4(29)
    fadds 0, 4, 2
    stfs 0, {C_CAM_AT} + 4(29)
    fmadds 4, 2, 6, 4
    stfs 4, {C_RAY_TO} + 4(29)
    lfs 4, {C_CAM_KEPT} + 8(29)
    stfs 4, {C_RAY_FROM} + 8(29)
    fadds 0, 4, 3
    stfs 0, {C_CAM_AT} + 8(29)
    fmadds 4, 3, 6, 4
    stfs 4, {C_RAY_TO} + 8(29)
    lwz 6, {C_BODY}(29)
    bl coop_cam_ray
    cmpwi 3, 0
    bne ccm_cut
    lwz 10, {C_CAM_AT}(29)          # the moved one -> Ratchet's chest
    stw 10, {C_RAY_FROM}(29)
    lwz 10, {C_CAM_AT} + 4(29)
    stw 10, {C_RAY_FROM} + 4(29)
    lwz 10, {C_CAM_AT} + 8(29)
    stw 10, {C_RAY_FROM} + 8(29)
    lwz 10, 0x80(30)
    stw 10, {C_RAY_TO}(29)
    lwz 10, 0x84(30)
    stw 10, {C_RAY_TO} + 4(29)
    lfs 4, 0x88(30)
    lfs 0, {T_CAM_LOOK_UP}(29)
    fadds 4, 4, 0
    stfs 4, {C_RAY_TO} + 8(29)
    lwz 6, 0x2080(30)              # (Ratchet's moby left out)
    bl coop_cam_ray
    cmpwi 3, 0
    bne ccm_cut
    lwz 10, {C_CAM_P2}(29)          # and the moved one -> Player 2
    lwz 11, 0(10)
    stw 11, {C_RAY_TO}(29)
    lwz 11, 4(10)
    stw 11, {C_RAY_TO} + 4(29)
    lwz 11, 8(10)
    stw 11, {C_RAY_TO} + 8(29)
    lwz 6, {C_CAM_P2_MOBY}(29)      # (his own moby left out)
    bl coop_cam_ray
    cmpwi 3, 0
    beq ccm_clear
ccm_cut:
    lfs 0, {T_CAM_EASE_IN}(29)      # blocked: half of it, eased in faster
    stfs 0, {C_CAM_RATE}(29)
    lfs 0, {T_HALF}(29)
    lfs 1, {C_CAM_WANT}(29)
    fmuls 1, 1, 0
    stfs 1, {C_CAM_WANT}(29)
    lfs 1, {C_CAM_WANT} + 4(29)
    fmuls 1, 1, 0
    stfs 1, {C_CAM_WANT} + 4(29)
    lfs 1, {C_CAM_WANT} + 8(29)
    fmuls 1, 1, 0
    stfs 1, {C_CAM_WANT} + 8(29)
    lwz 10, {C_CAM_TRIES}(29)
    addic. 10, 10, -1
    stw 10, {C_CAM_TRIES}(29)
    bne ccm_try
    lfs 1, {T_ZERO}(29)             # none gets through: none
    fmr 2, 1
    fmr 3, 1
    b ccm_eased
ccm_clear:
    lfs 1, {C_CAM_WANT}(29)
    lfs 2, {C_CAM_WANT} + 4(29)
    lfs 3, {C_CAM_WANT} + 8(29)
    b ccm_eased
ccm_ease:
ccm_eased:
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 0, {C_CAM_RATE}(29)
    lfs 4, {C_CAM_OFF}(29)
    fsubs 5, 1, 4
    fmadds 4, 5, 0, 4
    stfs 4, {C_CAM_OFF}(29)
    lfs 5, {C_CAM_KEPT}(29)
    fadds 5, 5, 4
    stfs 5, 0x140(9)
    lfs 4, {C_CAM_OFF} + 4(29)
    fsubs 5, 2, 4
    fmadds 4, 5, 0, 4
    stfs 4, {C_CAM_OFF} + 4(29)
    lfs 5, {C_CAM_KEPT} + 4(29)
    fadds 5, 5, 4
    stfs 5, 0x144(9)
    lfs 4, {C_CAM_OFF} + 8(29)
    fsubs 5, 3, 4
    fmadds 4, 5, 0, 4
    stfs 4, {C_CAM_OFF} + 8(29)
    lfs 5, {C_CAM_KEPT} + 8(29)
    fadds 5, 5, 4
    stfs 5, 0x148(9)
    lwz 10, 0x140(9)
    stw 10, {C_CAM_APPLIED}(29)
    li 10, 1
    stw 10, {C_CAM_ON}(29)
    b ccm_out
ccm_scene:                          # a scene: no offset, at once
    stfs 1, {C_CAM_OFF}(29)
    stfs 1, {C_CAM_OFF} + 4(29)
    stfs 1, {C_CAM_OFF} + 8(29)
ccm_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
"""
