"""Logical geometry and full-scene native detail are independent contracts."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
import unittest
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import pygame
import rendering as r


class RenderingTests(unittest.TestCase):
    def setUp(self):r.clear_cache()

    def pattern(self):
        image=pygame.Surface((4,4),pygame.SRCALPHA);image.fill('red')
        image.set_at((1,0),'blue');image.set_at((2,3),'yellow')
        return image

    def test_aerial_projection_uses_declared_density_without_changing_world_matrix(self):
        import numpy as np
        from regent_aerial import RegentAerial
        aerial=RegentAerial(None)
        image=pygame.Surface((960,640));image.fill('red');image.set_at((1,0),'blue')
        plane={'pixels':pygame.surfarray.array3d(image),'artwork_pixels_per_world_pixel':2}
        matrix=np.diag((.5,.5,1.))
        high=aerial._warp(plane,matrix)
        self.assertIsInstance(high,r.WorldCanvas)
        self.assertEqual(high.native.get_at((1,0)),pygame.Color('blue'))
        plane['artwork_pixels_per_world_pixel']=1
        legacy=aerial._warp(plane,matrix)
        self.assertNotIsInstance(legacy,r.WorldCanvas)
        scene=r.WorldCanvas((480,320));scene.blit(legacy,(0,0))
        self.assertEqual(scene.native.get_at((1,0)),pygame.Color('red'))

    def test_cinematic_background_density_selects_shader_grid_and_cache(self):
        import numpy as np
        from ice_reaper_action import IceReaperActionStage,PerspectiveCamera
        stage=IceReaperActionStage.__new__(IceReaperActionStage)
        stage._background_cache={};stage.panorama=True;stage.ground_texture=None
        stage._screen_x=np.arange(8,dtype=np.float32)[:,None]
        stage._screen_y=np.arange(8,dtype=np.float32)[None,:]
        stage.world_landmarks=lambda:()
        grids=[]
        def sky(canvas,camera):
            grids.append(stage._screen_x.shape[0])
            canvas.fill('red');canvas.set_at((1,0),'blue')
        stage._panoramic_sky_pixels=sky
        camera=PerspectiveCamera((0,2,4),(0,0,0))
        stage.environment_density=1;scene=r.WorldCanvas((8,8))
        stage._background(scene,camera,0)
        self.assertEqual(scene.native.get_at((2,0)),pygame.Color('blue'))
        stage.environment_density=2;stage._background(scene,camera,0)
        self.assertEqual(scene.native.get_at((1,0)),pygame.Color('blue'))
        self.assertEqual(grids,[8,16])

    def test_artwork_preserves_every_texel_and_logical_footprint(self):
        source=self.pattern();before=pygame.image.tobytes(source,'RGBA')
        art=r.record_art(source,{'artwork_pixels_per_world_pixel':2,'logical_size':[2,2]})
        self.assertEqual(art.get_size(),(2,2))
        scene=r.WorldCanvas((8,8),pygame.SRCALPHA);scene.fill('black');scene.blit(art,(2,3))
        self.assertEqual(pygame.image.tobytes(scene.native.subsurface((4,6,4,4)),'RGBA'),before)
        self.assertEqual(pygame.image.tobytes(source,'RGBA'),before)
        for density,size in [(0,None),(True,None),(3,None),(2,[4,4])]:
            with self.subTest(density=density,size=size),self.assertRaises(ValueError):
                r.artwork(source,density,size)
        with self.assertRaises(ValueError):r.artwork(pygame.Surface((3,4)),2)

    def test_subpixel_silhouette_has_conservative_logical_bounds(self):
        source=pygame.Surface((4,4),pygame.SRCALPHA);source.set_at((1,1),'red')
        art=r.artwork(source,2)
        self.assertEqual(art.get_bounding_rect(),pygame.Rect(0,0,1,1))

    def test_fractional_anchor_and_negative_crop_preserve_detail(self):
        scene=r.WorldCanvas((4,4));scene.fill('black')
        scene.blit(r.artwork(self.pattern(),2),(.5,.5))
        self.assertEqual(scene.native.get_at((2,1)),pygame.Color('blue'))
        scene.fill('black');scene.blit(r.artwork(self.pattern(),2),(-1,0))
        self.assertEqual(scene.native.get_at((0,3)),pygame.Color('yellow'))
        scene.fill('black');scene.blit(r.artwork(self.pattern(),2),(3.5,0))
        self.assertEqual(scene.native.get_at((7,0)),pygame.Color('red'))

    def test_depth_and_transparency_apply_once_over_overlapping_art(self):
        scene=r.WorldCanvas((4,4));scene.fill('black');art=r.artwork(self.pattern(),2)
        scene.blit(art,(0,0));scene.blit(art,(0,0))
        foreground=pygame.Surface((2,2),pygame.SRCALPHA);foreground.fill((0,255,0,128))
        scene.blit(foreground,(0,0))
        expected=self.pattern();expected.blit(pygame.transform.scale(foreground,(4,4)),(0,0))
        self.assertEqual(pygame.image.tobytes(scene.native.subsurface((0,0,4,4)),'RGB'),pygame.image.tobytes(expected,'RGB'))

    def test_primitives_clipping_and_shared_subsurface_update_both_buffers(self):
        scene=r.WorldCanvas((5,5));scene.fill('black');scene.set_clip((1,1,2,2))
        r.draw.rect(scene,'green',(0,0,5,5))
        self.assertEqual(scene.native.get_at((0,0)),pygame.Color('black'))
        self.assertEqual(scene.native.get_at((2,2)),pygame.Color('green'))
        scene.set_clip(None);sub=scene.subsurface((3,3,2,2));sub.fill('blue')
        self.assertEqual(scene.native.get_at((6,6)),pygame.Color('blue'))
        self.assertEqual(scene.get_at((3,3)),pygame.Color('blue'))
        scene.fill('black');r.draw.rect(scene,'red',(.5,.5,1.,1.))
        self.assertEqual(scene.native.get_at((1,1)),pygame.Color('red'))
        self.assertEqual(scene.native.get_at((0,0)),pygame.Color('black'))

    def test_scaled_and_flipped_intermediates_retain_native_detail(self):
        art=r.artwork(self.pattern(),2);flipped=r.flip(art,True,False)
        expected=pygame.transform.flip(self.pattern(),True,False)
        self.assertEqual(pygame.image.tobytes(flipped.native,'RGBA'),pygame.image.tobytes(expected,'RGBA'))
        scaled=r.scale(flipped,(4,4));self.assertEqual(scaled.native.get_size(),(8,8))
        target=pygame.Surface((8,8));r.present(scaled,target)
        self.assertEqual(pygame.image.tobytes(target,'RGB'),pygame.image.tobytes(pygame.transform.scale(expected,(8,8)),'RGB'))

    def test_snapshots_are_complete_plain_independent_frames(self):
        scene=r.WorldCanvas((4,4));scene.fill('black');scene.blit_art(self.pattern(),(1,1))
        frozen=r.snapshot(scene);self.assertNotIsInstance(frozen,r.WorldCanvas)
        self.assertEqual(frozen.get_size(),(8,8));scene.fill('green')
        self.assertEqual(frozen.get_at((3,2)),pygame.Color('blue'))
        copy=scene.copy();scene.fill('red')
        self.assertEqual(copy.native.get_at((0,0)),pygame.Color('green'))

    def test_battle_transition_keeps_native_detail_after_source_changes(self):
        from battle_transition import BattleTransition
        source=r.WorldCanvas((4,4));source.fill('black');source.blit_art(self.pattern(),(1,1))
        transition=BattleTransition(source);source.fill('green')
        target=r.WorldCanvas((4,4));transition.draw(target)
        self.assertEqual(target.native.get_at((3,2)),pygame.Color('blue'))

    def test_mutable_layers_are_not_cached_and_immutable_cache_is_byte_bounded(self):
        with patch.object(r,'CACHE_BYTES',1024):
            scene=r.WorldCanvas((8,8));scene.fill('black')
            for i in range(12):
                art=pygame.Surface((4,4));art.fill((i,0,0));r.immutable(art)
                scene.blit(art,(0,0))
                self.assertLessEqual(r.cache_info()['bytes'],1024)
            dynamic=pygame.Surface((2,2));dynamic.fill('blue');scene.blit(dynamic,(0,0))
            dynamic.fill('yellow');scene.blit(dynamic,(0,0))
            self.assertEqual(scene.native.get_at((0,0)),pygame.Color('yellow'))

    def test_large_grounds_are_cropped_before_scaling(self):
        scene=r.WorldCanvas((8,8));ground=r.immutable(pygame.Surface((1024,1024)))
        ground.fill('blue');scene.blit(ground,(-500,-500))
        self.assertEqual(scene.native.get_at((0,0)),pygame.Color('blue'))
        self.assertEqual(r.cache_info()['bytes'],0)

    def test_projected_sources_and_ui_images_bypass_logical_downsampling(self):
        source=pygame.Surface((8,8))
        for x in range(8):source.fill((x*31,0,0),(x,0,1,8))
        projected=r.project_art(source,(3,3))
        expected=pygame.transform.scale(source,(6,6))
        self.assertEqual(pygame.image.tobytes(projected.native,'RGB'),pygame.image.tobytes(expected,'RGB'))
        flattened=pygame.transform.scale(projected,(6,6))
        self.assertNotEqual(pygame.image.tobytes(flattened,'RGB'),pygame.image.tobytes(expected,'RGB'))
        self.assertEqual(pygame.image.tobytes(r.display_image(projected,(6,6)),'RGB'),pygame.image.tobytes(expected,'RGB'))

    def test_projected_cache_counts_both_buffers_and_rejects_oversized_frames(self):
        cache=r.SurfaceCache(128)
        for i in range(3):cache[i]=r.WorldCanvas((2,2))
        self.assertEqual(len(cache),1);self.assertLessEqual(cache.bytes,128)
        cache['large']=r.WorldCanvas((8,8))
        self.assertIsNone(cache.get('large'));self.assertLessEqual(cache.bytes,128)
        cache.clear();self.assertEqual(cache.bytes,0)

    def test_plain_surface_helpers_keep_ordinary_pygame_semantics(self):
        source=self.pattern();out=pygame.Surface((8,8),pygame.SRCALPHA)
        self.assertIs(r.scale(source,(8,8),out),out)
        self.assertEqual(pygame.image.tobytes(out,'RGBA'),pygame.image.tobytes(pygame.transform.scale(source,(8,8)),'RGBA'))


class WorldDensityTests(unittest.TestCase):
    def test_native_ground_entity_player_and_logical_collision_share_one_world(self):
        from main import World
        pygame.display.init();pygame.display.set_mode((48,48))
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            ground=pygame.Surface((48,48));ground.fill('black');ground.set_at((1,0),'blue')
            art=pygame.Surface((4,4),pygame.SRCALPHA);art.fill('red');art.set_at((1,0),'yellow')
            collision=pygame.Surface((24,24));collision.fill('black')
            for name,image in [('ground',ground),('art',art),('collision',collision)]:pygame.image.save(image,str(folder/(name+'.png')))
            record={'id':'density-fixture','size_pixels':[24,24],
                    'ground_frames':[str(folder/'ground.png')],'ground_frame_duration_ms':200,
                    'artwork_pixels_per_world_pixel':2,'collision':str(folder/'collision.png'),
                    'player_probe_size':[2,2],'player_draw_anchor':[0,0],
                    'overview':str(folder/'collision.png'),'doors':[],'foreground':[],
                    'entities':[{'id':'prop','frames':[str(folder/'art.png')],'position':[3,4],
                                 'sort_y':4,'frame_duration_ms':100,'phase_offset':0}]}
            manifest=folder/'map.json';manifest.write_text(json.dumps(record));world=World(manifest)
            self.assertEqual(world.size,(24,24));self.assertEqual(world.blocked.get_size(),(24,24))
            self.assertEqual(world.entities[0]['rect'].size,(2,2))
            player=SimpleNamespace(story_visible=True,position=pygame.Vector2(8,8),
                                   sprite=lambda:r.artwork(art,2))
            canvas=r.WorldCanvas((24,24));world.draw(canvas,(0,0),player,0,False)
            self.assertEqual(canvas.native.get_at((1,0))[:3],(0,0,255))
            self.assertEqual(canvas.native.get_at((7,8))[:3],(255,255,0))
            self.assertEqual(canvas.native.get_at((17,16))[:3],(255,255,0))
        pygame.quit()
