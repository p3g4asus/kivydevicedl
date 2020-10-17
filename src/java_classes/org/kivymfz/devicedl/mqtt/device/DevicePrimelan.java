package org.kivymfz.devicedl.mqtt.device;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.json.JSONObject;
import org.kivymfz.devicedl.mqtt.command.StateCommand;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;

public class DevicePrimelan extends BaseDevice {
    public final static int ON_OFF_2BUTTON = 0;
    public final static int IN_OFF_SLIDER = 2;
    public final static int L0_100_SLIDER = 1;
    private int subtype = ON_OFF_2BUTTON;
    public DevicePrimelan(String name, Mqtt3Publish pub) {
        super(name, pub);
    }

    @Override
    public void parseState(Mqtt3Publish publish) {
        String jsons = StandardCharsets.UTF_8.decode(publish.getPayload().get()).toString();
        try {
            JSONObject jso = new JSONObject(jsons);
            int newsubtype = jso.getInt("subtype");
            if (subtype != newsubtype || commands == null) {
                subtype = newsubtype;
                commands = new ArrayList<>();
                if (subtype == L0_100_SLIDER) {
                    commands.add(new StateCommand(REMOTE_ONOFF, COMMAND_ON, this, "1"));
                    commands.add(new StateCommand(REMOTE_ONOFF, COMMAND_OFF, this, "0"));
                }
                else {
                    commands.add(new StateCommand(REMOTE_ONOFF, COMMAND_LEVEL, this, ""));
                }
            }
            int status = Integer.parseInt(jso.getString("state"));
            if (subtype == L0_100_SLIDER)
                state = status | STATE_LIMIT_0100;
            else
                state =  (status != 0? STATE_ON:STATE_OFF) | STATE_ON_OFF;
        }
        catch (Exception ex) {
            state = (state&STATE_MASK) | STATE_ERROR_OFFSET + 1000;
        }
        state |= DEVICE_TYPE_LIGHT;
    }
}
