import math

class FakeCmds:
    def listRelatives(self, transform, shapes=False, type=None):
        assert transform == "CG_MATCHED_CAMERA"
        assert shapes and type == "camera"
        return ["CG_MATCHED_CAMERAShape"]
    def getAttr(self, plug):
        values = {
            "CG_MATCHED_CAMERAShape.focalLength": 35.0,
            "CG_MATCHED_CAMERAShape.horizontalFilmAperture": 36.0/25.4,
            "CG_MATCHED_CAMERAShape.verticalFilmAperture": 24.0/25.4,
            "CG_MATCHED_CAMERAShape.horizontalFilmOffset": 0.0,
            "CG_MATCHED_CAMERAShape.verticalFilmOffset": 0.0,
        }
        return values[plug]
    def xform(self, transform, query=False, worldSpace=False, matrix=False):
        assert query and worldSpace and matrix
        return [1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]

def camera_signature(cmds, camera_transform):
    shape=(cmds.listRelatives(camera_transform, shapes=True, type="camera") or [])[0]
    focal_mm=float(cmds.getAttr(f"{shape}.focalLength"))
    aperture_in=float(cmds.getAttr(f"{shape}.horizontalFilmAperture"))
    sensor_mm=aperture_in*25.4
    fov=float(math.degrees(2.0*math.atan(sensor_mm/(2.0*max(focal_mm,1e-12)))))
    return {"horizontal_fov_deg":fov,"focal_length_mm":focal_mm,"world_matrix":[float(v) for v in cmds.xform(camera_transform,query=True,worldSpace=True,matrix=True)]}

sig=camera_signature(FakeCmds(),"CG_MATCHED_CAMERA")
expected=math.degrees(2.0*math.atan(36.0/(2.0*35.0)))
assert abs(sig["horizontal_fov_deg"]-expected)<1e-9
assert len(sig["world_matrix"])==16
print("P9_V0413_MAYA_CAMERA_SIGNATURE_PASS",sig["horizontal_fov_deg"])
