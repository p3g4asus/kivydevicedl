package org.kivymfz.devicedl.mqtt.device;

import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish;
import org.kivymfz.devicedl.mqtt.command.Command;
import org.kivymfz.devicedl.mqtt.command.EmitCommand;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

public class DeviceRm extends BaseDevice {

    public DeviceRm(String name, Mqtt3Publish pub) {
        super(name, pub);
        state |=  STATE_STATELESS;
    }

    public static class Pair<K, V> {
        public K key;
        public V value;
        public Pair(K k, V v) {
            key = k;
            value = v;
        }
    }

    @Override
    public void parseState(Mqtt3Publish publish) {
        try {
            String topic = publish.getTopic().toString();
            String id = getId();
            String jsons = StandardCharsets.UTF_8.decode(publish.getPayload().get()).toString();
            if (topic.equals("stat/" + id + "/emit")) {
                JSONArray jso = new JSONArray(jsons);
                int sta = 1;
                for (int i = 0; i<jso.length(); i++) {
                    sta = jso.getJSONObject(i).getInt("status");
                    if (sta!=1)
                        break;
                }
                state = (sta != 1? STATE_ERROR_OFFSET + sta: STATE_OK) | STATE_STATELESS;
                /*Iterable it = (() -> jso.iterator());
                Optional<Integer>  rv = StreamSupport.stream(it.spliterator(),false).
                        map(el -> ((JSONObject)el).getInt("status")).
                        filter(sta -> (Integer)sta != 1).findFirst();
                state = (rv.isPresent()? STATE_ERROR_OFFSET + rv.get(): STATE_OK) | STATE_STATELESS;*/
            }
            else if (topic.equals("stat/" + id + "/remotes")) {
                JSONObject remotes = new JSONObject(jsons);
                List<Command> cmds = new ArrayList<>();
                for (Iterator<String> it = remotes.keys(); it.hasNext(); ) {
                    String remName = it.next();
                    JSONArray remote = remotes.getJSONArray(remName);
                    for (int j = 0; j<remote.length(); j++) {
                        cmds.add(new EmitCommand(remName, remote.getString(j), this));
                    }
                }
                /*List<Command> cmds = (List<Command>) remotes.keySet().stream().map(k -> new Pair<String, JSONArray>(k, remotes.getJSONArray(k))).
                        flatMap(p -> {
                            Iterable it = (() -> p.value.iterator());
                            return StreamSupport.stream(it.spliterator(),false).map(o -> new EmitCommand(p.key, o.toString(), this));
                        }).collect(Collectors.toList());*/
                if (commands == null)
                    commands = cmds;
                else {
                    commands = commands.stream().filter(c -> c.getRemote().equals("@")).collect(Collectors.toList());
                    commands.addAll(cmds);
                }
                this.remotes = commands.stream().map(c -> c.getRemote()).distinct().collect(Collectors.toList());
            }
            else if (topic.equals("stat/" + id + "/shortcuts")) {
                JSONArray shs = new JSONArray(jsons);
                List<Command> cmds = new ArrayList<>();
                for (int j = 0; j<shs.length(); j++) {
                    cmds.add(new EmitCommand("@", shs.getString(j), this));
                }
                /*Iterable it = (() -> shs.iterator());
                List<Command> cmds = (List<Command>) StreamSupport.stream(it.spliterator(),false).map(o -> new EmitCommand("@", o.toString(), this)).collect(Collectors.toList());*/
                if (commands == null)
                    commands = cmds;
                else {
                    commands = commands.stream().filter(c -> !c.getRemote().equals("@")).collect(Collectors.toList());
                    commands.addAll(cmds);
                }
                this.remotes = commands.stream().map(c -> c.getRemote()).distinct().collect(Collectors.toList());
            }
        } catch (JSONException e) {
            e.printStackTrace();
            state = STATE_INVALID | STATE_STATELESS;
        }
    }
}
