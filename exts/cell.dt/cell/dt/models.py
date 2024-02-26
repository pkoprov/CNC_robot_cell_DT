import omni.kit.commands as commands
from pxr import Usd, Sdf, UsdLux, Gf, UsdGeom
import omni

ext_dir = omni.kit.app.get_app().get_extension_manager().get_extension_path('cell.dt')
print(ext_dir)


class Cube():
    def __init__(self):
        commands.execute('CreateMeshPrimWithDefaultXform',prim_type='Cube')


class Light():
    def __init__(self):  
        commands.execute('CreatePrim',
        prim_type='DistantLight',
        attributes={'angle': 1.0, 'intensity': 3000})


        # stage: Usd.Stage = Usd.Stage.CreateInMemory()

class VF2():
    def __init__(self, stage: Usd.Stage):
        commands.execute('AddReference',
	stage=stage, 
    prim_path=Sdf.Path('/World'),
	reference=Sdf.Reference('Documents/CNC_robot_cell_DT/exts/cell.dt/data/VF_2.usd'))


def add_default_light(stage):
    # Define the path for the new light prim
    lightPath = "/World/DefaultLight"
    
    # Create a DistantLight prim at the specified path
    distantLight = UsdLux.DistantLight.Define(stage, lightPath)
    
    # Set some basic properties of the light
    distantLight.CreateIntensityAttr(5000)  # Adjust the intensity as needed
    distantLight.CreateColorAttr((1.0, 1.0, 1.0))  # White light
    distantLight.CreateAngleAttr(0.53)  # Adjust the angle for softer shadows
    
    # Position the light (optional, depending on whether you need a specific direction)
    # This example positions the light at a 45-degree angle downward, like sunlight
    lightXformable = UsdGeom.Xformable(distantLight)
    # Create rotations around X and Y axes
    rotationX = Gf.Rotation(Gf.Vec3d(1, 0, 0), 45)
    rotationY = Gf.Rotation(Gf.Vec3d(0, 1, 0), 45)

    # Combine rotations
    combinedRotation = rotationX * rotationY
    lightXformable.AddRotateXOp().Set(combinedRotation.angle)