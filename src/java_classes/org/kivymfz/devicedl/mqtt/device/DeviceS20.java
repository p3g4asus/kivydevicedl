package org.kivymfz.devicedl.mqtt.device;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.command.StateCommand;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;

public class DeviceS20 extends BaseDevice {

    public DeviceS20(String name, Mqtt3Publish pub) {
        super(name, pub);
        remotes = new ArrayList<>();
        remotes.add("");
        commands = new ArrayList<>();
        commands.add(new StateCommand(REMOTE_ONOFF, COMMAND_ON, this, "1"));
        commands.add(new StateCommand(REMOTE_ONOFF, COMMAND_OFF, this, "0"));
    }

    @Override
    public void parseState(Mqtt3Publish publish) {
        int st = -1;
        try {
            ByteBuffer bb = publish.getPayload().get();
            st = Integer.parseInt(StandardCharsets.UTF_8.decode(bb).toString());
        } catch (Exception e) {
            e.printStackTrace();
        }
        state = (st < 0 ? STATE_UNDETECTED:st == 0? STATE_OFF:STATE_ON) | STATE_ON_OFF;
    }
}
