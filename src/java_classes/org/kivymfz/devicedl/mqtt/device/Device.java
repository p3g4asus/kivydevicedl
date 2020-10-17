package org.kivymfz.devicedl.mqtt.device;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.command.Command;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public interface Device {
    int STATE_OFF = 0;
    int STATE_ON = 1;
    int STATE_UNDETECTED = 2;
    int STATE_INVALID = 3;
    int STATE_OK = 4;
    int STATE_ERROR_OFFSET = 100;
    int STATE_MASK = 0xFFFF;
    int DEVICE_TYPE_MASK = 0xFF0000;
    int STATE_TYPE_MASK = 0xFF000000;
    int STATE_ON_OFF = (1<<24);
    int STATE_STATELESS = (2<<24);
    int STATE_LIMIT_0100 = (3<<24);
    int DEVICE_TYPE_SWITCH = (0<<16);
    int DEVICE_TYPE_LIGHT = (1<<16);
    int DEVICE_TYPE_REMOTE = (2<<16);
    String COMMAND_ON = "ON";
    String COMMAND_OFF = "OFF";
    String COMMAND_LEVEL = "LEVEL";
    String STATE_ON_S = COMMAND_ON;
    String STATE_OFF_S = COMMAND_OFF;
    String STATE_UNDETECTED_S = "N/A";
    String REMOTE_ONOFF = "";
    String STATE_OK_S = "OK";
    String STATE_INVALID_S = "ERR";

    void parseState(Mqtt3Publish publish);
    List<Command> getCommands();
    int getState();
    String getName();
    String getType();
    String getId();
    List<String> getRemotes();
    static String[] typeAndNameFromTopic(String topic) {
        Pattern r = Pattern.compile("^stat/([^/]+)/([^/]+)");

        // Now create matcher object.
        Matcher m = r.matcher(topic);

        if (m.find( )) {
            return new String[] { m.group(1),  m.group(2)};
        } else {
            return null;
        }
    }

    static String extractId(Mqtt3Publish publish) {
        String[] typeAndName = typeAndNameFromTopic(publish.getTopic().toString());
        return typeAndName != null? typeAndName[0] + "/" + typeAndName[1]: null;
    }

    static Device build(Mqtt3Publish publish) {
        String[] typeAndName = typeAndNameFromTopic(publish.getTopic().toString());
        if (typeAndName != null) {
            try {
                Class<? extends Device> c = (Class<? extends Device>) Class.forName(Device.class.getPackage().getName()+".Device"+typeAndName[0].substring(0,1).toUpperCase()+typeAndName[0].substring(1));
                return c.getConstructor(String.class, Mqtt3Publish.class).newInstance(typeAndName[1], publish);
            } catch (ClassNotFoundException cnfe) {

            }
            catch (Exception e) {
                e.printStackTrace();
            }
        }
        return null;
    }
}
