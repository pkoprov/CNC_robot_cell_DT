import omni.ext
import omni.ui as ui
from paho.mqtt import client as mqtt_client
import random
from pxr import UsdGeom, Gf
from .models import Cube



class SyncTwinMqttSampleExtension(omni.ext.IExt):

    def load_usd_model(self):
        print("loading model...")
        self.context = omni.usd.get_context()
        self_cube = Cube()   
          
    def on_startup(self, ext_id):
        print("Digital Twin startup")
        # init data         
        self.mqtt_connected = False
        self.target_prim = "/World/Cube"
        self.current_coord = ui.SimpleFloatModel(0)

        # init ui 
        self.context = omni.usd.get_context()
        self._window = ui.Window("Digital Twin", width=300, height=350)
        with self._window.frame:
            with ui.VStack():

                ui.Button("load model",clicked_fn=self.load_usd_model)
                
                ui.Label("Current Z coord")
                ui.StringField(self.current_coord)

                self.status_label = ui.Label("- not connected -")
                
                ui.Button("connect MQTT", clicked_fn=self.connect_mqtt)
                ui.Button("disconnect MQTT", clicked_fn=self.disconnect)
                    
        # we want to know when model changes 
        self._sub_stage_event = self.context.get_stage_event_stream().create_subscription_to_pop(
                self._on_stage_event)

        # find our xf prim if model already present 
        self.find_xf_prim()

        # and we need a callback on each frame to update our xf prim 
        self._app_update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
                self._on_app_update_event, name="synctwin.mqtt_sample._on_app_update_event")   
        
    # # called on every frame, be careful what to put there 
    def _on_app_update_event(self, evt):
        # if we have found the transform lets update the translation 
        if self.xf:            
            self.xf.ClearXformOpOrder()
            self.xf.AddTranslateOp().Set(Gf.Vec3f(0, 0, self.current_coord.get_value_as_float()))       

    # called on load 
    def _on_stage_event(self, event):
        if event.type == int(omni.usd.StageEventType.OPENED): 
            print("opened new model")
            self.find_xf_prim()
    
    # find the prim to be transformed 
    def find_xf_prim(self):
        # get prim from input 
        stage = self.context.get_stage()
        prim = stage.GetPrimAtPath(self.target_prim)
        
        self.xf = UsdGeom.Xformable(prim)
        
        if self.xf:
            msg = "found xf."
        else:
            msg = "## xf not found."
        self.status_label.text = msg 
        print(msg)

    # connect to mqtt broker 
    def connect_mqtt(self):

        # this is called when a message arrives 
        def on_message(client, userdata, msg):
            msg_content = msg.payload.decode()
            print(f"Received `{msg_content}` from `{msg.topic}` topic")
            # userdata is self 
            userdata.current_coord.set_value(float(msg_content))

        # called when connection to mqtt broker has been established 
        def on_connect(client, userdata, flags, rc):
            print(f">> connected {client} {rc}")
            if rc == 0:
                userdata.status_label.text = "Connected to MQTT Broker!"
                topic = "ncsu/digital_twin/Cube"
                print(f"subscribing topic {topic}")
                client.subscribe(topic)
            else:
                userdata.status_label.text = f"Failed to connect, return code {rc}"

        # let us know when we've subscribed 
        def on_subscribe(client, userdata, mid, granted_qos):
            print(f"subscribed {mid} {granted_qos}")
        
        # now connect broker
        if self.mqtt_connected:
            print("Already connected to MQTT Broker!")
            self.status_label.text = "Already connected to MQTT Broker!"
            return
            
        # Set Connecting Client ID
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1,  'Omni Cube Client')
        self.client.user_data_set(self)
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        self.client.on_subscribe = on_subscribe
        self.client.connect("192.168.10.4")
        self.client.loop_start()
        self.mqtt_connected = True
        return 

    def disconnect(self):
        print("disconnecting")
        self.client.disconnect()
        self.client.loop_stop()
        self.mqtt_connected = False
        self.status_label.text = "Disonnected from MQTT Broker!"

    def on_shutdown(self):
        print("Digital Twin shutdown")
        self.client = None
        self._app_update_sub = None