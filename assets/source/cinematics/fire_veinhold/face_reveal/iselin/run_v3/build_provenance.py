"""Bind the selected complete drawings to their retained generation inputs."""
from pathlib import Path
from hashlib import sha256
import json

P = Path(__file__).resolve().parent
A = P.parent
ROOT = A.parents[5]
REFERENCES = {
    'key_00': ['reference_snapshots/frame_47.png', 'reference_snapshots/frame_00.png'],
    'key_01_d': ['key_00.png', 'key_01_c.png'],
    'key_02_c': ['authoring_hand_02.png', 'key_03.png'],
    'key_03': ['reference_snapshots/frame_03.png', 'material_00_left_reference.png', 'material_06_left_reference.png'],
    'key_13_subdivision': ['authoring_braid_13_subdivision.png', 'braid_body_13_subdivision.png', 'material_15_outward_reference.png'],
    'key_13_recolor': ['key_13_subdivision.png', 'palette_12_blue_fabric.png', 'palette_15_actual_blue_fabric.png', 'palette_12_skin.png', 'palette_15_white_hair.png'],
    'key_14_braid_mid': ['braid_mid_curve_reference.png', 'braid_final_body_14_reference.png'],
    'key_14_recolor': ['key_14_braid_mid.png', 'palette_12_blue_fabric.png', 'palette_15_actual_blue_fabric.png', 'palette_12_skin.png', 'palette_15_white_hair.png'],
    'key_15_hair': ['helper_frame_15.png', 'hair_14_material_reference.png', 'hair_16_material_reference.png'],
    'key_16_c': ['key_16_b.png'],
    'key_23': ['reference_snapshots/frame_23.png', 'reference_snapshots/frame_24.png'],
    'key_25_b': ['reference_snapshots/frame_24.png', 'reference_snapshots/frame_26.png'],
    'key_31_braid_path': ['authoring_braid_31_path.png', 'braid_body_31_reference.png'],
    'key_32_braid_path': ['authoring_braid_32_path.png', 'braid_body_32_reference.png'],
    'key_33_braid_path': ['authoring_braid_33_path.png', 'braid_body_33_reference.png'],
    'key_38_braid_path': ['authoring_braid_38_path.png', 'braid_body_38_reference.png'],
    'key_38_braid_final': ['braid_11_intermediate_reference.png', 'braid_body_38_final_reference.png', 'authoring_braid_38_final_guide.png'],
    'key_38_braid_clean': ['braid_mid_curve_reference.png', 'braid_body_38_approved_reference.png'],
    'key_39_braid_mid': ['braid_mid_curve_reference.png', 'braid_final_body_39_reference.png'],
    'key_40_b': ['reference_snapshots/frame_40.png', 'reference_snapshots/frame_39.png', 'reference_snapshots/frame_41.png'],
    'key_43_c': ['authoring_boot_43.png', 'reference_snapshots/frame_43.png'],
    'key_43_d': ['key_43_c.png'],
}

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def helper_inputs(row):
    name = Path(row['source']).name
    for manifest in ['helper_generation_records.json', 'helper_braid_generation_records.json']:
        data = json.loads((P / manifest).read_text())
        for record in data['records']:
            if record.get('source', record.get('source_master')) != name or record['generation_id'] != row['generation_id']:
                continue
            refs = record.get('archived_references')
            if refs is None:
                refs = [{'path': path, 'sha256': expected} for path, expected in record['reference_sha256'].items()]
            result = []
            for reference in refs:
                original = reference['path']
                path = Path(original)
                if path.is_absolute():
                    path = path.relative_to(ROOT)
                if str(path).startswith('assets/story/fire_veinhold_opening/shot07/characters/iselin/'):
                    path = P / 'reference_snapshots' / path.name
                elif str(path).startswith('assets/source/cinematics/fire_veinhold/face_reveal/iselin/'):
                    path = ROOT / path
                else:
                    path = A / path
                if digest(path) != reference['sha256']:
                    raise ValueError('Generation reference changed: ' + str(path))
                result.append({'path': path.relative_to(A).as_posix(), 'sha256': reference['sha256'], 'original_recorded_path': original})
            return manifest, result
    raise ValueError('Missing exact helper generation: ' + name)

def main():
    selected = json.loads((P / 'candidate_records.json').read_text())
    records = []
    for index, row in sorted(selected.items(), key=lambda item: int(item[0])):
        source, prompt = A / row['source'], A / row['prompt_file']
        record = {'effective_frame': int(index), 'source_master': row['source'], 'source_sha256': digest(source),
                  'generation_id': row['generation_id'], 'prompt_file': row['prompt_file'], 'prompt_sha256': digest(prompt),
                  'tool': 'image_gen.imagegen', 'transparent_background': True,
                  'input_path_space': 'Relative to the actor source folder.',
                  'construction': 'Complete ImageGen figure. No regional restoration, detached limbs, warps, blends, duplicated endpoint or guide pixels enter the exported artwork.'}
        if source.stem in REFERENCES:
            record['input_images'] = [{'path': 'run_v3/' + name, 'sha256': digest(P / name)} for name in REFERENCES[source.stem]]
        else:
            manifest, inputs = helper_inputs(row)
            record['helper_generation_record'] = 'run_v3/' + manifest
            record['input_images'] = inputs
        record['selection_notes'] = row.get('selection_notes', 'Selected in observed chronological order. Source filename is authoring history, not effective phase.')
        records.append(record)
    (P / 'generation_records.json').write_text(json.dumps({'version': 1, 'actor': 'iselin', 'approval_state': 'implemented_for_ingame_review', 'records': records}, indent=2) + '\n')
    profile = json.loads((P / 'candidate_source_art_48.json').read_text())
    order = [{'effective_frame': index, 'source': row['source'], 'sha256': digest(A / row['source']), 'generation_id': row.get('generation_id')} for index, row in enumerate(profile['frames'])]
    (P / 'selected_order.json').write_text(json.dumps(order, indent=2) + '\n')
    print(f'Bound {len(records)} new complete drawings and all {len(order)} selected phases.')

if __name__ == '__main__':
    main()
