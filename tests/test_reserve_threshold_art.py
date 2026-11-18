"""Stone threshold presentation remains independent of portal/collision ownership."""
import unittest
from PIL import Image,ImageChops
from tools.build_sanctuary_reserve_hd import ROOT,relief_door_frames,stone_threshold
from tools.eldenmere_hd_materials import Materials,read

class ReserveThresholdArtTests(unittest.TestCase):
    def test_registered_door_frames_retain_leaf_and_static_frame(self):
        frames=relief_door_frames((24,36),Materials())
        self.assertEqual(len(frames),5)
        for i,frame in enumerate(frames):
            self.assertEqual(frame.size,(48,72))
            self.assertEqual(set(frame.getchannel('A').tobytes()),{0,255})
            self.assertEqual(Image.open(ROOT/f'assets/maps/sanctuary_reserve_hd/doors/{i}.png').tobytes(),frame.tobytes())
            for box in ((0,0,48,8),(0,8,5,70),(43,8,48,70),(6,70,42,72)):
                self.assertIsNone(ImageChops.difference(frame.crop(box),frames[0].crop(box)).getbbox())
        self.assertNotEqual(frames[-1].getpixel((24,30))[:3],(36,48,45))
        self.assertGreater(len(set(frames[-1].crop((10,50,38,68)).getdata())),4)

    def test_sill_uses_exact_sensor_and_clearance_not_a_new_entrance(self):
        for scene in ('elden_vale_sanctuary_hall','elden_vale_sanctuary_relief'):
            data=read(f'assets/maps/{scene}/map.json');door=data['doors'][0]
            shell=Image.new('RGBA',tuple(v*2 for v in data['size_pixels']))
            result=stone_threshold(shell,data,door,Materials(),scene.endswith('_hall'))
            y=data['exit_clearance'][1]
            w=48 if scene.endswith('_hall') else 24
            x=door['anchor'][0]-w//2
            sy=door['entry_y']*2-3
            self.assertEqual(result.getpixel((x*2+1,sy))[:3],(222,214,182))
            self.assertEqual(result.getpixel(((x+w)*2-2,sy))[:3],(222,214,182))
            # Added cut-wall returns remain outside the clear passage.
            self.assertEqual(result.getpixel((x*2-10,y*2))[:3],(114,121,107))
            self.assertEqual(result.getpixel(((x+w)*2+10,y*2))[:3],(114,121,107))
