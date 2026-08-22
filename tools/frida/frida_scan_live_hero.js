/**
 * Fast Hero Reference Scan for live match hero: 0x79b5f1e000
 */
'use strict';

function scan() {
    var heroAddr = ptr('0x79b5f1e000');
    console.log('[*] Target Hero: ' + heroAddr);

    // Read hero level & HP to confirm
    try {
        var lvl = heroAddr.add(0xb4).readS32();
        var hp = heroAddr.add(0xc8).readS32();
        var hpMax = heroAddr.add(0xcc).readS32();
        console.log('[+] Target Hero confirmed: Level ' + lvl + ', HP ' + hp + '/' + hpMax);
    } catch(e) {
        console.log('[-] Error reading target hero: ' + e);
        return;
    }

    // Convert hero pointer to little-endian hex pattern
    var pVal = BigInt(heroAddr.toString());
    var bytes = [];
    for (var b = 0; b < 8; b++) {
        var byteHex = Number((pVal >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
        if (byteHex.length < 2) byteHex = '0' + byteHex;
        bytes.push(byteHex);
    }
    var pattern = bytes.join(' ');
    console.log('[+] Scanning memory for hero pointer pattern: ' + pattern);

    var ranges = Process.enumerateRanges('rw-');
    var hits = [];

    ranges.forEach(function(r) {
        if (r.size < 0x4000 || r.size > 0x8000000) return;
        try {
            Memory.scanSync(r.base, r.size, pattern).forEach(function(m) {
                hits.push(m.address);
            });
        } catch(e) {}
    });

    console.log('[+] Total references found: ' + hits.length);

    hits.forEach(function(hit) {
        [0x200, 0x0a0, 0x0a8, 0x018, 0x020].forEach(function(off) {
            var cand = hit.sub(off);
            try {
                var k = cand.readPointer();
                if (!k.isNull()) {
                    var nPtr = k.add(0x10).readPointer();
                    var name = nPtr.readUtf8String();
                    if (name && (name.indexOf('Battle') !== -1 || name.indexOf('Manager') !== -1 || name.indexOf('Logic') !== -1)) {
                        var state = cand.add(0x180).readS32();
                        var ft = cand.add(0x19c).readU32();
                        var selfP = cand.add(0x200).readPointer();
                        var dicP = cand.add(0x0a8).readPointer();
                        console.log('\n[🔥 MATCH CANDIDATE]');
                        console.log('  Container (-0x' + off.toString(16) + ') : ' + cand);
                        console.log('  Class Name          : ' + name);
                        console.log('  _m_eState (+0x180)  : ' + state + (state === 2 ? ' (IN_BATTLE ✅)' : ''));
                        console.log('  m_uiFrameTime (+0x19c): ' + ft);
                        console.log('  m_RealSelfPlayer    : ' + selfP);
                        console.log('  m_dicPlayerLogic    : ' + dicP);
                        console.log('  Il2CppClass Pointer : ' + k);

                        if (state === 2 && !selfP.isNull()) {
                            console.log('  >>> 🎉 THIS IS THE ACTIVE LOGICBATTLEMANAGER! 🎉 <<<');
                            // Dump static_fields pointers from Il2CppClass
                            console.log('  Dumping Il2CppClass static fields:');
                            for (var sfOff = 0x90; sfOff <= 0xd0; sfOff += 8) {
                                var sfP = k.add(sfOff).readPointer();
                                if (!sfP.isNull()) {
                                    try {
                                        var sfDeref = sfP.readPointer();
                                        console.log('    klass + 0x' + sfOff.toString(16) + ' -> ' + sfP + ' (deref -> ' + sfDeref + ')' + (sfDeref.equals(cand) ? ' [MATCHES INSTANCE SINGLETON! 🎯]' : ''));
                                    } catch(e) {
                                        console.log('    klass + 0x' + sfOff.toString(16) + ' -> ' + sfP);
                                    }
                                }
                            }
                        }
                    }
                }
            } catch(e) {}
        });
    });

    console.log('\n[*] Done scanning.');
}

setTimeout(scan, 50);
