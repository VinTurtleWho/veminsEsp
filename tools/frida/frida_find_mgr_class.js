/**
 * Direct Il2CppClass Scanner for LogicBattleManager
 */

'use strict';

function findClass() {
    console.log('[*] Scanning for LogicBattleManager Il2CppClass...');

    var ranges = Process.enumerateRanges('r--');
    var strMatches = [];

    // Step 1: Find all occurrences of "LogicBattleManager\0"
    ranges.forEach(function(r) {
        if (r.size > 0x10000000) return;
        try {
            Memory.scanSync(r.base, r.size, '4c 6f 67 69 63 42 61 74 74 6c 65 4d 61 6e 61 67 65 72 00').forEach(function(m) {
                strMatches.push(m.address);
                console.log('[+] Found string "LogicBattleManager" at ' + m.address);
            });
        } catch(e) {}
    });

    if (strMatches.length === 0) {
        console.log('[-] String not found in r--, scanning rw- ranges...');
        Process.enumerateRanges('rw-').forEach(function(r) {
            if (r.size > 0x10000000) return;
            try {
                Memory.scanSync(r.base, r.size, '4c 6f 67 69 63 42 61 74 74 6c 65 4d 61 6e 61 67 65 72 00').forEach(function(m) {
                    strMatches.push(m.address);
                    console.log('[+] Found string in rw- at ' + m.address);
                });
            } catch(e) {}
        });
    }

    console.log('[+] Total string occurrences: ' + strMatches.length);

    // Step 2: For each string address, scan for pointers pointing to it
    var allRanges = Process.enumerateRanges('r--').concat(Process.enumerateRanges('rw-'));
    var foundClasses = [];

    strMatches.forEach(function(sAddr) {
        var pVal = BigInt(sAddr.toString());
        var bytes = [];
        for (var b = 0; b < 8; b++) {
            var byteHex = Number((pVal >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
            if (byteHex.length < 2) byteHex = '0' + byteHex;
            bytes.push(byteHex);
        }
        var pPattern = bytes.join(' ');
        console.log('[*] Searching for pointer to string: ' + pPattern);

        allRanges.forEach(function(r) {
            if (r.size > 0x10000000) return;
            try {
                Memory.scanSync(r.base, r.size, pPattern).forEach(function(m) {
                    // m.address is name_ptr at klass + 0x10
                    [0x10, 0x08, 0x18, 0x20].forEach(function(off) {
                        var candKlass = m.address.sub(off);
                        try {
                            var img = candKlass.readPointer();
                            var namePtr = candKlass.add(0x10).readPointer();
                            if (namePtr.equals(sAddr)) {
                                console.log('\n[🎉 FOUND LOGICBATTLEMANAGER IL2CPPCLASS! 🎉]');
                                console.log('[+] Il2CppClass Address: ' + candKlass);
                                console.log('[+] Image Pointer      : ' + img);
                                
                                for (var sfOff = 0x90; sfOff <= 0xd8; sfOff += 8) {
                                    var sfVal = candKlass.add(sfOff).readPointer();
                                    if (!sfVal.isNull() && sfVal.compare(ptr(0x10000000)) > 0) {
                                        try {
                                            var inst = sfVal.readPointer();
                                            console.log('    klass + 0x' + sfOff.toString(16) + ' -> sf: ' + sfVal + ' -> Instance: ' + inst);
                                            if (!inst.isNull() && inst.compare(ptr(0x10000000)) > 0) {
                                                var state = inst.add(0x180).readS32();
                                                var ft = inst.add(0x19c).readU32();
                                                var selfP = inst.add(0x200).readPointer();
                                                var dicP = inst.add(0x0a8).readPointer();
                                                console.log('    >>> LIVE BATTLE MANAGER INSTANCE: ' + inst + ' <<<');
                                                console.log('        _m_eState (+0x180)       : ' + state);
                                                console.log('        m_uiFrameTime (+0x19c)   : ' + ft);
                                                console.log('        m_RealSelfPlayer (+0x200): ' + selfP);
                                                console.log('        m_dicPlayerLogic (+0xa8) : ' + dicP);
                                            }
                                        } catch(e) {
                                            console.log('    klass + 0x' + sfOff.toString(16) + ' -> ' + sfVal);
                                        }
                                    }
                                }

                                foundClasses.push(candKlass);
                            }
                        } catch(e) {}
                    });
                });
            } catch(e) {}
        });
    });

    console.log('\n[*] Done. Total LogicBattleManager classes found: ' + foundClasses.length);
}

setTimeout(findClass, 50);
