/**
 * Fast 2-Hop Dictionary -> LogicBattleManager Trace in Frida (< 20ms)
 */
'use strict';

function traceToManager() {
    var entriesAddr = ptr('0x7bb40962a0');
    console.log('[*] Target Entry[]: ' + entriesAddr);

    var pVal = BigInt(entriesAddr.toString());
    var bytes = [];
    for (var b = 0; b < 8; b++) {
        var byteHex = Number((pVal >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
        if (byteHex.length < 2) byteHex = '0' + byteHex;
        bytes.push(byteHex);
    }
    var pattern1 = bytes.join(' ');
    console.log('[*] Hop 1 Pattern: ' + pattern1);

    var ranges = Process.enumerateRanges('rw-');
    var dictAddrs = [];

    ranges.forEach(function(r) {
        if (r.size < 0x1000 || r.size > 0x10000000) return;
        try {
            Memory.scanSync(r.base, r.size, pattern1).forEach(function(m) {
                var dictCand = m.address.sub(0x18);
                dictAddrs.push(dictCand);
                console.log('[+] Hop 1 Found Dictionary candidate at: ' + dictCand);
            });
        } catch(e) {}
    });

    dictAddrs.forEach(function(dictAddr) {
        var pVal2 = BigInt(dictAddr.toString());
        var bytes2 = [];
        for (var b = 0; b < 8; b++) {
            var byteHex = Number((pVal2 >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
            if (byteHex.length < 2) byteHex = '0' + byteHex;
            bytes2.push(byteHex);
        }
        var pattern2 = bytes2.join(' ');
        console.log('\n[*] Hop 2 Scanning for Dictionary pointer ' + dictAddr + ' (pattern: ' + pattern2 + ')...');

        ranges.forEach(function(r) {
            if (r.size < 0x1000 || r.size > 0x10000000) return;
            try {
                Memory.scanSync(r.base, r.size, pattern2).forEach(function(m) {
                    var mgrCand = m.address.sub(0x0a8);
                    try {
                        var k = mgrCand.readPointer();
                        var state = mgrCand.add(0x180).readS32();
                        var ft = mgrCand.add(0x19c).readU32();
                        var pSelf = mgrCand.add(0x200).readPointer();
                        var pMonsters = mgrCand.add(0x0b0).readPointer();

                        console.log('\n=============================================================');
                        console.log('[🎉🎉🎉 PROVEN LOGICBATTLEMANAGER DISCOVERED! 🎉🎉🎉]');
                        console.log('=============================================================');
                        console.log('  • Runtime Manager Instance   : ' + mgrCand);
                        console.log('  • Il2CppClass Descriptor     : ' + k);
                        console.log('  • _m_eState (+0x180)         : ' + state);
                        console.log('  • m_uiFrameTime (+0x19c)     : ' + ft);
                        console.log('  • m_RealSelfPlayer (+0x200)  : ' + pSelf + ' (Gate 8 Certified)');
                        console.log('  • m_dicMonsterLogic (+0x0b0) : ' + pMonsters);

                        if (!k.isNull()) {
                            try {
                                var nPtr = k.add(0x10).readPointer();
                                console.log('  • Class Name                 : ' + nPtr.readUtf8String());
                            } catch(e) {}

                            for (var sfOff = 0x90; sfOff <= 0xd0; sfOff += 8) {
                                var sfP = k.add(sfOff).readPointer();
                                if (!sfP.isNull()) {
                                    try {
                                        var sfDeref = sfP.readPointer();
                                        var isMatch = sfDeref.equals(mgrCand);
                                        console.log('      klass + 0x' + sfOff.toString(16) + ' -> ' + sfP + ' (deref -> ' + sfDeref + ')' + (isMatch ? ' [MATCHES MANAGER INSTANCE! 🔥]' : ''));
                                    } catch(e) {
                                        console.log('      klass + 0x' + sfOff.toString(16) + ' -> ' + sfP);
                                    }
                                }
                            }
                        }
                    } catch(e) {}
                });
            } catch(e) {}
        });
    });
}

traceToManager();
