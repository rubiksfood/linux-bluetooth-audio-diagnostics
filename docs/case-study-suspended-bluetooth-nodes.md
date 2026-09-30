# Case Study: Interpreting Suspended Bluetooth Audio Nodes

## Overview

This case study demonstrates how Linux Bluetooth Audio Diagnostics was validated against a real Bluetooth audio device and how real-world behaviour helped refine one of the diagnostic rules.

The test device was a **soundcore V40i** connected to a Linux system using BlueZ, PipeWire and WirePlumber.

Two operating states were captured:

1. audio playback active through the soundcore V40i;
2. microphone recording active through the soundcore V40i.

In both cases, BlueZ reported the headset as paired, trusted and connected. The significant difference appeared in the PipeWire playback and capture nodes.

The evidence was collected using redacted diagnostic bundles. Bluetooth addresses and host identifiers have therefore been replaced with placeholders.

## Why this case was useful

PipeWire can report an audio node as `suspended` even when the Bluetooth device itself is connected and working correctly.

A suspended node does not necessarily indicate a failure. It can simply mean that the corresponding direction of the audio device is not currently in use.

This distinction matters for a diagnostic tool because treating every suspended node as a fault would produce misleading results.

The BT005 diagnostic rule therefore reports suspended nodes with `INFO` severity and provides guidance based on whether the node represents playback or capture.

## Test environment

The relevant Bluetooth device remained connected throughout both tests.

A simplified BlueZ view was:

```json
{
  "address": "<bluetooth-address-1>",
  "alias": "soundcore V40i",
  "paired": true,
  "trusted": true,
  "connected": true,
  "blocked": false
}
```

PipeWire exposed one Bluetooth audio device with two associated nodes:

- an `Audio/Sink` playback node;
- an `Audio/Source` capture node.

The correlated PipeWire device had object ID `76`.

## Scenario 1: audio playback active

### User action

Audio playback was actively running through the soundcore V40i.

### Observed PipeWire state

The playback node was active:

```json
{
  "object_id": 82,
  "media_class": "Audio/Sink",
  "state": "running"
}
```

The capture node was suspended:

```json
{
  "object_id": 79,
  "media_class": "Audio/Source",
  "state": "suspended"
}
```

The correlation layer associated both nodes with the same connected Bluetooth device:

```text
Bluetooth device
    soundcore V40i
        |
        +-- PipeWire device 76
              |
              +-- Audio/Sink   node 82   running
              |
              +-- Audio/Source node 79   suspended
```

### Diagnostic result

The tool reported:

```text
[INFO] BT005 - bluez_input.<bluetooth-address-1> for soundcore V40i is in the suspended state.
  Evidence:
    - PipeWire node ID 79 reports state=suspended.
    - Node media class is Audio/Source.
  Possible cause: A suspended capture node is normally idle when no application is using the audio input.
  Recommended next step: Start audio capture and check whether the node leaves the suspended state.
```

### Interpretation

This was expected behaviour.

Audio was being played through the headset, so the `Audio/Sink` node was running. No application was using the headset microphone, so the `Audio/Source` node remained suspended.

The Bluetooth connection itself was healthy.

The suspended capture node was therefore useful diagnostic information, but not evidence of a fault.

## Scenario 2: microphone recording active

### User action

A microphone recording session was started using the soundcore V40i.

### Observed PipeWire state

The capture node became active:

```json
{
  "object_id": 79,
  "media_class": "Audio/Source",
  "state": "running"
}
```

At the same time, the playback node was suspended:

```json
{
  "object_id": 82,
  "media_class": "Audio/Sink",
  "state": "suspended"
}
```

The correlation view was therefore:

```text
Bluetooth device
    soundcore V40i
        |
        +-- PipeWire device 76
              |
              +-- Audio/Sink   node 82   suspended
              |
              +-- Audio/Source node 79   running
```

### Diagnostic result

