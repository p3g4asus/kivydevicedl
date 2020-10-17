package org.kivymfz.devicedl.mqtt.command;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.device.Device;

public class StateCommand extends Command {
    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    private String state = "";
    public StateCommand(String remote, String name, Device device, String state) {
        super(remote, name, device);
        this.state = state;
        this.publishToSend = generatePublishToSend();
    }

    @Override
    protected Mqtt3Publish generatePublishToSend() {
        if (state != null && !state.isEmpty()) {
            return Mqtt3Publish.builder().topic("cmnd/"+ device.getId()+"/state").payload(state.getBytes()).build();
        }
        else
            return null;
    }
}
