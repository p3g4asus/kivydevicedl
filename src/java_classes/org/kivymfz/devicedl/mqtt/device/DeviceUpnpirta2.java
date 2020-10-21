package org.kivymfz.devicedl.mqtt.device;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;

public class DeviceUpnpirta2 extends DeviceRm {
    public DeviceUpnpirta2(String name, Mqtt3Publish pub) {
        super(name, pub);
    }

    @Override
    protected Command buildStateRequestCommand() {
        return new StateCommand("", COMMAND_GET_STATE, this, GET_STATE_ACTION);
    }

    @Override
    public void parseState(Mqtt3Publish publish) {
        super.parseState(publish);
        int st = -1;
        try {
            String topic = publish.getTopic().toString();
            String id = getId();
            if (topic.equals("stat/" + id + "/upnp")) {
                ByteBuffer bb = publish.getPayload().get();
                st = Integer.parseInt(StandardCharsets.UTF_8.decode(bb).toString());
                state = (sta != 1? STATE_ERROR_OFFSET + sta: STATE_OK) | STATE_STATELESS | DEVICE_TYPE_REMOTE;
            }
        }
        catch (Exception ex) {
            ex.printStackTrace();
        }
        if (st < 0)
            state = STATE_UNDETECTED | STATE_STATELESS | DEVICE_TYPE_REMOTE;
    }
}
