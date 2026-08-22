/**
 * Fast Hero-Pointer Reference Scanner
 * Searches all heap memory for pointers to the active hero
 * and reveals the containing LogicBattleManager object!
 */

'use strict';

function findHeroRefs() {
    console.log('[*] =========================================================');
    console.log('[*] HERO POINTER BACK-REFERENCE SCAN');
    console.log('[*] =========================================================');

    // Step 1: Scan for the active LogicPlayer (IsPlayer == 1 at +0x5c)
    var ranges = Process.enumerateRanges('rw-');
    var activeHero = null;

    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size < 0x1000 || r.size > 0x10000000) continue;

        try {
            Memory.scanSync(r.base, r.size, '01 00 00 00').forEach(function(m) {
                if (activeHero) return;
                var cand = m.address.sub(0x5c);
                try {
                    var lvl = cand.add(0xb4).readS32();
                    var hp = cand.add(0xc8).readS32();
                    var hpMax = cand.add(0xcc).readS32();
                    if (lvl >= 1 && lvl <= 15 && hpMax >= 500 && hp > 0 && hp <= hpMax) {
                        var klass = cand.readPointer();
                        if (!klass.isNull()) {
                            var namePtr = klass.add(0x10).readPointer();
                            var name = namePtr.readUtf8String();
                            if (name === 'LogicPlayer') {
                                activeHero = cand;
                                console.log('[+] Found Active LogicPlayer: ' + activeHero);
                                console.log('    Level: ' + lvl + ', HP: ' + hp + '/' + hpMax);
                                console.log('    Pos  : (' + cand.add(0x268).readDouble().toFixed(1) + ', ' + cand.add(0x270).readDouble().toFixed(1) + ')');
                            }
                        }
                    }
                } catch(e) {}
            });
        } catch(e) {}
        if (activeHero) break;
    }

    if (!activeHero) {
        console.log('[-] Could not locate active LogicPlayer');
        return;
    }

    // Step 2: Convert activeHero pointer to hex pattern (Little-Endian)
    var heroBigInt = BigInt(activeHero.toString());
    var hexBytes = [];
    for (var b = 0; b < 8; b++) {
        var byteVal = Number((heroBigInt >> BigInt(b * 8)) & BigInt(0xff));
        var hexStr = byteVal.toString(16);
        if (hexStr.length < 2) hexStr = '0' + hexStr;
        hexBytes.push(hexStr);
    }
    var heroPattern = hexBytes.join(' ');
    console.log('[+] Hero pointer pattern: ' + heroPattern);

    // Step 3: Scan all rw- ranges for references to this hero pointer!
    var refLocations = [];
    ranges.forEach(function(r) {
        if (r.size < 0x1000 || r.size > 0x10000000) return;
        try {
            Memory.scanSync(r.base, r.size, heroPattern).forEach(function(m) {
                refLocations.push(m.address);
            });
        } catch(e) {}
    });

    console.log('[+] Found ' + refLocations.length + ' memory references to Hero pointer:');
    
    refLocations.forEach(function(refAddr, idx) {
        console.log('\n--- Reference #' + (idx + 1) + ' at ' + refAddr + ' ---');
        // Check offsets from containing candidate objects
        // If refAddr is container + 0x200, container is refAddr - 0x200
        // If refAddr is container + 0x0a0, container is refAddr - 0x0a0
        [0x200, 0x0a0, 0x038, 0x040, 0x020].forEach(function(testOff) {
            var container = refAddr.sub(testOff);
            try {
                var cKlass = container.readPointer();
                if (!cKlass.isNull()) {
                    var cNamePtr = cKlass.add(0x10).readPointer();
                    var cName = cNamePtr.readUtf8String();
                    if (cName && cName.length > 2 && cName.length < 60) {
                        console.log('  Container (-0x' + testOff.toString(16) + '): ' + container + ' -> Class: ' + cName);
                        if (cName.indexOf('BattleManager') !== -1 || cName.indexOf('LogicBattle') !== -1) {
                            console.log('  🎉 MATCH! LogicBattleManager at: ' + container);
                            var state = container.add(0x180).readS32();
                            var ft = container.add(0x19c).readU32();
                            console.log('     _m_eState (+0x180): ' + state);
                            console.log('     m_uiFrameTime (+0x19c): ' + ft);
                        }
                    }
                }
            } catch(e) {}
        });
    });
}

setTimeout(findHeroRefs, 100);
