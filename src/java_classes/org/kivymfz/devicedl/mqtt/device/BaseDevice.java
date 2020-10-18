package org.kivymfz.devicedl.mqtt.device;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.command.Command;

import java.util.List;

public abstract class BaseDevice implements Device {
    protected String name;
    protected int state = STATE_UNDETECTED;
    protected List<Command> commands = null;
    protected Command stateRequestCommand = null;
    protected List<String> remotes = null;
    protected String type;

    @Override
    public String toString() {
        String out = "Dev " + getId() +"(" + getState() + "):\n";
        if (commands != null)
            for (Command c: commands) {
                out += c.toString() + "\n";
            }
        return out;
    }

    @Override
    public Command getStateRequestCommand() {
        return stateRequestCommand;
    }

    protected Command buildStateRequestCommand() {
        return null;
    }

    @Override
    public List<Command> getCommands() {
        return commands;
    }

    @Override
    public int getState() {
        return state;
    }

    @Override
    public String getName() {
        return name;
    }

    @Override
    public String getId() {
        return getType() + "/" + getName();
    }

    @Override
    public List<String> getRemotes() {
        return remotes;
    }

    @Override
    public String getType() {
        return type;
    }

    public BaseDevice(String name, Mqtt3Publish pub) {
        this.name = name;
        this.type = getClass().getSimpleName().substring("Device".length()).toLowerCase();
        parseState(pub);
        this.stateRequestCommand = buildStateRequestCommand();
    }
}
