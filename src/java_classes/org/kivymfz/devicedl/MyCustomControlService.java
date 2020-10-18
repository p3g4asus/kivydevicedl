package org.kivymfz.devicedl;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Environment;
import android.service.controls.Control;
import android.service.controls.ControlsProviderService;
import android.service.controls.DeviceTypes;
import android.service.controls.actions.BooleanAction;
import android.service.controls.actions.ControlAction;
import android.service.controls.actions.FloatAction;
import android.service.controls.templates.ControlButton;
import android.service.controls.templates.RangeTemplate;
import android.service.controls.templates.StatelessTemplate;
import android.service.controls.templates.ToggleTemplate;
import android.util.Log;
import io.reactivex.Flowable;
import io.reactivex.processors.ReplayProcessor;
import org.kivymfz.devicedl.mqtt.MQTTTest;
import org.kivymfz.devicedl.mqtt.command.Command;
import org.kivymfz.devicedl.mqtt.command.StateCommand;
import org.kivymfz.devicedl.mqtt.device.Device;
import org.reactivestreams.FlowAdapters;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.Flow;
import java.util.function.Consumer;
import java.util.stream.Collectors;

//Ini ini = new Ini();
//ini.load(new FileReader(file));
//int age = ini.get("happy", "age", int.class);

public class MyCustomControlService extends ControlsProviderService {
    public static final String TAG = "MyCustomControlService";
    private MQTTTest mqttManager = null;
    private List<Control> stateControls = new ArrayList<>();
    private ReplayProcessor updatePublisher = null;
    private PendingIntent activityIntent;

    private static String statusTextFromDeviceState(int status) {
        if ((status&Device.STATE_TYPE_MASK) == Device.STATE_ON_OFF) {
            if ((status & Device.STATE_MASK) == Device.STATE_OFF)
                return Device.STATE_OFF_S;
            else if ((status & Device.STATE_MASK) == Device.STATE_ON)
                return Device.STATE_ON_S;
            else if ((status & Device.STATE_MASK) == Device.STATE_UNDETECTED)
                return Device.STATE_UNDETECTED_S;
        }
        else if ((status&Device.STATE_TYPE_MASK) == Device.STATE_LIMIT_0100) {
            if ((status & Device.STATE_MASK) == Device.STATE_UNDETECTED)
                return Device.STATE_UNDETECTED_S;
            else if ((status & Device.STATE_MASK) > Device.STATE_ERROR_OFFSET)
                return Device.STATE_INVALID_S;
            else
                return (status & Device.STATE_MASK) != 0? Device.STATE_ON_S: Device.STATE_OFF_S;
        }
        else if ((status&Device.STATE_TYPE_MASK) == Device.STATE_STATELESS) {
            if ((status & Device.STATE_MASK) == Device.STATE_OK)
                return Device.STATE_OK_S;
            else if ((status & Device.STATE_MASK) == Device.STATE_UNDETECTED)
                return Device.STATE_OK_S;
            else
                return Device.STATE_INVALID_S;
        }
        return "" ;
    }

    private boolean isControlOK(String searchControlId, String searchStatus) {
        Optional<Control> opControl = stateControls.stream().filter(c -> c.getControlId().equals(searchControlId)).findFirst();
        Control control;
        if (opControl.isPresent()) {
            control = opControl.get();
            if (control.getStatusText().equals(searchStatus))
                return true;
        }
        return false;
    }

    private void updateControl(Control control) {
        stateControls = stateControls.stream().filter(c -> !c.getControlId().equals(control.getControlId())).collect(Collectors.toList());
        stateControls.add(control);
        if (updatePublisher != null)
            updatePublisher.onNext(control);
    }

