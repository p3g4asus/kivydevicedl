package org.kivymfz.devicedl.mqtt.command;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.device.Device;

public class EmitCommand extends Command {
    public EmitCommand(String remote, String name, Device device) {
        super(remote, name, device);
    }

    @Override
    protected Mqtt3Publish generatePublishToSend() {
        return Mqtt3Publish.builder().topic("cmnd/"+ device.getId()+"/emit")
                .payload(
                        ("[{\"key\":\""+
                                (remote == "@" ? "@":"")+name+"\"," +
                         "\"remote\":\""+ remote + "\"}]").getBytes()).build();
    }
}
