import omni.ext
import omni.ui as ui
from paho.mqtt import client as mqtt_client
from pxr import UsdGeom, Gf
from .models import VF2, add_default_light
from .subscriber import DT
import carb.events
import json


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
        for prim in self.stage.Traverse():
            if prim.GetPath() != "/":  # Skip the PseudoRoot
                self.stage.RemovePrim(prim.GetPath())

    def test(self):
        print("test")
        print(self.dt.coordinates)

        # if self.vf2:
        #     translation_matrix = Gf.Matrix4d().SetTranslate(Gf.Vec3d(0, 0, 0))
        #     print(translation_matrix)
        #     self.vf2.MakeMatrixXform().Set(translation_matrix)
        #     print("Done translating to",translation_matrix)

    # called on every frame, be careful what to put there
    def _on_app_update_event(self, evt):
            self.current_coord.set_value(str(self.vf2_client.coordinates))

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
            self.vf2_model.axes = {}
            self.vf2_model.axis_origin = {}
            for coord, path in {"X":"/World/VF_2/Geometry/VF_2_0/Y_Axis_Saddle/X_Axis_Table",
                        "Y":"/World/VF_2/Geometry/VF_2_0/Y_Axis_Saddle",
                        "Z":"/World/VF_2/Geometry/VF_2_0/Z_Axis_Ram"}.items():
                prim = self.stage.GetPrimAtPath(path)
                self.vf2_model.axes[coord] = UsdGeom.Xformable(prim)
                self.vf2_model.axis_origin[coord] = self.vf2_model.axes[
                    coord
                ].GetLocalTransformation()
        else:
            msg = "## model not found."
        self.status_label.text = msg
        print(msg)

    # connect to mqtt broker
    def connect_mqtt(self):
        self.vf2_client = DT()
        self.vf2_client.connect()

    def disconnect(self):
        self.dt.disconnect()
        self.status_label.text = "Disonnected from MQTT Broker!"

    def on_shutdown(self):
        print("Digital Twin shutdown")
        self._app_update_sub = None
        try:
            self.dt.disconnect()
        except:
            print("No DT to disconnect from.")
            pass
