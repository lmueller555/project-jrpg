from PIL import Image
from tools.terrain.audit_grassland_seams import edge_error, report

def test_identical_flat_tiles_have_zero_seam_error():
    a=Image.new("RGB",(32,32),(25,50,75))
    assert edge_error(a,a)==0
    assert edge_error(a,a,"vertical")==0

def test_edge_detection_finds_mismatch():
    a=Image.new("RGB",(32,32),(0,0,0))
    b=Image.new("RGB",(32,32),(255,255,255))
    assert edge_error(a,b)==255

def test_source_slot_mismatch_report_exists():
    results=report()
    assert len(results)==5
    assert all(0<=v<=255 for v in results.values())
    # Deliberately do not assert a pass: a source-slot atlas is not mask-verified.
