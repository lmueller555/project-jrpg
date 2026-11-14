import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import unittest
import pygame
from dense_art import WorldCanvas


class DenseArtTests(unittest.TestCase):
    def test_detail_and_translucent_foreground_follow_depth(self):
        canvas=WorldCanvas((8,8));canvas.fill('black')
        art=pygame.Surface((4,4),pygame.SRCALPHA);art.fill('red')
        art.set_at((1,0),'blue')
        canvas.blit_art(art,(2,2))
        foreground=pygame.Surface((1,1),pygame.SRCALPHA);foreground.fill((0,255,0,128))
        canvas.blit(foreground,(2,2))
        target=pygame.transform.scale(canvas,(16,16));canvas.present_detail(target)
        expected=pygame.Surface((1,1));expected.fill('blue');expected.blit(foreground,(0,0))
        self.assertEqual(target.get_at((5,4)),expected.get_at((0,0)))
        self.assertEqual(target.get_at((4,6)),pygame.Color('red'))

    def test_overlapping_actors_do_not_duplicate_translucent_occluder(self):
        canvas=WorldCanvas((8,8));canvas.fill('black')
        art=pygame.Surface((6,6),pygame.SRCALPHA);art.fill('red')
        canvas.blit_art(art,(1,1));canvas.blit_art(art,(2,2))
        foreground=pygame.Surface((8,8),pygame.SRCALPHA);foreground.fill((0,255,0,128))
        canvas.blit(foreground,(0,0))
        target=pygame.transform.scale(canvas,(16,16));canvas.present_detail(target)
        self.assertEqual(target.get_at((5,5))[:3],(127,128,0))

    def test_frame_reset_and_clipped_blits(self):
        canvas=WorldCanvas((8,8));canvas.fill('black')
        art=pygame.Surface((4,4));art.fill('red');canvas.blit_art(art,(-1,0))
        cover=pygame.Surface((3,3));cover.fill('green')
        canvas.blit(cover,(-1,-1),pygame.Rect(0,0,3,3))
        target=pygame.transform.scale(canvas,(16,16));canvas.present_detail(target)
        self.assertEqual(target.get_at((0,0)),pygame.Color('green'))
        canvas.reset_detail();canvas.fill('blue')
        target=pygame.transform.scale(canvas,(16,16));canvas.present_detail(target)
        self.assertEqual(target.get_at((0,0)),pygame.Color('blue'))

    def test_ordinary_frames_unchanged(self):
        canvas=WorldCanvas((8,8));canvas.fill('black')
        image=pygame.Surface((3,3));image.fill('blue');canvas.blit(image,(2,2))
        expected=pygame.transform.scale(canvas,(24,24));actual=expected.copy()
        canvas.present_detail(actual)
        self.assertEqual(pygame.image.tobytes(actual,'RGB'),pygame.image.tobytes(expected,'RGB'))

    def test_direct_primitive_after_actor_remains_visible(self):
        canvas=WorldCanvas((8,8));canvas.fill('black')
        art=pygame.Surface((4,4));art.fill('red');canvas.blit_art(art,(2,2))
        pygame.draw.rect(canvas,'green',(2,2,1,1))
        target=pygame.transform.scale(canvas,(16,16));canvas.present_detail(target)
        self.assertEqual(target.get_at((4,4)),pygame.Color('green'))
        self.assertEqual(target.get_at((6,6)),pygame.Color('red'))
