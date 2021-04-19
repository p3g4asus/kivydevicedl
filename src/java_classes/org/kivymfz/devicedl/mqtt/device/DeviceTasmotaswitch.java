package org.kivymfz.devicedl.mqtt.device;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;

public class DeviceTasmotaswitch extends DeviceS20 {

    public DeviceTasmotaswitch(String name, Mqtt3Publish pub) {
        super(name, pub);
    }
}
