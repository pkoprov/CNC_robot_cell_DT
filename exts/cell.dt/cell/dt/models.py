import omni.kit.commands as commands
# from pxr import Usd
# import omni.isaac.core.utils.prims as prim_utils

class Cube():
    def __init__(self):
        commands.execute('CreateMeshPrimWithDefaultXform',prim_type='Cube')


class Light():
    def __init__(self):  
        commands.execute('CreatePrim',
        prim_type='DistantLight',
        attributes={'angle': 1.0, 'intensity': 3000})


        # stage: Usd.Stage = Usd.Stage.CreateInMemory()
