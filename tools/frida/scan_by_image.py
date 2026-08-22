import frida
import json
import threading

event = threading.Event()

js_code = """
'use strict';

function scanClasses() {
    var imgPtr = ptr('0x777faabda0');
    var pVal = BigInt(imgPtr.toString());
    var pPattern = '';
    for (var b = 0; b < 8; b++) {
        var bHex = Number((pVal >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
        if (bHex.length < 2) bHex = '0' + bHex;
        pPattern += bHex + (b < 7 ? ' ' : '');
    }

    var targetNames = ['CData_Hero', 'CData_Skill', 'CData_Effect', 'CData_EquipBase'];
    var results = {};
    var count = 0;

    var ranges = Process.enumerateRanges('rw-').concat(Process.enumerateRanges('r--'));
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size > 50 * 1024 * 1024) continue;
        try {
            var matches = Memory.scanSync(r.base, r.size, pPattern);
            for (var j = 0; j < matches.length; j++) {
                var klass = matches[j].address; // klass + 0x00 is image pointer
                try {
                    var namePtr = klass.add(0x10).readPointer();
                    if (!namePtr.isNull() && namePtr.compare(ptr(0x10000000)) > 0) {
                        var cname = namePtr.readUtf8String();
                        if (targetNames.indexOf(cname) !== -1) {
                            // Match! Inspect static fields
                            var sf = klass.add(0xb0).readPointer();
                            var inst = sf.isNull() ? ptr(0) : sf.add(0x8).readPointer();
                            results[cname] = {
                                klass: klass.toString(),
                                static_fields: sf.toString(),
                                instance: inst.toString()
                            };
                        }
                    }
                } catch(e) {}
            }
        } catch(e) {}
    }

    send({ status: 'done', results: results });
}

setTimeout(scanClasses, 50);
"""

def on_message(message, data):
    if message['type'] == 'send':
        payload = message['payload']
        if payload.get('status') == 'done':
            print("\n==========================================")
            print("  SUCCESS: CDATA INSTANCES DISCOVERED")
            print("==========================================")
            print(json.dumps(payload['results'], indent=2))
            event.set()
        else:
            print("MSG:", payload)
    elif message['type'] == 'error':
        print("ERROR:", message['stack'])
        event.set()

device_manager = frida.get_device_manager()
device = device_manager.add_remote_device("127.0.0.1:27042")
session = device.attach(5050)
script = session.create_script(js_code)
script.on('message', on_message)
script.load()

event.wait(timeout=25)