    private void processDeviceUpdate(Device updatedDevice) {
        int status = updatedDevice.getState();
        String devId = updatedDevice.getId();
        String devStatusS = statusTextFromDeviceState(status);
        Log.i(TAG, "ProcessDeviceUpdate " + updatedDevice);
        if ((status&Device.STATE_TYPE_MASK) == Device.STATE_ON_OFF) {
            if (isControlOK(devId, devStatusS))
                return;
            Control control = new Control.StatefulBuilder(devId, activityIntent)
                    // Required: The name of the control
                    .setTitle(updatedDevice.getName())
                    .setControlTemplate(new ToggleTemplate(devId + "_toggle", new ControlButton(devStatusS.equals(Device.STATE_ON_S), "toggle")))
                    .setStatusText(devStatusS)
                    // Required: Usually the room where the control is located
                    .setSubtitle("Tap to switch")
                    // Optional: Structure where the control is located, an example would be a house
                    .setStructure(mqttManager.getHomeName())
                    // Required: Type of device, i.e., thermostat, light, switch
                    .setDeviceType((status&Device.DEVICE_TYPE_MASK) == Device.DEVICE_TYPE_LIGHT?DeviceTypes.TYPE_LIGHT:DeviceTypes.TYPE_SWITCH) // For example, DeviceTypes.TYPE_THERMOSTAT
                    // Required: Current status of the device
                    .setStatus((status & Device.STATE_MASK) == Device.STATE_UNDETECTED?Control.STATUS_UNKNOWN:Control.STATUS_OK) // For example, Control.STATUS_OK
                    .build();
            updateControl(control);

        }
        else if ((status&Device.STATE_TYPE_MASK) == Device.STATE_LIMIT_0100) {
            if (isControlOK(devId, devStatusS))
                return;
            Control control = new Control.StatefulBuilder(devId, activityIntent)
                    // Required: The name of the control
                    .setTitle(updatedDevice.getName())
                    .setControlTemplate(new RangeTemplate(devId + "_range",0.0f, 100.0f, updatedDevice.getState()&Device.STATE_MASK, 1, "%d"))
                    .setStatusText(devStatusS)
                    // Required: Usually the room where the control is located
                    .setSubtitle("Set level")
                    // Optional: Structure where the control is located, an example would be a house
                    .setStructure(mqttManager.getHomeName())
                    // Required: Type of device, i.e., thermostat, light, switch
                    .setDeviceType(DeviceTypes.TYPE_LIGHT) // For example, DeviceTypes.TYPE_THERMOSTAT
                    // Required: Current status of the device
                    .setStatus((status & Device.STATE_MASK) == Device.STATE_UNDETECTED?Control.STATUS_UNKNOWN:
                            ((status & Device.STATE_MASK) > Device.STATE_ERROR_OFFSET?Control.STATUS_ERROR:Control.STATUS_OK)) // For example, Control.STATUS_OK
                    .build();
            updateControl(control);

        }
        else if ((status&Device.STATE_TYPE_MASK) == Device.STATE_STATELESS) {
            List<Command> commands = updatedDevice.getCommands();
            commands.stream().filter(com -> !isControlOK(com.getId(), devStatusS)).forEach(com -> {
                Control control = new Control.StatefulBuilder(com.getId(), activityIntent)
                        // Required: The name of the control
                        .setTitle(com.getName())
                        .setControlTemplate(new StatelessTemplate(devId + "_stateless"))
                        .setStatusText(devStatusS)
                        // Required: Usually the room where the control is located
                        .setSubtitle(updatedDevice.getName())
                        // Optional: Structure where the control is located, an example would be a house
                        .setStructure(mqttManager.getHomeName() + " - " + updatedDevice.getName() + "/" + com.getRemote())
                        // Required: Type of device, i.e., thermostat, light, switch
                        .setDeviceType(DeviceTypes.TYPE_REMOTE_CONTROL) // For example, DeviceTypes.TYPE_THERMOSTAT
                        // Required: Current status of the device
                        .setStatus(devStatusS.equals(Device.STATE_OK_S)?Control.STATUS_OK:Control.STATUS_ERROR) // For example, Control.STATUS_OK
                        .build();
                updateControl(control);
            });

        }
    }

