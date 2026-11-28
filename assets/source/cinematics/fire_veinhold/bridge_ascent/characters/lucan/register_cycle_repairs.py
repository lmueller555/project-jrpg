"""Register bounded whole-figure overhead repairs using actual rigid observations."""
from pathlib import Path
from hashlib import sha256
import json
S=Path(__file__).resolve().parent;ROOT=S.parents[6]


def apply():
    from register_banks import export,OUT
    folder=S/'overhead_motion_repair';selection=json.loads((folder/'selection.json').read_text())
    records=[];allowed=set(range(8,16))|set(range(32,40))|set(range(40,48))
    master_scales={}
    for row in selection['frames']:
        phase=row['phase'];assert phase in allowed,'Repair outside bounded reviewed source intervals'
        source=folder/row['source'];digest=sha256(source.read_bytes()).hexdigest()
        assert digest==row['source_sha256'],'Changed wholefigure ImageGen master'
        scale=row['uniform_scale']
        if source in master_scales:assert master_scales[source]==scale,'Per-pose body normalization is not permitted'
        master_scales[source]=scale
        center=row['crown_center'];origin=[512-center[0]*scale,1040-center[1]*scale]
        record={'kind':'overhead','index':phase,'gait_frame':phase,
            'source':source.relative_to(ROOT).as_posix(),'source_sha256':digest,
            'cell':row['cell'],'scale':scale,'origin':origin,'alpha_floor':16,
            'observed_crown_bbox':row['crown_bbox'],'observed_crown_center':center,
            'rigid_registration':{'observed_main_pauldron_pair_x_bounds':row['main_pauldron_pair_x_bounds'],
                'observed_main_pauldron_pair_span':row['main_pauldron_pair_span'],
                'projected_crown_width':row['projected_crown_width'],
                'projected_main_cap_pair_span':row['projected_main_cap_pair_span'],
                'uncertainty_source_pixels':row['uncertainty_source_pixels']},
            'method':'One uniform scale per unchanged complete ImageGen master, from actual crown and rigid cap observations; whole-image translation registers crown. No occupied-height normalization or part transformation.'}
        path=OUT/f'overhead_{phase:03d}.png';export(record).save(path);record['output_sha256']=sha256(path.read_bytes()).hexdigest();records.append(record)
    return records
