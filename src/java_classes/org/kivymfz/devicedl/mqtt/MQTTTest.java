package org.kivymfz.devicedl.mqtt;
import android.util.Log;
import com.hivemq.client.mqtt.MqttGlobalPublishFilter;
import com.hivemq.client.mqtt.datatypes.MqttQos;
import com.hivemq.client.mqtt.mqtt3.Mqtt3AsyncClient;
import com.hivemq.client.mqtt.mqtt3.Mqtt3Client;
import com.hivemq.client.mqtt.mqtt3.message.connect.connack.Mqtt3ConnAckReturnCode;
import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.ini4j.Ini;
import org.kivymfz.devicedl.mqtt.command.Command;
import org.kivymfz.devicedl.mqtt.device.Device;

import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.function.Consumer;

public class MQTTTest {
    private String host = "";
    private int port = 0;
    private Mqtt3AsyncClient client = null;
    private HashMap<String, Device> deviceMap = new HashMap<>();
    private Consumer<Device> deviceUpdateCallback = null;
    private String homeName = "Home";
    private String iniPath = "";
    private CompletableFuture<Boolean>  connectionAlreadyStarted = null;
    public final static String TAG = "MQTTTest";
    public MQTTTest(String path, Consumer<Device> callbackUpdate) {
        deviceUpdateCallback = callbackUpdate;
        iniPath = path;
        loadFromIni();
    }

    public boolean loadFromIni() {
        Ini ini = new Ini();
        boolean rv = false;
        try {
            ini.load(new FileReader(iniPath));
            Ini.Section dopey = ini.get("network");
            String newhost = dopey.get("host", "127.0.0.1");
            int newport = dopey.get("mqttport", int.class, 8913);
            if (!host.equals(newhost) || port!=newport) {
                host = newhost;
                port = newport;
                disconnect();
                rv = true;
            }
            dopey = ini.get("params");
            homeName = dopey.get("home", String.class, "Home");
        } catch (IOException e) {
            e.printStackTrace();
        }
        return rv;
    }

    public String getHomeName() {
        return homeName;
    }

    public CompletableFuture<Boolean> connect() {
        if (host.isEmpty() || port == 0) {
            CompletableFuture<Boolean> cf = new CompletableFuture<>();
            cf.complete(false);
            return cf;
        }
        if (client == null) {
            client = Mqtt3Client.builder().
                    serverHost(host).
                    serverPort(port).
                    automaticReconnectWithDefaultConfig().
                    identifier("mfz-test").
                    buildAsync();
            connectionAlreadyStarted = null;
        }
        if (connectionAlreadyStarted == null) {
            Log.i(TAG, "Connecting " + host + ":" + port);
            connectionAlreadyStarted = client.connect().thenAccept(ack -> {
                if (ack.getReturnCode() == Mqtt3ConnAckReturnCode.SUCCESS)
                    client.publishes(MqttGlobalPublishFilter.SUBSCRIBED, this::getPublishedMsg);
                else
                    throw new RuntimeException("Connection not completed (" + ack.getReturnCode() + ")");
            }).thenCompose(cc -> client.subscribeWith().topicFilter("stat/#").qos(MqttQos.EXACTLY_ONCE).send()
            ).handle((subAck, throwable) -> {
                if (throwable != null) {
                    throwable.printStackTrace();
                    return false;
                } else {
                    subAck.getReturnCodes().stream().filter(rc -> rc.isError()).forEach(rc -> {
                        Log.i(TAG, "Subscribe error : " + rc);
                    });
                    return true;
                }
            });
        }
        return connectionAlreadyStarted;
    }

    private void getPublishedMsg(Mqtt3Publish mqtt3Publish) {
        Device d;
        Log.i(TAG, "New message: " + mqtt3Publish);
        String deviceId = Device.extractId(mqtt3Publish);
        if (!deviceMap.containsKey(deviceId)) {
            d = Device.build(mqtt3Publish);
            if (d!= null) {
                deviceMap.put(deviceId, d);
                Log.i(TAG, "New Device: " + d);
            }
        }
        else {
            (d = deviceMap.get(deviceId)).parseState(mqtt3Publish);
            Log.i(TAG, "New state for device "+ deviceId + ": "+ d);
        }
        if (d!=null && deviceUpdateCallback != null) {
            deviceUpdateCallback.accept(d);
        }
    }

    public boolean sendCommand(String commandId) {
        try {
            Log.i(TAG, "command is "+ commandId);
            return deviceMap.keySet().stream().
                    filter(k -> commandId.startsWith(k + "/")).
                    flatMap(k -> deviceMap.get(k).getCommands().stream()).
                    filter(c -> c.getId().equals(commandId)).
                    map(c -> c.getPublishToSend()).map(p -> {
                try {
                    return client.publish(p).handle((pu, t) -> {
                        if (t == null) {
                            Log.i(TAG, "Sent "+ pu);
                            return true;
                        }
                        else {
                            t.printStackTrace();
                            return false;
                        }
                    }).get();
                } catch (InterruptedException e) {
                    e.printStackTrace();
                } catch (ExecutionException e) {
                    e.printStackTrace();
                }
                return false;
            }).findFirst().get();
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    public boolean sendCommand(Command command) {
        Log.i(TAG, "command is "+ command);
        Mqtt3Publish p = command.getPublishToSend();
        try {
            return client.publish(p).handle((pu, t) -> {
                if (t == null) {
                    Log.i(TAG, "Sent "+ pu);
                    return true;
                }
                else {
                    t.printStackTrace();
                    return false;
                }
            }).get();
        } catch (InterruptedException e) {
            e.printStackTrace();
        } catch (ExecutionException e) {
            e.printStackTrace();
        }
        return false;
    }

    public Device getDevice(String devId) {
        return deviceMap.get(devId);
    }

    public void disconnect() {
        if (client!= null) {
            client.disconnect();
            client = null;
        }
    }

    public static void main(String[] args) {
        if (args.length >= 1) {
            MQTTTest tst = new MQTTTest(args[0], null);
            try {
                tst.connect().get();
            } catch (InterruptedException e) {
                e.printStackTrace();
            } catch (ExecutionException e) {
                e.printStackTrace();
            }
            try {
                Thread.sleep(10000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            for (int i = 1; i<args.length; i++) {
                tst.sendCommand(args[i]);
            }
        }
    }
}
