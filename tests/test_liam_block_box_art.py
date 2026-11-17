"""Native box structure, per-piece contents and camera-correct carry ownership."""
import ast
import gc
import json
import os
from pathlib import Path
import unittest

os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from PIL import Image
import pygame
from tools import liam_block_art as art

ROOT=Path(__file__).resolve().parents[1]
PACK=json.loads((ROOT/'assets/terrain/eldenmere/liam_home/blocks/blocks.json').read_text())
ROOM=json.loads((ROOT/'assets/maps/eldenmere/building_interiors/rooms/liam_house/map.json').read_text())


class LiamBlockArtTests(unittest.TestCase):
    def test_native_contents_use_one_stationary_orthogonal_structure(self):
        empty,base=art.layers(0);front=base['front'];shell=base['back']
        self.assertEqual(empty.size,(64,48))
        self.assertEqual(front.getbbox(),(4,31,60,45))
        self.assertEqual(len({art.layers(mask)[0].tobytes() for mask in range(32)}),32)
        for mask in range(32):
            im,layers=art.layers(mask)
            self.assertEqual(layers['front'].tobytes(),front.tobytes())
            self.assertEqual(layers['back'].tobytes(),shell.tobytes())
            self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
            # Literal near-face extraction: repainting it cannot change a box.
            repainted=im.copy();repainted.alpha_composite(front)
            self.assertEqual(repainted.tobytes(),im.tobytes())
            self.assertEqual(im.getbbox(),empty.getbbox())
            # Horizontal rear/front rims, parallel side walls, no vanishing point.
            self.assertEqual(im.getpixel((4,10)),im.getpixel((59,10)))

    def test_live_aliases_share_the_exact_drawings_not_retained_toy_icons(self):
        entity=next(e for e in ROOM['entities'] if e['id']=='liam_block_box')
        self.assertEqual(entity['position'],PACK['box_position'])
        self.assertEqual(entity['logical_size'],[32,24])
        self.assertEqual(entity['sort_y'],203)
        self.assertEqual(entity['artwork_pixels_per_world_pixel'],2)
        for mask in range(32):
            actual=Image.open(ROOT/entity['state_images'][f'contents_{mask:02d}']).convert('RGBA')
            self.assertEqual(actual.tobytes(),art.layers(mask)[0].tobytes())
        for index,spec in enumerate(PACK['blocks']):
            alias=ROOM['art_replacements'][spec['image']]
            self.assertEqual(alias['logical_size'],spec['frame_size'])
            self.assertEqual(Image.open(ROOT/alias['file']).convert('RGBA').tobytes(),art.block(index).tobytes())
        alias=ROOM['art_replacements'][PACK['front_overlay']]
        self.assertEqual(Image.open(ROOT/alias['file']).convert('RGBA').tobytes(),art.structure()[1].tobytes())
        self.assertEqual(Image.open(ROOT/entity['frames'][0]).convert('RGBA').tobytes(),art.layers(31)[0].tobytes())

    def test_unrelated_room_gameplay_and_adult_paths_are_preserved(self):
        baseline=json.loads((ROOT/'assets/source/maps/eldenmere/town_hd/baseline_maps.json').read_text())['liam_house']
        self.assertEqual(ROOM['npcs'],baseline['npcs'])
        self.assertEqual(ROOM['size_pixels'],baseline['size_pixels'])
        for key in ('block_centers','scatter_centers','dog_contact_station','idle_position'):
            # Authoritative routine goals remain the pre-audit exact coordinates.
            self.assertIn(key,json.loads((ROOT/'assets/maps/eldenmere/routines/liam_blocks.json').read_text()))
        # This presentation-only change does not introduce persistence fields.
        node=ast.parse((ROOT/'liam_blocks.py').read_text())
        self.assertFalse(any(isinstance(n,ast.FunctionDef) and n.name in ('save','serialize') for n in ast.walk(node)))

    def test_runtime_exact_identities_cues_focus_and_interrupted_cleanup(self):
        from main import Game
        game=Game(fullscreen=False,start_on_title=False,save_path=None)
        try:
            r=game.block_routines[0];game.world=r.home;game.player.position.update(230,300)
            r.shared.cooldown_ms=999999;r.daisy.duration_ms=999999
            r.daisy.cooldowns={'food':999999,'water':999999}
            r.begin(accident=False,forget=False)
            seen=set()
            def tick():
                old=[b['state'] for b in r.blocks]
                game.update(1/60,(0,0),False)
                mask=sum(1 << i for i,b in enumerate(r.blocks) if b['state']=='box')
                self.assertEqual(r.box['state'],f'contents_{mask:02d}')
                self.assertLessEqual(sum(b['state']=='held' for b in r.blocks),1)
                self.assertEqual({b['id'] for b in r.blocks},{f'block_{i}' for i in range(1,6)})
                for before,b in zip(old,r.blocks):
                    if before!=b['state']:
                        seen.add((before,b['state']))
                        self.assertEqual(r._frame()[0],2)
            for _ in range(2000):
                tick()
                if r.held is not None:break
            else:self.fail(r.state)
            snapshot=(r.state,r.state_ms,r.liam.position.copy(),r.box['state'])
            game._music_focused=False;game.update(.5,(1,0),True)
            self.assertEqual((r.state,r.state_ms,r.liam.position,r.box['state']),snapshot)
            game._music_focused=True
            game.pause.open();game.update(.5,(1,0),True)
            self.assertEqual((r.state,r.state_ms,r.liam.position,r.box['state']),snapshot)
            game.pause.close()
            # Explicit facing is published before each reach, not inherited from
            # the final waypoint's travel direction.
            self.assertEqual(r.liam.facing,'left')
            r.request_release()
            for _ in range(6000):
                tick()
                if not r.active:break
            else:self.fail(r.state)
            self.assertIn(('box','held'),seen);self.assertIn(('held','box'),seen)
            self.assertTrue(all(b['state']=='box' for b in r.blocks))
            self.assertIsNone(r.held);self.assertIsNone(r.liam.work_renderer)
            self.assertIsNone(r.shared.liam_owner)
            self.assertEqual(r.box['state'],'contents_31')
            # Existing Continue/New Game staging resets one conserved set.
            r.reset_for_story()
            self.assertEqual(len(r.blocks),5);self.assertEqual(r.box['state'],'contents_31')
        finally:
            game.music.stop();pygame.quit();del game;gc.collect()


if __name__=='__main__':unittest.main()
