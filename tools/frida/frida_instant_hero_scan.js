/**
 * Instant in-process hero reference scanner via Frida.
 * Executes in ~150ms and dumps all containers holding references to the player.
 */

'use strict';

function instantScan() {
    console.log('[*] Starting in-process fast memory scan for LogicPlayer references...');
    
    var ranges = Process.enumerateRanges('rw-');
    var targetPlayer = null;

    // Fast locate LogicPlayer
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size < 0x4000 || r.size > 0x8000000) continue;
        try {
            Memory.scanSync(r.base, r.size, '01 00 00 00').forEach(function(m) {
                if (targetPlayer) return;
                var cand = m.address.sub(0x5c);
                try {
                    var lvl = cand.add(0xb4).readS32();
                    var hpMax = cand.add(0xcc).readS32();
                    if (lvl >= 1 && lvl <= 15 && hpMax >= 500) {
                        var k = cand.readPointer();
                        if (!k.isNull()) {
                            var n = k.add(0x10).readPointer().readUtf8String();
                            if (n === 'LogicPlayer') {
                                targetPlayer = cand;
                                console.log('[+] Live LogicPlayer located @ ' + targetPlayer + ' (Lvl ' + lvl + ', HP_Max: ' + hpMax + ')');
                            }
                        }
                    }
                } catch(e) {}
            });
        } catch(e) {}
        if (targetPlayer) break;
    }

    if (!targetPlayer) {
        console.log('[-] LogicPlayer not found');
        return;
    }

    // Convert pointer to pattern
    var pVal = BigInt(targetPlayer.toString());
    var bytes = [];
    for (var b = 0; b < 8; b++) {
        var byteHex = Number((pVal >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
        if (byteHex.length < 2) byteHex = '0' + byteHex;
        bytes.push(byteHex);
    }
    var pattern = bytes.join(' ');
    console.log('[+] Scanning for pointer pattern: ' + pattern);

    var hits = [];
    ranges.forEach(function(r) {
        if (r.size < 0x4000 || r.size > 0x8000000) return;
        try {
            Memory.scanSync(r.base, r.size, pattern).forEach(function(m) {
                hits.push(m.address);
            });
        } catch(e) {}
    });

    console.log('[+] Total hits for hero pointer: ' + hits.length);

    hits.forEach(function(addr) {
        console.log('\n--- Hit at ' + addr + ' ---');
        // Test various container offsets
        [0x200, 0x0a0, 0x0a8, 0x020, 0x018, 0x010].forEach(function(off) {
            var candObj = addr.sub(off);
            try {
                var k = candObj.readPointer();
                if (!k.isNull()) {
                    var namePtr = k.add(0x10).readPointer();
                    var name = namePtr.readUtf8String();
                    if (name && name.length > 2 && name.length < 50) {
                        console.log('  Container (-0x' + off.toString(16) + '): ' + candObj + ' | Class: ' + name);
                        if (name.indexOf('BattleManager') !== -1 || name.indexOf('BattleData') !== -1 || name.indexOf('Logic') !== -1) {
                            var state = candObj.add(0x180).readS32();
                            var ft = candObj.add(0x19c).readU32();
                            var selfP = candObj.add(0x200).readPointer();
                            var dicP = candObj.add(0x0a8).readPointer();
                            console.log('  🔥 MATCH: ' + name + ' @ ' + candObj);
                            console.log('     _m_eState (+0x180)  : ' + state);
                            console.log('     m_uiFrameTime (+0x19c): ' + ft);
                            console.log('     m_RealSelfPlayer (+0x200): ' + selfP);
                            console.log('     m_dicPlayerLogic (+0xa8) : ' + dicP);
                            console.log('     Manager Il2CppClass      : ' + k);
                        }
                    }
                }
            } catch(e) {}
        });
    });

    console.log('\n[*] Instant scan complete.');
}

setTimeout(instantScan, 50);
