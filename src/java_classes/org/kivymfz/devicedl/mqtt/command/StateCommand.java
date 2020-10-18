package org.kivymfz.devicedl.mqtt.command;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.device.Device;

public class StateCommand extends Command {
    public String getState() {
        return state;
    }

    public void setState(String state) {
        if (this.state != state) {
            this.state = state;
            this.publishToSend = generatePublishToSend();
        }
    }

    private String state = "";
    public StateCommand(String remote, String name, Device device, String state) {
        super(remote, name, device);
        this.setState(state);
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