    @Override
    public void onCreate() {
        Context ctx = getApplicationContext();
        File[] strg = ctx.getExternalFilesDirs(null);
        File dest = null;
        String data_dir = null;
        if (strg != null && strg.length > 0) {
            dest = strg[0];
            for (File f : strg) {
                if (Environment.isExternalStorageRemovable(f)) {
                    dest = f;
                    break;
                }
            }
            data_dir = dest.getAbsolutePath();
        }
        else {
            dest = ctx.getFilesDir();
            data_dir = dest.getAbsolutePath();
        }
        mqttManager = new MQTTTest(data_dir + File.separator + ".my.ini", this::processDeviceUpdate);
        Intent i = new Intent();
        activityIntent = PendingIntent.getActivity(getBaseContext(), 1, i, PendingIntent.FLAG_UPDATE_CURRENT);
        mqttManager.connect();
        super.onCreate();
    }

    @Override
    public void onDestroy() {
        mqttManager.disconnect();
        super.onDestroy();
    }

    @Override
    public Flow.Publisher createPublisherFor(List<String> controlIds) {
        if (mqttManager.loadFromIni())
            mqttManager.connect();
        /* Fill in details for the activity related to this device. On long press,
         * this Intent will be launched in a bottomsheet. Please design the activity
         * accordingly to fit a more limited space (about 2/3 screen height).
         */


        updatePublisher = ReplayProcessor.create();

        for (String id: controlIds) {
            Log.i(TAG, "cpf "+ id);
        }

        stateControls.stream().
                filter(control -> controlIds.stream().anyMatch(id ->control.getControlId().equals(id))).
                forEach(control -> updatePublisher.onNext(control));
        // Uses the Reactive Streams API
        return FlowAdapters.toFlowPublisher(updatePublisher);
    }



    @Override
    public Flow.Publisher createPublisherForAllAvailable() {
        Log.i(TAG, "cpa");
        if (mqttManager.loadFromIni())
            mqttManager.connect();
        // Uses the RxJava 2 library
        return FlowAdapters.toFlowPublisher(Flowable.fromIterable(stateControls));
    }

    @Override
    public void performControlAction(String controlId, ControlAction action,
                                     Consumer consumer) {

        /* First, locate the control identified by the controlId. Once it is located, you can
         * interpret the action appropriately for that specific device. For instance, the following
         * assumes that the controlId is associated with a light, and the light can be turned on
         * or off.
         */
        try {
            Log.i(TAG, "pca " + controlId + " act " + action);
            Device deviceForId = mqttManager.getDevice(controlId);
            int response = ControlAction.RESPONSE_FAIL;
            if (deviceForId != null) {
                if ((deviceForId.getState() & Device.STATE_TYPE_MASK) == Device.STATE_ON_OFF) {
                    if (action instanceof BooleanAction) {
                        response = ControlAction.RESPONSE_OK;
                        boolean newState = ((BooleanAction) action).getNewState();
                        deviceForId.getCommands().stream().filter(c -> c.getName().equals(newState ? Device.COMMAND_ON : Device.COMMAND_OFF)).forEach(c -> mqttManager.sendCommand(c));
                    }
                } else if ((deviceForId.getState() & Device.STATE_TYPE_MASK) == Device.STATE_LIMIT_0100) {
                    if (action instanceof FloatAction) {
                        response = ControlAction.RESPONSE_OK;
                        int val = (int) (((FloatAction) action).getNewValue() + 0.5f);
                        deviceForId.getCommands().stream().filter(c -> c.getName().equals(Device.COMMAND_LEVEL)).forEach(c -> {
                            ((StateCommand) c).setState("" + val);
                            mqttManager.sendCommand(c);
                        });
                    }
                }
            } else {
                deviceForId = mqttManager.getDeviceFromCommand(controlId);
                if (deviceForId != null) {
                    if ((deviceForId.getState() & Device.STATE_TYPE_MASK) == Device.STATE_STATELESS) {
                        Command cmd = mqttManager.getDeviceCommand(deviceForId, controlId);
                        if (cmd != null && mqttManager.sendCommand(cmd))
                            response = ControlAction.RESPONSE_OK;
                    }
                }
            }
            consumer.accept(response);
        }
        catch (Exception ex) {
            MQTTTest.stackTrace(ex, TAG);
        }
    }
}
