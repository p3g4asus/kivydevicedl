package org.kivymfz.devicedl.mqtt.command;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.device.Device;

public class StateCommand extends Command {
    private String state = "";
    public StateCommand(String remote, String name, Device device, String state) {
        super(remote, name, device);
        this.state = state;
        this.publishToSend = generatePublishToSend();
    }

    @Override
    protected Mqtt3Publish generatePublishToSend() {
        if (state != null && !state.isEmpty()) {
            return Mqtt3Publish.builder().topic("cmnd/"+ device.getId()+"/power").payload(state.getBytes()).build();
        }
        else
            return null;
    }
}
