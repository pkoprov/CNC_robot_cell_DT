import omni.ext
import omni.ui as ui
from pxr import UsdGeom, UsdPhysics
from .models import VF2, add_default_light
from .subscriber import DT
import carb.events

# Event is unique integer id. Create it from string by hashing, using helper function.
NEW_MESSAGE = carb.events.type_from_string("cell.dt.NEW_MESSAGE_EVENT")
BUS = omni.kit.app.get_app().get_message_bus_event_stream()


class SyncTwinMqttSampleExtension(omni.ext.IExt):

    def load_usd_model(self):
        print("loading model...")
        if not self.world:
            self.world = self.stage.DefinePrim("/World", "Xform")
        self.model = VF2(self.stage)
        add_default_light(self.stage)
        self.find_model_prim()

    def on_startup(self, ext_id):
        print("Digital Twin startup")
        self.context = omni.usd.get_context()
        self.stage = self.context.get_stage()
        # init data
        self.mqtt_connected = False
        self.world = self.stage.GetPrimAtPath("/World")
        self.model_path = "/World/VF_2"
        self.current_coord = ui.SimpleStringModel("")

        # init ui
        self._window = ui.Window("Digital Twin", width=300, height=350)
        with self._window.frame:
            with ui.VStack():

                ui.Button("load model",clicked_fn=self.load_usd_model)

                ui.Label("Current axes coordinates:")
                ui.StringField(self.current_coord)

                self.status_label = ui.Label("- not connected -")

                ui.Button("connect MQTT", clicked_fn=self.connect_mqtt)
                ui.Button("disconnect MQTT", clicked_fn=self.disconnect)
                ui.Button("Reset Twin", clicked_fn=self.reset)
                ui.Button("Test", clicked_fn=self.test)
                ui.Button("Clear Stage", clicked_fn=self.clear_stage)

        # we want to know when model changes
        self._sub_stage_event = self.context.get_stage_event_stream().create_subscription_to_pop(
                self._on_stage_event)

        # find our xf prim if model already present
        self.find_model_prim()

        # and we need a callback on each frame to update our xf prim
        self._app_update_sub = BUS.create_subscription_to_pop_by_type(NEW_MESSAGE,
                                self._on_app_update_event, name="synctwin.mqtt_sample._on_app_update_event")   

    def clear_stage(self):
        print("clearing stage")
        self.context = omni.usd.get_context()
        self.stage = self.context.get_stage()
        for prim in self.stage.Traverse():
            if prim.GetPath() != "/":  # Skip the PseudoRoot
                self.stage.RemovePrim(prim.GetPath())

    def test(self):
        print("test")

        print(self.vf2_model.axes_drives)
        self.current_coord.set_value(
            str(self.vf2_model.axes_drives["X"].GetTargetPositionAttr().Get())
        )

    def reset(self):
        print("reset")
        BUS.push(NEW_MESSAGE, payload={"CMD": "RESET_ALL"})

    # called on every frame, be careful what to put there
    def _on_app_update_event(self, evt):
        self.current_coord.set_value(str(evt.payload))
        if "CMD" in  evt.payload:
            if evt.payload["CMD"] == "RESET_ALL":
                for drive in self.vf2_model.axes_drives.values():
                    drive.GetTargetPositionAttr().Set(0)
        else:
            for coord, drive in self.vf2_model.axes_drives.items():
                drive.GetTargetPositionAttr().Set(evt.payload[coord])
            self.vf2_model.carousel.GetTargetPositionAttr().Set(
                (self.vf2_client.tool_in_use - 1) * 18
            )

    # called on load
    def _on_stage_event(self, event):
        if event.type == int(omni.usd.StageEventType.OPENED): 
            print("opened new model")
            self.find_model_prim()

    # find the prim to be transformed
    def find_model_prim(self):
        # get prim from input
        prim = self.stage.GetPrimAtPath(self.model_path)
        self.vf2_model = UsdGeom.Xformable(prim)

        if self.vf2_model:
            msg = "found model."
            self.status_label.text = msg

            self.vf2_model.axes_drives = {}
            for coord, path in {
                "X": "/World/VF_2/Geometry/VF_2_0/Y_Axis_Saddle/X_axis_table/Table/X_axis_table_PrismaticJoint",
                "Y": "/World/VF_2/Geometry/VF_2_0/Y_Axis_Saddle/Bearings/Y_axis_saddle_PrismaticJoint",
                "Z": "/World/VF_2/Geometry/VF_2_0/Z_Axis_Ram/Z_axis_ram_PrismaticJoint",
            }.items():
                drive = self.stage.GetPrimAtPath(path)
                self.vf2_model.axes_drives[coord] = UsdPhysics.DriveAPI.GetAll(drive)[0]
            drive = self.stage.GetPrimAtPath(
                "/World/VF_2/Geometry/VF_2_0/Umbrella_Tool_Changer/Umbrella/Carousel/RevoluteJoint"
            )
            self.vf2_model.carousel = UsdPhysics.DriveAPI.GetAll(drive)[0]
            drive = self.stage.GetPrimAtPath(
                "/World/VF_2/Geometry/VF_2_0/Umbrella_Tool_Changer/Drive_Assy/PrismaticJoint"
            )
            self.vf2_model.umbrella = UsdPhysics.DriveAPI.GetAll(drive)[0]

        else:
            msg = "## model not found."
        print(msg)

    # connect to mqtt broker
    def connect_mqtt(self):
        self.vf2_client = DT()
        self.vf2_client.connect()

    def disconnect(self):
        self.vf2_client.disconnect()
        self.status_label.text = "Disonnected from MQTT Broker!"

    def on_shutdown(self):
        print("Digital Twin shutdown")
        self._app_update_sub = None
        try:
            self.vf2_client.disconnect()
        except:
            print("No DT to disconnect from.")
            pass
