/**
 * Frida Hook on LogicBattleManager methods & direct pointer resolution
 */
'use strict';

function run() {
    var liblogic = Process.findModuleByName('liblogic.so');
    var libil2cpp = Process.findModuleByName('libil2cpp.so');
    console.log('[+] liblogic  : ' + (liblogic ? liblogic.base : 'null'));
    console.log('[+] libil2cpp : ' + (libil2cpp ? libil2cpp.base : 'null'));

    // Scan for all instances of LogicPlayer and print their pointers and heroes
    var ranges = Process.enumerateRanges('rw-');
    console.log('[+] Enumerated ' + ranges.length + ' rw ranges.');

    var heroPointers = [];
    ranges.forEach(function(r) {
        if (r.size < 0x1000 || r.size > 0x8000000) return;
        try {
            // Check for LogicPlayer objects
            for (var off = 0; off < Math.min(r.size, 0x400000) - 0x300; off += 0x1000) {
                var p = r.base.add(off);
                try {
                    if (p.add(0x5c).readU8() === 1) {
                        var hid = p.add(0xac).readS32();
                        var lvl = p.add(0xb4).readS32();
                        var hp = p.add(0xc8).readS32();
                        var hpMax = p.add(0xcc).readS32();
                        var camp = p.add(0x1dc).readS32();
                        if (hid > 0 && hid < 200 && lvl >= 1 && lvl <= 15 && hp >= 0 && hp <= hpMax && hpMax > 1000 && hpMax < 50000 && (camp === 1 || camp === 2)) {
                            var px = p.add(0x268).readDouble();
                            var py = p.add(0x270).readDouble();
                            heroPointers.push({ptr: p, id: hid, lvl: lvl, hp: hp, hpMax: hpMax, camp: camp, pos: '(' + px.toFixed(1) + ', ' + py.toFixed(1) + ')'});
                        }
                    }
                } catch(e) {}
            }
        } catch(e) {}
    });

    console.log('\n[✓] ALL ACTIVE HEROES IN MATCH:');
    heroPointers.forEach(function(h) {
        var isLayla = h.id === 18 ? ' ⭐⭐ [LAYLA - LOCAL CANDIDATE]' : '';
        console.log('  • ' + h.ptr + ' | ID: ' + h.id + ' | Lv.' + h.lvl + ' | Camp: ' + h.camp + ' | HP: ' + h.hp + '/' + h.hpMax + ' | Pos: ' + h.pos + isLayla);
    });
}

run();
