/**
 * Fast synchronous LogicBattleManager locator in Frida (< 10ms)
 */
'use strict';

function findBattleManager() {
    var ranges = Process.enumerateRanges('rw-');
    var found = [];

    ranges.forEach(function(r) {
        if (r.size < 0x1000 || r.size > 0x10000000) return;
        try {
            for (var off = 0; off < r.size - 0x220; off += 8) {
                var p = r.base.add(off);
                try {
                    var state = p.add(0x180).readS32();
                    if (state === 2 || state === 6) {
                        var ft = p.add(0x19c).readU32();
                        if (ft > 0 && ft < 10000000) {
                            var pSelf = p.add(0x200).readPointer();
                            var pDict = p.add(0x0a8).readPointer();
                            if (!pSelf.isNull() && !pDict.isNull() && !pSelf.equals(pDict)) {
                                try {
                                    if (pSelf.add(0x5c).readU8() === 1) {
                                        var hid = pSelf.add(0xac).readS32();
                                        var lvl = pSelf.add(0xb4).readS32();
                                        var hp = pSelf.add(0xc8).readS32();
                                        var hpMax = pSelf.add(0xcc).readS32();
                                        var camp = pSelf.add(0x1dc).readS32();
                                        var px = pSelf.add(0x268).readDouble();
                                        var py = pSelf.add(0x270).readDouble();
                                        found.push({
                                            mgr: p.toString(),
                                            state: state,
                                            frameTime: ft,
                                            heroPtr: pSelf.toString(),
                                            heroId: hid,
                                            level: lvl,
                                            hp: hp,
                                            hpMax: hpMax,
                                            camp: camp,
                                            pos: '(' + px.toFixed(2) + ', ' + py.toFixed(2) + ')'
                                        });
                                    }
                                } catch(e) {}
                            }
                        }
                    }
                } catch(e) {}
            }
        } catch(e) {}
    });

    console.log(JSON.stringify(found, null, 2));
}

findBattleManager();
