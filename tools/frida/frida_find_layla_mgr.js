/**
 * Find LogicBattleManager by scanning for references to User's Layla (0x7bb4058000)
 */

'use strict';

function findLaylaMgr() {
    var laylaAddr = ptr('0x7bb4058000');
    console.log('[*] Target User Layla: ' + laylaAddr);

    var pVal = BigInt(laylaAddr.toString());
    var bytes = [];
    for (var b = 0; b < 8; b++) {
        var byteHex = Number((pVal >> BigInt(b * 8)) & BigInt(0xff)).toString(16);
        if (byteHex.length < 2) byteHex = '0' + byteHex;
        bytes.push(byteHex);
    }
    var pattern = bytes.join(' ');
    console.log('[*] Scanning for pattern: ' + pattern);

    var ranges = Process.enumerateRanges('rw-');
    var hits = [];
    ranges.forEach(function(r) {
        if (r.size < 0x1000 || r.size > 0x10000000) return;
        try {
            Memory.scanSync(r.base, r.size, pattern).forEach(function(m) {
                hits.push(m.address);
            });
        } catch(e) {}
    });

    console.log('[+] Total references to Layla: ' + hits.length);

    hits.forEach(function(hit) {
        console.log('  Hit at address: ' + hit);
        [0x200, 0x0a0, 0x0a8, 0x0e0, 0x0e8, 0x1fc, 0x588].forEach(function(off) {
            var cand = hit.sub(off);
            try {
                var state = cand.add(0x180).readS32();
                var ft = cand.add(0x19c).readU32();
                var pSelf = cand.add(0x200).readPointer();
                var pPlayers = cand.add(0x0a8).readPointer();
                var pMonsters = cand.add(0x0b0).readPointer();

                if (ft > 0 && !pPlayers.isNull() && !pMonsters.isNull()) {
                    var k = cand.readPointer();
                    console.log('\n[🌟 MATCHING LOGICBATTLEMANAGER FOUND!]');
                    console.log('  Instance (-0x' + off.toString(16) + ') : ' + cand);
                    console.log('  State (+0x180)      : ' + state);
                    console.log('  FrameTime (+0x19c)  : ' + ft);
                    console.log('  RealSelfPlayer (+0x200): ' + pSelf);
                    console.log('  dicPlayers (+0x0a8) : ' + pPlayers);
                    console.log('  dicMonsters (+0x0b0): ' + pMonsters);
                    console.log('  Il2CppClass Pointer : ' + k);

                    if (!k.isNull()) {
                        for (var sfOff = 0x90; sfOff <= 0xd0; sfOff += 8) {
                            var sfP = k.add(sfOff).readPointer();
                            if (!sfP.isNull()) {
                                try {
                                    var sfDeref = sfP.readPointer();
                                    console.log('    klass + 0x' + sfOff.toString(16) + ' -> ' + sfP + ' (deref -> ' + sfDeref + ')' + (sfDeref.equals(cand) ? ' [MATCHES INSTANCE! 🔥]' : ''));
                                } catch(e) {}
                            }
                        }
                    }
                }
            } catch(e) {}
        });
    });
}

findLaylaMgr();
