package org.kivymfz.devicedl.mqtt.command;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.device.Device;

public abstract class Command {
    protected String remote;
    protected String name;
    protected Device device;
    protected Mqtt3Publish publishToSend;

    protected abstract Mqtt3Publish generatePublishToSend();

    @Override
    public String toString() {
        return getId();
    }

    public String getId() {
        return device.getId() + "/" + (remote == null || remote.isEmpty()? name: remote + ":" + name);
    }

    public static String commandId2DeviceId(String commandId) {
        int idx = commandId.lastIndexOf('/');
        if (idx>0 && idx<commandId.length()) {
            return commandId.substring(0, idx);
        }
        else
            return "";
    }

    @Override
    public boolean equals(Object obj) {
        if (obj == null || !(obj instanceof Command))
            return false;
        else {
            return getId().equals(((Command)obj).getId());
        }
    }

    public Mqtt3Publish getPublishToSend(){
        return publishToSend;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Device getDevice() {
        return device;
    }

    public void setDevice(Device device) {
        this.device = device;
    }

    public String getRemote() {
        return remote;
    }

    public void setRemote(String remote) {
        this.remote = remote;
    }


    public Command(String remote, String name, Device device) {
        this.remote = remote;
        this.name = name;
        this.device = device;
        this.publishToSend = generatePublishToSend();
    }

}
