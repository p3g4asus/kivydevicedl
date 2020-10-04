package org.kivymfz.devicedl;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.service.controls.Control;
import android.service.controls.ControlsProviderService;
import android.service.controls.DeviceTypes;
import android.service.controls.actions.BooleanAction;
import android.service.controls.actions.ControlAction;
import android.service.controls.templates.ControlButton;
import android.service.controls.templates.ControlTemplate;
import android.service.controls.templates.ToggleRangeTemplate;
import android.service.controls.templates.ToggleTemplate;
import android.util.Log;

import org.reactivestreams.FlowAdapters;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Flow;
import java.util.function.Consumer;

import io.reactivex.Flowable;
import io.reactivex.processors.ReplayProcessor;

public class MyCustomControlService extends ControlsProviderService {
    public static final String TAG = "MyCustomControlService";

    private ReplayProcessor updatePublisher;

    @Override
    public Flow.Publisher createPublisherFor(List<String> controlIds) {

        Context context = getBaseContext();
        /* Fill in details for the activity related to this device. On long press,
         * this Intent will be launched in a bottomsheet. Please design the activity
         * accordingly to fit a more limited space (about 2/3 screen height).
         */
        Intent i = new Intent();
        PendingIntent pi = PendingIntent.getActivity(context, 1, i, PendingIntent.FLAG_UPDATE_CURRENT);

        updatePublisher = ReplayProcessor.create();

        for (String id: controlIds) {
            Log.i(TAG, "cpf "+ id);
        }

        // For each controlId in controlIds


        if (controlIds.contains("s20_s202")) {

            Control control = new Control.StatefulBuilder("s20_s202", pi)
                    // Required: The name of the control
                    .setTitle("MiniPC")
                    .setControlTemplate(new ToggleTemplate("s201_toggle", new ControlButton(false, "toggle")))
                    .setStatusText("OFF")
                    // Required: Usually the room where the control is located
                    .setSubtitle("Spinning")
                    // Optional: Structure where the control is located, an example would be a house
                    .setStructure("CasaZazzetta")
                    // Required: Type of device, i.e., thermostat, light, switch
                    .setDeviceType(DeviceTypes.TYPE_SWITCH) // For example, DeviceTypes.TYPE_THERMOSTAT
                    // Required: Current status of the device
                    .setStatus(Control.STATUS_OK) // For example, Control.STATUS_OK
                    .build();

            updatePublisher.onNext(control);
        }
        // Uses the Reactive Streams API
        return FlowAdapters.toFlowPublisher(updatePublisher);
    }



    @Override
    public Flow.Publisher createPublisherForAllAvailable() {
        Context context = getBaseContext();
        Log.i(TAG, "cpa");
        Intent i = new Intent();
        PendingIntent pi = PendingIntent.getActivity(context, 1, i, PendingIntent.FLAG_UPDATE_CURRENT);
        List controls = new ArrayList<>();
        Control control = new Control.StatelessBuilder("s20_s202", pi)
                // Required: The name of the control
                .setTitle("MiniPC")
                // Required: Usually the room where the control is located
                .setSubtitle("Spinning")
                // Optional: Structure where the control is located, an example would be a house
                .setStructure("CasaZazzetta")
                // Required: Type of device, i.e., thermostat, light, switch
                .setDeviceType(DeviceTypes.TYPE_SWITCH) // For example, DeviceTypes.TYPE_THERMOSTAT
                .build();
        controls.add(control);
        // Create more controls here if needed and add it to the ArrayList

        // Uses the RxJava 2 library
        return FlowAdapters.toFlowPublisher(Flowable.fromIterable(controls));
    }

    @Override
    public void performControlAction(String controlId, ControlAction action,
                                     Consumer consumer) {

        /* First, locate the control identified by the controlId. Once it is located, you can
         * interpret the action appropriately for that specific device. For instance, the following
         * assumes that the controlId is associated with a light, and the light can be turned on
         * or off.
         */
        Log.i(TAG, "pca "+ controlId + " act "+action);
        if (action instanceof BooleanAction) {

            // Inform SystemUI that the action has been received and is being processed
            consumer.accept(ControlAction.RESPONSE_OK);

            BooleanAction bAction = (BooleanAction) action;
            Log.i(TAG, "ba "+ bAction.getNewState());
            // In this example, action.getNewState() will have the requested action: true for On,
            // false for Off.
            Intent sendInt = new Intent(Intent.ACTION_SENDTO, Uri.parse("udp://mfzhome.ddns.net:10000/@34 statechange s202 "+(bAction.getNewState()?"1":"0")));
            sendInt.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(sendInt);

            /* This is where application logic/network requests would be invoked to update the state of
             * the device.
             * After updating, the application should use the publisher to update SystemUI with the new
             * state.
             */
            Context context = getBaseContext();
            Intent i = new Intent();
            PendingIntent pi = PendingIntent.getActivity(context, 1, i, PendingIntent.FLAG_UPDATE_CURRENT);
            Control control = new Control.StatefulBuilder("s20_s202", pi)
                    // Required: The name of the control
                    .setTitle("MiniPC")
                    .setControlTemplate(new ToggleTemplate("s201_toggle", new ControlButton(false, "toggle")))
                    .setStatusText("OFF")
                    // Required: Usually the room where the control is located
                    .setSubtitle("Spinning")
                    // Optional: Structure where the control is located, an example would be a house
                    .setStructure("CasaZazzetta")
                    // Required: Type of device, i.e., thermostat, light, switch
                    .setDeviceType(DeviceTypes.TYPE_SWITCH) // For example, DeviceTypes.TYPE_THERMOSTAT
                    // Required: Current status of the device
                    .setStatus(Control.STATUS_OK) // For example, Control.STATUS_OK
                    .build();

            // This is the publisher the application created during the call to createPublisherFor()
            updatePublisher.onNext(control);
        }
    }
}