The tool reported:

```text
[INFO] BT005 - bluez_output.<bluetooth-address-1> for soundcore V40i is in the suspended state.
  Evidence:
    - PipeWire node ID 82 reports state=suspended.
    - Node media class is Audio/Sink.
  Possible cause: A suspended playback node is normally idle when no application is playing audio.
  Recommended next step: Start audio playback and check whether the node leaves the suspended state.
```

### Interpretation

Again, the result was consistent with the observed activity.

The microphone was in use, so the `Audio/Source` node had moved from `suspended` to `running`.

The playback endpoint was not being used during the recording test, so the `Audio/Sink` node was suspended instead.

The important result was that the suspended state moved between endpoints according to which direction of the Bluetooth audio device was active.

## Comparison

| Test state | Audio/Sink | Audio/Source | BT005 finding |
| --- | --- | --- | --- |
| Playback active | `running` | `suspended` | Informational finding for capture node |
| Recording active | `suspended` | `running` | Informational finding for playback node |

This demonstrates why a suspended PipeWire node cannot be interpreted correctly without considering its media class and the current audio activity.

## Diagnostic rule refinement

Earlier development of BT005 used generic guidance for a suspended node:

```text
Start audio playback or capture and check whether the node leaves the suspended state.
```

Real-device testing showed that this was unnecessarily broad.

When the suspended node is an `Audio/Source`, starting playback does not test that endpoint. Similarly, starting a recording does not directly test a suspended `Audio/Sink`.

BT005 was therefore refined to provide media-class-aware guidance.

For an `Audio/Source`:

```text
Possible cause: A suspended capture node is normally idle when no application is using the audio input.
Recommended next step: Start audio capture and check whether the node leaves the suspended state.
```

For an `Audio/Sink`:

```text
Possible cause: A suspended playback node is normally idle when no application is playing audio.
Recommended next step: Start audio playback and check whether the node leaves the suspended state.
```

The severity remains `INFO` for a suspended node because suspension can be a normal idle state rather than a failure.

An actual PipeWire node state of `error` remains a higher-severity condition.

## Validation outcome

The real-device test confirmed several parts of the diagnostic pipeline:

- BlueZ correctly identified the headset as connected;
- PipeWire exposed separate playback and capture endpoints;
- the correlation layer associated both endpoints with the correct Bluetooth device;
- BT005 detected suspended nodes;
- suspended-state findings remained informational rather than being treated as failures;
- the active and suspended endpoints changed consistently with real playback and recording activity;
- media-class-aware recommendations accurately described how to test the affected endpoint.

The test also demonstrated the value of keeping observed evidence separate from possible causes.

The diagnostic tool does not claim that `suspended` means the audio stack has failed. Instead, it reports the observed state and explains that idle suspension may be normal.

## Privacy

The evidence used for this case study was collected from redacted diagnostic bundles.

Known host identifiers and Bluetooth addresses were replaced with placeholders such as:

```text
<hostname>
<bluetooth-address-1>
```

Only fields relevant to the case study are reproduced here.

Redaction reduces exposure of known identifiers but is not intended to guarantee complete anonymisation of arbitrary diagnostic or journal content. Diagnostic bundles should still be reviewed before being shared publicly.

## Conclusion

This test showed that a connected Bluetooth headset can legitimately expose one running PipeWire endpoint and one suspended endpoint depending on whether playback or capture is active.

The important diagnostic distinction is therefore not simply:

```text
suspended = problem
```

but:

```text
Which node is suspended?
What is its media class?
What audio activity is currently expected?
```

Testing against real hardware exposed an ambiguity in the original BT005 guidance and led to a more precise diagnostic recommendation without increasing the severity of a normal idle state.

This is the behaviour expected from an evidence-driven diagnostic tool: report the observed state accurately, avoid claiming an unsupported root cause, and recommend a test appropriate to the affected audio endpoint.
